// Basic filament dryer: Wemos D1 Mini or ESP-01S (ESP8266), one temperature + humidity probe, a fan and a heater.
//
// While the air in the box is above 15 % RH the fan runs and the heater warms the box; both stop at
// 15 % RH (and start again above 17 %). The heater never pushes the box past 65 °C: full power up to
// 60 °C, then less and less until it's off at 65 °C. The on-board LED and the USB serial log
// (115200 baud) show what it's doing. The logic lives in lib/BasicControl (tested on the host with
// `pio test -e native`).
//
// D1 Mini: Wi-Fi reporting for the Printer Control Center, with the same API as the smart dryer
// (GET /api/state, WebSocket :81, mDNS filament-dryer-xxxx / _filament-dryer._tcp). The network is
// only a window: the control above runs the same with or without it. First boot opens the
// "FilamentDryer-XXXX" hotspot to enter the Wi-Fi. The ESP-01S build keeps Wi-Fi off.
//
// Pins, D1 Mini (env basic-d1mini; D1 Mini labels):
//   D5 (GPIO14)  heater: 500 Ω -> PC817 LED -> GND; the PC817 drives the IRF3205's gate from 12 V
//   D6 (GPIO12)  fan: 500 Ω -> 2N2222A base
//   D2 (GPIO4)   SDA  } AHT20 probe (I2C, 4.7 kΩ pull-ups to 3V3)
//   D1 (GPIO5)   SCL  }
//   D7 (GPIO13)  AM2301 / DHT22 probe data (4.7 kΩ pull-up to 3V3), used when no AHT20 answers
//   D4 (GPIO2)   on-board LED (active low)
//
// Pins, ESP-01S (env basic-esp01, -D BOARD_ESP01). GPIO0 and GPIO2 must be high at boot, so:
//   GPIO0  heater, ACTIVE LOW: 3V3 -> 470 Ω -> PC817 LED -> GPIO0 (10 kΩ pull-up keeps it off at boot)
//   GPIO3  (RX) fan: 500 Ω -> 2N2222A base, 10 kΩ base -> GND
//   GPIO2  AM2301 / DHT22 probe data (4.7 kΩ pull-up; it shares the on-board LED, so no status LED)
//   GPIO1  (TX) serial log only
#include <Arduino.h>
#include <DHT.h>
#include <EEPROM.h>
#include <ESP8266WiFi.h>
#include <Wire.h>

#include "BasicControl.h"

#define VERSION "0.1.0"

namespace pin {
#ifdef BOARD_ESP01
const uint8_t HEATER = 0, FAN = 3, DHT_ = 2;
const uint8_t HEATER_ON = LOW, HEATER_OFF = HIGH;
#define HAS_I2C 0
#define HAS_LED 0
#else
const uint8_t HEATER = 14, FAN = 12, SDA_ = 4, SCL_ = 5, DHT_ = 13, LED = 2;
const uint8_t HEATER_ON = HIGH, HEATER_OFF = LOW;
#define HAS_I2C 1
#define HAS_LED 1
#endif
}

#ifndef BOARD_ESP01
#define HAS_WIFI 1
#include <ESP8266HTTPUpdateServer.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <WebSocketsServer.h>
#include <WiFiManager.h>
#else
#define HAS_WIFI 0
#endif

static const basic::Settings kSettings;
static bool enabled = true;          // "auto" (default) or "off", set over the API and kept in flash
static char devName[32] = "filament-dryer";

static basic::Controller controller;
static basic::SlowPwm heaterPwm;
static basic::Output out;
static basic::Reading last;
static DHT dht(pin::DHT_, DHT21);

enum class Probe { None, Aht20, Dht21 };
static Probe probe = Probe::None;

#if HAS_I2C
// ---- AHT20 (I2C 0x38) ----
static const uint8_t AHT20 = 0x38;
static bool i2cPresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}
static bool aht20Init() {
  Wire.beginTransmission(AHT20);
  Wire.write(0xBE); Wire.write(0x08); Wire.write(0x00);   // calibrate / initialise
  if (Wire.endTransmission() != 0) return false;
  delay(20);
  return true;
}
static bool aht20Read(float& c, float& rh) {
  Wire.beginTransmission(AHT20);
  Wire.write(0xAC); Wire.write(0x33); Wire.write(0x00);   // trigger a measurement
  if (Wire.endTransmission() != 0) return false;
  delay(85);
  if (Wire.requestFrom((int)AHT20, 7) != 7) return false;
  uint8_t b[7];
  for (int i = 0; i < 7; i++) b[i] = Wire.read();
  if (b[0] & 0x80) return false;                           // still busy
  // CRC-8, polynomial 0x31, init 0xFF, over the first 6 bytes
  uint8_t crc = 0xFF;
  for (int i = 0; i < 6; i++) {
    crc ^= b[i];
    for (int k = 0; k < 8; k++) crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
  }
  if (crc != b[6]) return false;
  uint32_t hRaw = ((uint32_t)b[1] << 12) | ((uint32_t)b[2] << 4) | (b[3] >> 4);
  uint32_t tRaw = (((uint32_t)b[3] & 0x0F) << 16) | ((uint32_t)b[4] << 8) | b[5];
  rh = hRaw * 100.0f / 1048576.0f;
  c = tRaw * 200.0f / 1048576.0f - 50.0f;
  return true;
}
#endif

static void detectProbe() {
#if HAS_I2C
  if (i2cPresent(AHT20) && aht20Init()) {
    probe = Probe::Aht20;
    return;
  }
#endif
  dht.begin();
  delay(2100);                                             // the DHT21 needs 2 s after power-up
  float rh = dht.readHumidity(), c = dht.readTemperature();
  probe = (!isnan(rh) && !isnan(c)) ? Probe::Dht21 : Probe::None;
}

static basic::Reading readProbe() {
  basic::Reading r;
  float c = NAN, rh = NAN;
  if (probe == Probe::Aht20) {
#if HAS_I2C
    r.ok = aht20Read(c, rh);
#endif
  } else if (probe == Probe::Dht21) {
    rh = dht.readHumidity();
    c = dht.readTemperature();
    r.ok = !isnan(rh) && !isnan(c);
  }
  // values outside what the box can really see mean a bad read
  if (r.ok && (c < -20 || c > 100 || rh < 0 || rh > 100)) r.ok = false;
  if (r.ok) { r.c = c; r.rh = rh; }
  return r;
}

static const char* probeName() {
  switch (probe) {
    case Probe::Aht20: return "AHT20";
    case Probe::Dht21: return "AM2301/DHT21";
    default: return "none";
  }
}

// LED: solid while heating, slow blink while only the fan runs, short flash every 3 s when the box is
// dry and idle, fast blink on a sensor fault or over-temperature.
static void showLed(uint32_t now) {
#if HAS_LED
  bool on;
  if (out.sensorFault || out.overTemp) on = (now / 125) % 2;
  else if (out.heaterDuty > 0) on = true;
  else if (out.fan) on = (now / 500) % 2;
  else on = (now % 3000) < 60;
  digitalWrite(pin::LED, on ? LOW : HIGH);
#else
  (void)now;
#endif
}

// ---- settings kept in flash: just the on/off switch ----
static const uint32_t kMagic = 0xD12E0001;
static void loadSettings() {
  EEPROM.begin(16);
  uint32_t magic = 0;
  EEPROM.get(0, magic);
  if (magic == kMagic) enabled = EEPROM.read(4) != 0;
}
static void saveSettings() {
  EEPROM.put(0, kMagic);
  EEPROM.write(4, enabled ? 1 : 0);
  EEPROM.commit();
}

__attribute__((unused)) static const char* faultName() {
  if (out.overTemp) return "chamber_over_temp";
  if (out.sensorFault) return "chamber_sensor";
  return "none";
}

// Same shape as the smart dryer's /api/state where the fields exist, so one control-center
// client reads both. "model":"basic" tells them apart.
__attribute__((unused)) static String stateJson() {
  char chamber[96];
  if (last.ok)
    snprintf(chamber, sizeof chamber, "{\"ok\":true,\"c\":%.1f,\"rh\":%.1f,\"sensor\":\"%s\"}", last.c, last.rh,
             probe == Probe::Aht20 ? "aht20" : "am2301");
  else
    snprintf(chamber, sizeof chamber, "{\"ok\":false,\"sensor\":\"%s\"}",
             probe == Probe::Aht20 ? "aht20" : probe == Probe::Dht21 ? "am2301" : "none");
  char buf[512];
  snprintf(buf, sizeof buf,
           "{\"version\":\"%s\",\"name\":\"%s\",\"model\":\"basic\",\"mode\":\"%s\",\"drying\":%s,"
           "\"setpoint_c\":%.0f,\"stop_rh\":%.0f,\"start_rh\":%.0f,\"fault\":\"%s\",\"chamber\":%s,"
           "\"heater\":{\"duty\":%.2f,\"on\":%s},\"blower\":%s,\"uptime_s\":%lu,\"wifi_rssi\":%d}",
           VERSION, devName, enabled ? "auto" : "off", out.drying ? "true" : "false", kSettings.maxC, kSettings.stopRh,
           kSettings.startRh, faultName(), chamber, out.heaterDuty, out.heaterDuty > 0 ? "true" : "false",
           out.fan ? "true" : "false", (unsigned long)(millis() / 1000),
#if HAS_WIFI
           WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0
#else
           0
#endif
  );
  return String(buf);
}

// "auto" or "off"; anything else is an error
__attribute__((unused)) static String setMode(const String& m) {
  if (m == "auto" || m == "keep_dry" || m == "dry") enabled = true;
  else if (m == "off") enabled = false;
  else return "mode must be auto or off";
  saveSettings();
  Serial.printf("mode: %s\n", enabled ? "auto" : "off");
  return "";
}

#if HAS_WIFI
static ESP8266WebServer http(80);
static WebSocketsServer ws(81);
static ESP8266HTTPUpdateServer updater;
static WiFiManager wm;
static bool servicesUp = false;

static const char PAGE[] PROGMEM = R"HTML(<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Filament dryer</title>
<style>body{font-family:system-ui,sans-serif;margin:24px;background:#fafafa;color:#222}
.big{font-size:44px;font-weight:600}.row{display:flex;gap:32px;flex-wrap:wrap}.lbl{color:#666;font-size:14px}
button{font-size:16px;padding:8px 16px;margin-right:8px}</style></head><body>
<h2 id="n">Filament dryer</h2>
<div class="row"><div><div class="lbl">Temperature</div><div class="big" id="c">–</div></div>
<div><div class="lbl">Humidity</div><div class="big" id="rh">–</div></div></div>
<p id="s"></p>
<button onclick="m('auto')">Auto</button><button onclick="m('off')">Off</button>
<p class="lbl">Fan and heater run above 15 % RH; heater capped at 65 °C. <a href="/api/state">JSON</a> · <a href="/update">Update firmware</a></p>
<script>
function show(j){document.getElementById('n').textContent=j.name;
c.textContent=j.chamber.ok?j.chamber.c.toFixed(1)+' °C':'–';rh.textContent=j.chamber.ok?j.chamber.rh.toFixed(0)+' %':'–';
s.textContent=(j.mode=='off'?'Off':j.fault!='none'?'Fault: '+j.fault:j.drying?'Drying':'Dry, idle')+
' · heater '+Math.round(j.heater.duty*100)+' % · fan '+(j.blower?'on':'off');}
function poll(){fetch('/api/state').then(r=>r.json()).then(show).catch(()=>{});}
function m(x){fetch('/api/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:x})}).then(r=>r.json()).then(show);}
poll();setInterval(poll,2000);
</script></body></html>)HTML";

// tiny parser for {"mode":"..."} / {"cmd":"mode","mode":"..."}: no JSON library needed for one field
static String field(const String& body, const char* key) {
  String k = String("\"") + key + "\"";
  int i = body.indexOf(k);
  if (i < 0) return "";
  i = body.indexOf(':', i + k.length());
  int a = body.indexOf('"', i + 1);
  int b = a < 0 ? -1 : body.indexOf('"', a + 1);
  return (a < 0 || b < 0) ? "" : body.substring(a + 1, b);
}

static void reply(int code, const String& err) {
  http.sendHeader("Access-Control-Allow-Origin", "*");
  if (err.length()) http.send(code, "application/json", "{\"error\":\"" + err + "\"}");
  else http.send(code, "application/json", stateJson());
}

static void wsEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t len) {
  if (type == WStype_CONNECTED) {
    String st = stateJson();
    ws.sendTXT(num, st);
  } else if (type == WStype_TEXT) {
    String body;
    body.concat((const char*)payload, len);
    String err = field(body, "cmd") == "mode" ? setMode(field(body, "mode")) : String("unknown cmd");
    String msg = err.length() ? "{\"error\":\"" + err + "\"}" : stateJson();
    ws.sendTXT(num, msg);
  }
}

static void startServices() {
  MDNS.begin(devName);
  MDNS.addService("http", "tcp", 80);
  MDNS.addService("filament-dryer", "tcp", 81);
  MDNS.addServiceTxt("filament-dryer", "tcp", "model", "basic");
  http.on("/", HTTP_GET, [] { http.send_P(200, "text/html", PAGE); });
  http.on("/api/state", HTTP_GET, [] { reply(200, ""); });
  http.on("/api/mode", HTTP_POST, [] {
    String err = setMode(field(http.arg("plain"), "mode"));
    reply(err.length() ? 400 : 200, err);
  });
  http.on("/api/wifi/reset", HTTP_POST, [] {
    http.send(200, "application/json", "{\"ok\":true}");
    delay(300);
    wm.resetSettings();
    ESP.restart();
  });
  updater.setup(&http, "/update");                         // upload basic-dryer-d1mini.bin here
  http.onNotFound([] { reply(404, "not found"); });
  http.begin();
  ws.begin();
  ws.onEvent(wsEvent);
  servicesUp = true;
  Serial.printf("online: http://%s/  (%s.local)\n", WiFi.localIP().toString().c_str(), devName);
}

static void startWifi() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(devName, sizeof devName, "filament-dryer-%02x%02x", mac[4], mac[5]);
  char ap[32];
  snprintf(ap, sizeof ap, "FilamentDryer-%02X%02X", mac[4], mac[5]);
  WiFi.mode(WIFI_STA);
  WiFi.hostname(devName);
  wm.setConfigPortalBlocking(false);                      // the dryer keeps working while the hotspot is up
  wm.setConnectTimeout(15);
  wm.setHostname(devName);
  // With a network saved, the hotspot only opens for 3 min if it can't be reached (router down at
  // power-up), then the dryer goes back to trying the saved network. With none saved it stays open.
  if (wm.getWiFiIsSaved()) wm.setConfigPortalTimeout(180);
  if (!wm.autoConnect(ap)) Serial.printf("no saved Wi-Fi: join the hotspot %s to set it up\n", ap);
}

static void netLoop() {
  static bool wasPortal = false;
  wm.process();
  bool portal = wm.getConfigPortalActive();
  if (wasPortal && !portal && WiFi.status() != WL_CONNECTED) {   // hotspot timed out: back to the saved network
    WiFi.mode(WIFI_STA);
    WiFi.begin();
  }
  wasPortal = portal;
  bool up = WiFi.status() == WL_CONNECTED && !wm.getConfigPortalActive();
  if (up && !servicesUp) startServices();
  if (!servicesUp) return;
  MDNS.update();
  http.handleClient();
  ws.loop();
  static uint32_t lastPush = 0;
  if (millis() - lastPush >= 1000 && ws.connectedClients() > 0) {
    lastPush = millis();
    String st = stateJson();
    ws.broadcastTXT(st);
  }
}
#endif

void setup() {
  // outputs off before anything else (level first, so the pin never drives "on" for an instant)
  digitalWrite(pin::HEATER, pin::HEATER_OFF); pinMode(pin::HEATER, OUTPUT);
  digitalWrite(pin::FAN, LOW); pinMode(pin::FAN, OUTPUT);
#if HAS_LED
  digitalWrite(pin::LED, HIGH); pinMode(pin::LED, OUTPUT);
#endif

#ifdef BOARD_ESP01
  WiFi.mode(WIFI_OFF);                                     // no network on the ESP-01S build
  WiFi.forceSleepBegin();
  Serial.begin(115200, SERIAL_8N1, SERIAL_TX_ONLY);       // RX (GPIO3) drives the fan
  pinMode(pin::FAN, OUTPUT); digitalWrite(pin::FAN, LOW);
#else
  Serial.begin(115200);
#endif
  delay(200);
  Serial.printf("\nbasic dryer %s: stops at 15 %% RH, heater capped at 65 C\n", VERSION);
  loadSettings();

#if HAS_I2C
  Wire.begin(pin::SDA_, pin::SCL_);
  Wire.setClock(100000);
#endif
  detectProbe();
  Serial.printf("probe: %s, mode %s\n", probeName(), enabled ? "auto" : "off");
#if HAS_WIFI
  startWifi();
#endif
}

void loop() {
  static uint32_t lastRead = 0, lastLog = 0, lastRetry = 0;
  static bool first = true;
  uint32_t now = millis();

  if (first || now - lastRead >= 2000) {
    first = false;
    lastRead = now;
    if (probe == Probe::None && now - lastRetry >= 10000) {   // probe unplugged at boot: keep looking
      lastRetry = now;
      detectProbe();
      if (probe != Probe::None) Serial.printf("probe found: %s\n", probeName());
    }
    last = readProbe();
    out = controller.update(now, last);
    if (!enabled) {                                            // switched off over the API
      bool fault = out.sensorFault, over = out.overTemp;
      out = basic::Output();
      out.sensorFault = fault;
      out.overTemp = over;
    }
  }

  digitalWrite(pin::HEATER, heaterPwm.on(out.heaterDuty, now) ? pin::HEATER_ON : pin::HEATER_OFF);
  digitalWrite(pin::FAN, out.fan ? HIGH : LOW);
  showLed(now);

  if (now - lastLog >= 10000) {
    lastLog = now;
    if (last.ok)
      Serial.printf("%.1f C  %.1f %% RH  heater %3d %%  fan %s  %s%s\n", last.c, last.rh, (int)(out.heaterDuty * 100 + 0.5f),
                    out.fan ? "on " : "off", !enabled ? "off" : out.drying ? "drying" : "dry",
                    out.overTemp ? "  OVER-TEMPERATURE" : "");
    else
      Serial.printf("no reading (probe %s)%s: heater off\n", probeName(), out.sensorFault ? ", sensor fault" : "");
  }
#if HAS_WIFI
  netLoop();
#endif
  delay(10);
}
