// Basic filament dryer: Wemos D1 Mini (ESP8266), one temperature + humidity probe, a fan and a heater.
//
// While the air in the box is above 15 % RH the fan runs and the heater warms the box; both stop at
// 15 % RH (and start again above 17 %). The heater never pushes the box past 65 °C: full power up to
// 60 °C, then less and less until it's off at 65 °C. No Wi-Fi, no display: the on-board LED and the
// USB serial log (115200 baud) show what it's doing. The logic lives in lib/BasicControl (tested
// on the host with `pio test -e native`).
//
// Pins (D1 Mini labels):
//   D5 (GPIO14)  heater: 500 Ω -> PC817 LED -> GND; the PC817 drives the IRF3205's gate from 12 V
//   D6 (GPIO12)  fan: 500 Ω -> 2N2222A base
//   D2 (GPIO4)   SDA  } AHT20 probe (I2C, 4.7 kΩ pull-ups to 3V3)
//   D1 (GPIO5)   SCL  }
//   D7 (GPIO13)  AM2301 / DHT21 probe data (4.7 kΩ pull-up to 3V3), used when no AHT20 answers
//   D4 (GPIO2)   on-board LED (active low)
#include <Arduino.h>
#include <DHT.h>
#include <ESP8266WiFi.h>
#include <Wire.h>

#include "BasicControl.h"

#define VERSION "0.1.0"

namespace pin {
const uint8_t HEATER = 14, FAN = 12, SDA_ = 4, SCL_ = 5, DHT_ = 13, LED = 2;
}

static basic::Controller controller;
static basic::SlowPwm heaterPwm;
static basic::Output out;
static basic::Reading last;
static DHT dht(pin::DHT_, DHT21);

enum class Probe { None, Aht20, Dht21 };
static Probe probe = Probe::None;

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

static void detectProbe() {
  if (i2cPresent(AHT20) && aht20Init()) {
    probe = Probe::Aht20;
    return;
  }
  dht.begin();
  delay(2100);                                             // the DHT21 needs 2 s after power-up
  float rh = dht.readHumidity(), c = dht.readTemperature();
  probe = (!isnan(rh) && !isnan(c)) ? Probe::Dht21 : Probe::None;
}

static basic::Reading readProbe() {
  basic::Reading r;
  float c = NAN, rh = NAN;
  if (probe == Probe::Aht20) {
    r.ok = aht20Read(c, rh);
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
  bool on;
  if (out.sensorFault || out.overTemp) on = (now / 125) % 2;
  else if (out.heaterDuty > 0) on = true;
  else if (out.fan) on = (now / 500) % 2;
  else on = (now % 3000) < 60;
  digitalWrite(pin::LED, on ? LOW : HIGH);
}

void setup() {
  // outputs off before anything else
  pinMode(pin::HEATER, OUTPUT); digitalWrite(pin::HEATER, LOW);
  pinMode(pin::FAN, OUTPUT); digitalWrite(pin::FAN, LOW);
  pinMode(pin::LED, OUTPUT); digitalWrite(pin::LED, HIGH);

  WiFi.mode(WIFI_OFF);                                     // no network: less heat, less power
  WiFi.forceSleepBegin();

  Serial.begin(115200);
  delay(200);
  Serial.printf("\nbasic dryer %s: stops at 15 %% RH, heater capped at 65 C\n", VERSION);

  Wire.begin(pin::SDA_, pin::SCL_);
  Wire.setClock(100000);
  detectProbe();
  Serial.printf("probe: %s\n", probeName());
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
  }

  digitalWrite(pin::HEATER, heaterPwm.on(out.heaterDuty, now) ? HIGH : LOW);
  digitalWrite(pin::FAN, out.fan ? HIGH : LOW);
  showLed(now);

  if (now - lastLog >= 10000) {
    lastLog = now;
    if (last.ok)
      Serial.printf("%.1f C  %.1f %% RH  heater %3d %%  fan %s  %s%s\n", last.c, last.rh, (int)(out.heaterDuty * 100 + 0.5f),
                    out.fan ? "on " : "off", out.drying ? "drying" : "dry", out.overTemp ? "  OVER-TEMPERATURE" : "");
    else
      Serial.printf("no reading (probe %s)%s: heater off\n", probeName(), out.sensorFault ? ", sensor fault" : "");
  }
  delay(20);
}
