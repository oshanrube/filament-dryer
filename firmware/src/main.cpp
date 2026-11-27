// Filament dryer firmware.
//   dryer-1roll      the 1-roll PCB and its perfboard build (same pins): one load cell, BTT SFS, two fans
//   dryer-1roll-v2   1-roll v2 "twin scale" perfboard (DRYER_BOARD_V2) on an ESP32-S3-DevKitC-1 N16R8:
//                    the axle on two load cells, one blower, no SFS, a 2.8" capacitive touch screen,
//                    chamber capped at 65 °C
//
// FreeRTOS tasks, as in the gate controller:
//   control task  sensors, heater, fans, scale, button, buzzer, OLED. Never waits on the network,
//                 so the heater stays under control while Wi-Fi is down or the setup portal is open.
//   loop()        Wi-Fi and the setup portal, the web page, the REST API, the WebSocket feed, OTA.
//   ui task       (v2 only) the touch screen, in ui_v2.h. Reads the same snapshot and sends the same
//                 commands as the network side, so it can't stall the heater either.
// The control logic itself (modes, PID, cut-outs, scale maths) is lib/DryerCore, unit-tested on the host.
#ifndef DRYER_BOARD_V2
#define DRYER_BOARD_V2 0
#endif

#include <Arduino.h>
#include <ArduinoJson.h>
#include <DallasTemperature.h>
#include <ESPmDNS.h>
#include <HX711.h>
#include <OneWire.h>
#include <Preferences.h>
#if !DRYER_BOARD_V2
#include <U8g2lib.h>
#endif
#include <Update.h>
#include <WebServer.h>
#include <WebSocketsServer.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <esp_task_wdt.h>

#include <initializer_list>

#include "DryerCore.h"
#include "page.h"

// Stamped from the git tag by the CI build (exactly one such line, see .github/workflows/firmware.yml).
#define VERSION "0.1.0-dev"

using namespace dryer;

// ------------------------------------------------------------------------------------------------ pins
namespace pin {
#if DRYER_BOARD_V2
// 1-roll v2 perfboard on an ESP32-S3-DevKitC-1 N16R8 (1-roll-v2/wiring.svg). None of these are
// strapping pins (0, 3, 45, 46) or taken by the octal PSRAM (35-37). Each HX711 has its own clock.
constexpr int HX_SCK = 1;     // left load cell
constexpr int HX_DT = 2;
constexpr int HEATER = 4;     // PC817 -> IRF3205, off at boot
constexpr int BLOWER = 5;     // IRLZ44N gate
constexpr int BUZZER = 6;
constexpr int ONEWIRE = 7;    // DS18B20, heater outlet
constexpr int SDA = 8;        // sensor I2C: SHT40 chamber probe
constexpr int SCL = 9;
constexpr int TFT_CS = 10, TFT_MOSI = 11, TFT_SCK = 12, TFT_DC = 13, TFT_RST = 14;
constexpr int TP_SDA = 15, TP_SCL = 16, TP_INT = 17, TP_RST = 18;   // touch on its own I2C bus (FT6336 is 0x38, as an AHT20)
constexpr int HX2_SCK = 38;   // right load cell
constexpr int HX2_DT = 39;
constexpr int TFT_BL = 47;    // backlight, PWM
constexpr int BUTTON = -1, RUNOUT = -1, MOTION = -1, EXHAUST = -1;   // not fitted
#else
// Same on the 1-roll PCB and the perfboard (see 1-roll/page.html and 1-roll/perfboard/).
constexpr int HX_SCK = 0;
constexpr int HX_DT = 1;
constexpr int ONEWIRE = 2;    // DS18B20, heater outlet
constexpr int RUNOUT = 3;     // BTT SFS V2 runout switch (10 k pull-up)
constexpr int HEATER = 4;     // gate driver / PC817 input, pulled low at boot
constexpr int BLOWER = 5;
constexpr int EXHAUST = 6;
constexpr int SCL = 7;
constexpr int SDA = 8;
constexpr int BUZZER = 10;
constexpr int BUTTON = 20;    // front button to GND (10 k pull-up)
constexpr int MOTION = 21;    // BTT SFS V2 motion pulses, through 1 k
#endif
}  // namespace pin

// ------------------------------------------------------------------------------------------------ shared state
struct Snapshot {
  bool chamberOk = false; float chamberC = 0, chamberRh = 0; const char* chamberSensor = "none";
  bool bayOk = false; float bayC = 0, bayRh = 0;
  bool outletOk = false; float outletC = 0;
  bool scaleOk = false; float grams = 0, gramsLeft = 0, metresLeft = 0, emptyReelG = 0;
  uint32_t motionPulses = 0; float motionMm = 0; bool filamentPresent = false; bool runoutPinHigh = false;
  Mode mode = Mode::Off; Fault fault = Fault::None; bool boost = false; int material = 0;
  float setpointC = 0, duty = 0; bool heaterOn = false, blower = false, exhaust = false;
  uint32_t dryRemainingS = 0, modeElapsedS = 0;
  float mmPerPulse = 2.88f; bool runoutInvert = false;
  // 1-roll v2: two load cells
  float cellG[2] = {0, 0}; bool scaleCalibrated = false; float refC = 25; float driftGPerC[2] = {0, 0};
  bool driftLearned = false, learning = false; uint32_t learnSamples = 0; float learnSpanC = 0;
  const char* calStatus = "";
};
static Snapshot g_snap;
static portMUX_TYPE g_mux = portMUX_INITIALIZER_UNLOCKED;

static Snapshot snapshot() {
  Snapshot s;
  portENTER_CRITICAL(&g_mux);
  s = g_snap;
  portEXIT_CRITICAL(&g_mux);
  return s;
}

enum class CmdType : uint8_t { SetMode, SetMaterial, ClearFault, Tare, Calibrate, SetEmptyReel, SetMmPerPulse, SetRunoutInvert, ResetMotion,
                              CalPoint, LearnDrift, SetTouchFlip, Beep };
enum class CalStep : int { Left = 0, Right = 1, Centre = 2 };
struct Cmd { CmdType type; Mode mode; int material; float value; };
static QueueHandle_t g_cmds;
static volatile bool g_wifiResetRequested = false;
static volatile uint8_t g_touchFlip = 0;   // v2: bit 0 mirrors touch x, bit 1 mirrors y (some panels are fitted flipped)

static bool sendCmd(const Cmd& c) { return xQueueSend(g_cmds, &c, 0) == pdTRUE; }

// ------------------------------------------------------------------------------------------------ settings
static Preferences prefs;
static ScaleCal g_cal;

__attribute__((unused)) static void saveCal() {
  prefs.putFloat("offset", g_cal.offset);
  prefs.putFloat("scale", g_cal.scale);
  prefs.putFloat("empty", g_cal.emptyReelG);
}

// 1-roll v2: both cells' calibration, kept in flash
static TwinScaleCal g_twin;
__attribute__((unused)) static void saveTwin() {
  prefs.putFloat("o1", g_twin.offset[0]); prefs.putFloat("o2", g_twin.offset[1]);
  prefs.putFloat("k1", g_twin.gramsPerCount[0]); prefs.putFloat("k2", g_twin.gramsPerCount[1]);
  prefs.putFloat("d1", g_twin.driftPerC[0]); prefs.putFloat("d2", g_twin.driftPerC[1]);
  prefs.putFloat("refc", g_twin.refC); prefs.putFloat("empty", g_twin.emptyReelG);
}
__attribute__((unused)) static void loadTwin() {
  g_twin.offset[0] = prefs.getFloat("o1", 0); g_twin.offset[1] = prefs.getFloat("o2", 0);
  g_twin.gramsPerCount[0] = prefs.getFloat("k1", 0); g_twin.gramsPerCount[1] = prefs.getFloat("k2", 0);
  g_twin.driftPerC[0] = prefs.getFloat("d1", 0); g_twin.driftPerC[1] = prefs.getFloat("d2", 0);
  g_twin.refC = prefs.getFloat("refc", 25); g_twin.emptyReelG = prefs.getFloat("empty", 0);
}

// ------------------------------------------------------------------------------------------------ sensors
static uint8_t crc8(const uint8_t* d, size_t n) {   // Sensirion / Aosong CRC-8, poly 0x31, init 0xFF
  uint8_t crc = 0xFF;
  for (size_t i = 0; i < n; i++) {
    crc ^= d[i];
    for (int b = 0; b < 8; b++) crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
  }
  return crc;
}

static bool i2cPresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

static bool sht4xRead(uint8_t addr, float& t, float& rh) {
  Wire.beginTransmission(addr);
  Wire.write(0xFD);                                   // high-precision measurement
  if (Wire.endTransmission() != 0) return false;
  vTaskDelay(pdMS_TO_TICKS(10));
  if (Wire.requestFrom((int)addr, 6) != 6) return false;
  uint8_t b[6];
  for (int i = 0; i < 6; i++) b[i] = Wire.read();
  if (crc8(b, 2) != b[2] || crc8(b + 3, 2) != b[5]) return false;
  t = -45.0f + 175.0f * (float)((b[0] << 8) | b[1]) / 65535.0f;
  rh = -6.0f + 125.0f * (float)((b[3] << 8) | b[4]) / 65535.0f;
  rh = rh < 0 ? 0 : (rh > 100 ? 100 : rh);
  return true;
}

static const uint8_t AHT20 = 0x38;
static bool aht20Init() {
  Wire.beginTransmission(AHT20);
  Wire.write(0xBE); Wire.write(0x08); Wire.write(0x00);   // calibrate / initialise
  if (Wire.endTransmission() != 0) return false;
  vTaskDelay(pdMS_TO_TICKS(20));
  return true;
}

static bool aht20Read(float& t, float& rh) {
  Wire.beginTransmission(AHT20);
  Wire.write(0xAC); Wire.write(0x33); Wire.write(0x00);   // trigger
  if (Wire.endTransmission() != 0) return false;
  vTaskDelay(pdMS_TO_TICKS(85));
  if (Wire.requestFrom((int)AHT20, 7) != 7) return false;
  uint8_t b[7];
  for (int i = 0; i < 7; i++) b[i] = Wire.read();
  if (b[0] & 0x80) return false;                            // still busy
  if (crc8(b, 6) != b[6]) return false;
  uint32_t hr = ((uint32_t)b[1] << 12) | ((uint32_t)b[2] << 4) | (b[3] >> 4);
  uint32_t tr = (((uint32_t)b[3] & 0x0F) << 16) | ((uint32_t)b[4] << 8) | b[5];
  rh = hr * 100.0f / 1048576.0f;
  t = tr * 200.0f / 1048576.0f - 50.0f;
  return true;
}

enum class ChamberType : uint8_t { None, Sht4x, Aht20 };
static const char* chamberTypeName(ChamberType c) {
  return c == ChamberType::Sht4x ? "sht40" : (c == ChamberType::Aht20 ? "aht20" : "none");
}

// ------------------------------------------------------------------------------------------------ control task
static OneWire g_ow(pin::ONEWIRE);
static DallasTemperature g_ds(&g_ow);
static HX711 g_hx;
#if !DRYER_BOARD_V2
// SH1106 1.3" OLED. Passing the pins makes U8g2 start Wire on GPIO7/8, not the core's defaults.
static U8G2_SH1106_128X64_NONAME_F_HW_I2C g_sh1106(U8G2_R0, U8X8_PIN_NONE, pin::SCL, pin::SDA);
static U8G2* g_oled = &g_sh1106;
#endif
static volatile uint32_t g_motionPulses = 0;
__attribute__((unused)) static void IRAM_ATTR onMotion() { g_motionPulses = g_motionPulses + 1; }

struct Beeper {
  // a queue of on/off steps in ms, played from the control task
  uint16_t steps[12]; uint8_t n = 0, i = 0; uint32_t stepStart = 0; bool playing = false;
  void play(std::initializer_list<uint16_t> s, uint32_t now) {
    n = 0;
    for (uint16_t v : s) if (n < 12) steps[n++] = v;
    i = 0; stepStart = now; playing = n > 0;
  }
  bool update(uint32_t now) {   // true = buzzer on
    if (!playing) return false;
    while (i < n && now - stepStart >= steps[i]) { stepStart += steps[i]; i++; }
    if (i >= n) { playing = false; return false; }
    return (i % 2) == 0;
  }
};

#if !DRYER_BOARD_V2
static void drawOled(const Snapshot& s, const char* netLine) {
  char buf[32];
  g_oled->clearBuffer();
  g_oled->setFont(u8g2_font_6x12_tr);
  if (s.fault != Fault::None) {
    snprintf(buf, sizeof buf, "FAULT %s", faultName(s.fault));
  } else if (s.mode == Mode::Dry) {
    uint32_t m = s.dryRemainingS / 60;
    snprintf(buf, sizeof buf, "DRY %s %.0fC %lu:%02lu", MATERIALS[s.material].name, s.setpointC, (unsigned long)(m / 60), (unsigned long)(m % 60));
  } else if (s.mode == Mode::KeepDry) {
    snprintf(buf, sizeof buf, s.boost ? "KEEP DRY (boost 45C)" : "KEEP DRY");
  } else if (s.mode == Mode::Print) {
    snprintf(buf, sizeof buf, "PRINT %s %.0fC", MATERIALS[s.material].name, s.setpointC);
  } else {
    snprintf(buf, sizeof buf, "OFF  (%s)", MATERIALS[s.material].name);
  }
  g_oled->drawStr(0, 11, buf);
  if (s.chamberOk) snprintf(buf, sizeof buf, "Chamber %.1fC %.0f%%", s.chamberC, s.chamberRh);
  else snprintf(buf, sizeof buf, "Chamber: no sensor");
  g_oled->drawStr(0, 24, buf);
  if (s.outletOk) snprintf(buf, sizeof buf, "Outlet %.0fC  heat %d%%", s.outletC, (int)(s.duty * 100 + 0.5f));
  else snprintf(buf, sizeof buf, "Outlet: no probe");
  g_oled->drawStr(0, 37, buf);
  if (s.scaleOk) snprintf(buf, sizeof buf, "Reel %.0f g  %.0f m", s.gramsLeft, s.metresLeft);
  else snprintf(buf, sizeof buf, "Scale: no reading");
  g_oled->drawStr(0, 50, buf);
  g_oled->drawStr(0, 63, netLine);
  g_oled->sendBuffer();
}

#endif

static char g_netLine[32] = "Wi-Fi: starting";

static void controlTask(void*) {
  esp_task_wdt_add(NULL);

  Wire.begin(pin::SDA, pin::SCL, 100000);
#if !DRYER_BOARD_V2
  g_oled->setBusClock(100000);
  g_oled->begin();
#endif

  g_ds.begin();
  g_ds.setResolution(11);
  g_ds.setWaitForConversion(false);
  g_ds.requestTemperatures();

  g_hx.begin(pin::HX_DT, pin::HX_SCK);

  if (pin::BUTTON >= 0) pinMode(pin::BUTTON, INPUT_PULLUP);
#if DRYER_BOARD_V2
  static HX711 hx2;
  hx2.begin(pin::HX2_DT, pin::HX2_SCK);
  Median<100> median2;                    // right cell
  DriftFit drift;
  bool learning = false;
  uint32_t learnStartMs = 0, lastLearnSample = 0;
  float calNetL = 0, calNetR = 0, calGrams = 0;   // the first point of a two-point calibration
  bool haveCalPoint = false;
  const char* calStatus = g_twin.calibrated() ? "" : "not calibrated";
  uint32_t hx2AtMs = 0;
#else
  pinMode(pin::RUNOUT, INPUT_PULLUP);
  pinMode(pin::MOTION, INPUT);
  attachInterrupt(digitalPinToInterrupt(pin::MOTION), onMotion, RISING);
#endif

  Controller ctl;
  ctl.setMaterial(prefs.getInt("material", 0));
#if DRYER_BOARD_V2
  ctl.setMaxC(65);                        // the load cells sit in the chamber: rated to about 65 °C
#endif
  HeaterWindow window(2000, 100);
  Median<100> median;                     // 10 s of 10 Hz HX711 reads
  Beeper beeper;
  float mmPerPulse = prefs.getFloat("mmpp", 2.88f);
  bool runoutInvert = prefs.getBool("runinv", false);
  uint32_t motionBase = 0;
  (void)motionBase;
  float chamberC = 0, chamberRh = 0, bayC = 0, bayRh = 0, outletC = 0;
  uint32_t chamberAtMs = 0, outletAtMs = 0, bayAtMs = 0, hxAtMs = 0;
  bool haveChamber = false, haveOutlet = false, haveBay = false;

  // restore keep-dry after a power cut; any other mode starts off
  uint32_t now = millis();
  if (prefs.getUChar("mode", 0) == (uint8_t)Mode::KeepDry) ctl.setMode(Mode::KeepDry, now);

  ChamberType chamberType = ChamberType::None;
  bool bayPresent = false;
  uint32_t lastDs = 0, lastI2c = 0, lastDetect = 0, lastCtl = 0, lastOled = 0, lastSnap = 0;
  Outputs out;
  Mode lastMode = ctl.mode();
  Fault lastFault = Fault::None;
  uint32_t lastFaultBeep = 0;
  // button
#if !DRYER_BOARD_V2
  bool btnDown = false; uint32_t btnSince = 0;
#else
  (void)lastOled;
#endif

  TickType_t wake = xTaskGetTickCount();
  for (;;) {
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(20));
    esp_task_wdt_reset();
    now = millis();

    // ---- commands from the network task
    Cmd c;
    while (xQueueReceive(g_cmds, &c, 0) == pdTRUE) {
      switch (c.type) {
        case CmdType::SetMaterial: ctl.setMaterial(c.material); prefs.putInt("material", ctl.material()); break;
        case CmdType::SetMode: ctl.setMode(c.mode, now); beeper.play({60}, now); break;
        case CmdType::ClearFault: ctl.clearFault(now); beeper.play({60}, now); break;
#if DRYER_BOARD_V2
        case CmdType::Tare:
          if (median.count() && median2.count()) {
            g_twin.tare(median.value(), median2.value(), haveChamber ? chamberC : g_twin.refC);
            saveTwin(); calStatus = "tared"; beeper.play({60, 80, 60}, now);
          }
          break;
        case CmdType::CalPoint: {
          if (!median.count() || !median2.count()) { calStatus = "no scale reading"; beeper.play({400}, now); break; }
          float tc = haveChamber ? chamberC : g_twin.refC;
          float nl = g_twin.net(0, median.value(), tc), nr = g_twin.net(1, median2.value(), tc);
          float kl, kr;
          CalStep step = (CalStep)c.material;
          if (step == CalStep::Centre) {
            if (solveCentre(nl, nr, c.value, &kl, &kr)) {
              g_twin.gramsPerCount[0] = kl; g_twin.gramsPerCount[1] = kr; saveTwin();
              calStatus = "calibrated (middle)"; beeper.play({60, 80, 60}, now);
            } else { calStatus = "failed: is the weight in the middle?"; beeper.play({400}, now); }
            haveCalPoint = false;
          } else if (!haveCalPoint) {
            calNetL = nl; calNetR = nr; calGrams = c.value; haveCalPoint = true;
            calStatus = step == CalStep::Left ? "left saved: now the right end" : "right saved: now the left end";
            beeper.play({60}, now);
          } else {
            bool ok = c.value > calGrams - 1 && c.value < calGrams + 1 &&
                      solveTwoPoint(calNetL, calNetR, nl, nr, c.value, &kl, &kr);
            if (ok) {
              g_twin.gramsPerCount[0] = kl; g_twin.gramsPerCount[1] = kr; saveTwin();
              calStatus = "calibrated"; beeper.play({60, 80, 60}, now);
            } else { calStatus = "failed: move the weight to the other end"; beeper.play({400}, now); }
            haveCalPoint = false;
          }
          break;
        }
        case CmdType::LearnDrift:
          if (c.value > 0) {
            drift.reset(); learning = true; learnStartMs = now; lastLearnSample = 0;
            calStatus = "learning drift: keep the load the same";
          } else if (learning) {
            float dl, dr;
            learning = false;
            if (drift.solve(&dl, &dr)) { g_twin.driftPerC[0] = dl; g_twin.driftPerC[1] = dr; saveTwin(); calStatus = "drift learned"; }
            else calStatus = "drift: not enough temperature range";
          }
          break;
        case CmdType::SetTouchFlip: g_touchFlip = (uint8_t)(c.material & 3); prefs.putUChar("tflip", g_touchFlip); break;
        case CmdType::Beep: beeper.play({(uint16_t)(c.value > 0 ? c.value : 30)}, now); break;
        case CmdType::SetEmptyReel: g_twin.emptyReelG = c.value; saveTwin(); break;
        case CmdType::Calibrate: break;
#else
        case CmdType::Tare: if (median.count()) { g_cal.tare(median.value()); saveCal(); beeper.play({60, 80, 60}, now); } break;
        case CmdType::Calibrate:
          if (median.count() && g_cal.calibrate(median.value(), c.value)) { saveCal(); beeper.play({60, 80, 60}, now); }
          break;
        case CmdType::SetEmptyReel: g_cal.emptyReelG = c.value; saveCal(); break;
        case CmdType::CalPoint: case CmdType::LearnDrift: case CmdType::SetTouchFlip: case CmdType::Beep: break;
#endif
        case CmdType::SetMmPerPulse: if (c.value > 0) { mmPerPulse = c.value; prefs.putFloat("mmpp", mmPerPulse); } break;
        case CmdType::SetRunoutInvert: runoutInvert = c.value != 0; prefs.putBool("runinv", runoutInvert); break;
        case CmdType::ResetMotion: motionBase = g_motionPulses; break;
      }
    }

    // ---- sensors
    if (now - lastDetect >= 10000 || lastDetect == 0) {       // (re)detect hot-plugged I2C sensors
      lastDetect = now;
      if (chamberType == ChamberType::None) {
        if (i2cPresent(0x44)) chamberType = ChamberType::Sht4x;
        else if (i2cPresent(AHT20) && aht20Init()) chamberType = ChamberType::Aht20;
      }
      bayPresent = i2cPresent(0x45);
    }
    if (now - lastI2c >= 2000) {
      lastI2c = now;
      float t, h;
      bool okc = chamberType == ChamberType::Sht4x ? sht4xRead(0x44, t, h)
               : chamberType == ChamberType::Aht20 ? aht20Read(t, h) : false;
      if (okc) { chamberC = t; chamberRh = h; chamberAtMs = now; haveChamber = true; }
      if (bayPresent && sht4xRead(0x45, t, h)) { bayC = t; bayRh = h; bayAtMs = now; haveBay = true; }
    }
    if (now - lastDs >= 1000) {
      lastDs = now;
      if (g_ds.isConversionComplete()) {
        float t = g_ds.getTempCByIndex(0);
        if (t != DEVICE_DISCONNECTED_C && t > -40 && t < 150 && !(t == 85.0f && !haveOutlet)) {
          outletC = t; outletAtMs = now; haveOutlet = true;
        }
      }
      g_ds.requestTemperatures();
    }
    if (g_hx.is_ready()) { median.add((float)g_hx.read()); hxAtMs = now; }
#if DRYER_BOARD_V2
    if (hx2.is_ready()) { median2.add((float)hx2.read()); hx2AtMs = now; }
#endif

    bool chamberOk = haveChamber && now - chamberAtMs < 6000;
    bool outletOk = haveOutlet && now - outletAtMs < 4000;
    bool bayOk = haveBay && now - bayAtMs < 6000;
    bool scaleOk = median.count() > 0 && now - hxAtMs < 2000;
#if DRYER_BOARD_V2
    scaleOk = scaleOk && median2.count() > 0 && now - hx2AtMs < 2000;
    // drift learning: one sample a minute under a constant load; ends by itself after 8 h, or once
    // the dry cycle that heated it is over (with at least 25 °C of range)
    if (learning && scaleOk && chamberOk && now - lastLearnSample >= 60000) {
      lastLearnSample = now;
      drift.add(chamberC, median.value(), median2.value());
    }
    if (learning && (now - learnStartMs >= 8UL * 3600 * 1000 || (drift.spanC() >= 25 && ctl.mode() != Mode::Dry))) {
      Cmd stop{}; stop.type = CmdType::LearnDrift; stop.value = 0; sendCmd(stop);
    }
#endif

    // ---- control, twice a second
    if (now - lastCtl >= 500) {
      lastCtl = now;
      Inputs in;
      in.nowMs = now; in.chamberOk = chamberOk; in.chamberC = chamberC; in.chamberRh = chamberRh;
      in.outletOk = outletOk; in.outletC = outletC;
      out = ctl.update(in);
      if (ctl.mode() != lastMode) {
        if (lastMode == Mode::Dry && ctl.mode() == Mode::KeepDry) beeper.play({150, 100, 150, 100, 150}, now);   // dry done
        lastMode = ctl.mode();
        prefs.putUChar("mode", (uint8_t)lastMode);
      }
      if (ctl.fault() != Fault::None && (lastFault == Fault::None || now - lastFaultBeep >= 10000)) {
        beeper.play({200, 200, 200, 200, 200}, now);
        lastFaultBeep = now;
      }
      lastFault = ctl.fault();
    }
    bool heatOn = window.on(out.heaterDuty, now);
    digitalWrite(pin::HEATER, heatOn ? HIGH : LOW);
    digitalWrite(pin::BLOWER, out.blower ? HIGH : LOW);
    if (pin::EXHAUST >= 0) digitalWrite(pin::EXHAUST, out.exhaust ? HIGH : LOW);
    digitalWrite(pin::BUZZER, beeper.update(now) ? HIGH : LOW);

#if !DRYER_BOARD_V2
    // ---- front button: short = acknowledge a fault, or next mode; 3 s = tare; 10 s = forget Wi-Fi
    bool down = digitalRead(pin::BUTTON) == LOW;
    if (down && !btnDown) { btnDown = true; btnSince = now; }
    if (!down && btnDown) {
      btnDown = false;
      uint32_t held = now - btnSince;
      if (held >= 10000) { g_wifiResetRequested = true; beeper.play({500}, now); }
      else if (held >= 3000) { Cmd t{}; t.type = CmdType::Tare; sendCmd(t); }
      else if (held >= 40) {
        if (ctl.fault() != Fault::None) ctl.clearFault(now);
        else {
          static const Mode order[] = {Mode::Off, Mode::Dry, Mode::KeepDry, Mode::Print};
          int idx = 0;
          for (int k = 0; k < 4; k++) if (order[k] == ctl.mode()) idx = k;
          ctl.setMode(order[(idx + 1) % 4], now);
        }
        beeper.play({60}, now);
      }
    }
#endif

    // ---- publish
    if (now - lastSnap >= 200) {
      lastSnap = now;
      Snapshot s;
#if DRYER_BOARD_V2
      float tc = chamberOk ? chamberC : g_twin.refC;
      float grams = 0;
      if (scaleOk) {
        s.cellG[0] = g_twin.cellGrams(0, median.value(), tc);
        s.cellG[1] = g_twin.cellGrams(1, median2.value(), tc);
        grams = s.cellG[0] + s.cellG[1];
      }
      float emptyReel = g_twin.emptyReelG;
      s.scaleCalibrated = g_twin.calibrated(); s.refC = g_twin.refC;
      s.driftGPerC[0] = g_twin.driftPerC[0] * g_twin.gramsPerCount[0];
      s.driftGPerC[1] = g_twin.driftPerC[1] * g_twin.gramsPerCount[1];
      s.driftLearned = g_twin.driftPerC[0] != 0 || g_twin.driftPerC[1] != 0;
      s.learning = learning; s.learnSamples = drift.count(); s.learnSpanC = drift.spanC();
      s.calStatus = calStatus;
      bool runHigh = false;
      uint32_t pulses = 0;
#else
      float grams = scaleOk ? g_cal.gramsFromRaw(median.value()) : 0;
      float emptyReel = g_cal.emptyReelG;
      bool runHigh = digitalRead(pin::RUNOUT) == HIGH;
      uint32_t pulses = g_motionPulses - motionBase;
#endif
      float left = grams - emptyReel;
      if (left < 0) left = 0;
      s.chamberOk = chamberOk; s.chamberC = chamberC; s.chamberRh = chamberRh; s.chamberSensor = chamberTypeName(chamberType);
      s.bayOk = bayOk; s.bayC = bayC; s.bayRh = bayRh;
      s.outletOk = outletOk; s.outletC = outletC;
      s.scaleOk = scaleOk; s.grams = grams; s.gramsLeft = left; s.emptyReelG = emptyReel;
      s.metresLeft = metresLeft(left, MATERIALS[ctl.material()].density);
      s.motionPulses = pulses; s.motionMm = pulses * mmPerPulse;
      s.runoutPinHigh = runHigh; s.filamentPresent = runHigh != runoutInvert;
      s.mode = ctl.mode(); s.fault = ctl.fault(); s.boost = ctl.boosting(); s.material = ctl.material();
      s.setpointC = ctl.setpoint(); s.duty = ctl.lastDuty(); s.heaterOn = heatOn; s.blower = out.blower; s.exhaust = out.exhaust;
      s.dryRemainingS = ctl.dryRemainingS(now); s.modeElapsedS = ctl.modeElapsedMs(now) / 1000;
      s.mmPerPulse = mmPerPulse; s.runoutInvert = runoutInvert;
      portENTER_CRITICAL(&g_mux);
      g_snap = s;
      portEXIT_CRITICAL(&g_mux);
    }
#if !DRYER_BOARD_V2
    if (now - lastOled >= 1000) {
      lastOled = now;
      char line[32];
      portENTER_CRITICAL(&g_mux);
      memcpy(line, g_netLine, sizeof line);
      portEXIT_CRITICAL(&g_mux);
      if (btnDown && now - btnSince >= 10000) strcpy(line, "Release: forget Wi-Fi");
      else if (btnDown && now - btnSince >= 3000) strcpy(line, "Release: tare scale");
      drawOled(snapshot(), line);
    }
#endif
  }
}

// ------------------------------------------------------------------------------------------------ network
static WiFiManager g_wm;
static WebServer g_http(80);
static WebSocketsServer g_ws(81);
static bool g_servicesUp = false;
static String g_name;

static String stateJson() {
  Snapshot s = snapshot();
  StaticJsonDocument<1536> d;
  d["version"] = VERSION;
  d["name"] = g_name;
  d["uptime_s"] = millis() / 1000;
  d["rssi"] = WiFi.RSSI();
  d["ip"] = WiFi.localIP().toString();
  d["mode"] = modeName(s.mode);
  d["boost"] = s.boost;
  d["material"] = MATERIALS[s.material].name;
  d["setpoint_c"] = s.setpointC;
  d["dry_remaining_s"] = s.dryRemainingS;
  d["mode_elapsed_s"] = s.modeElapsedS;
  d["fault"] = faultName(s.fault);
  JsonObject ch = d.createNestedObject("chamber");
  ch["ok"] = s.chamberOk; ch["c"] = s.chamberC; ch["rh"] = s.chamberRh; ch["sensor"] = s.chamberSensor;
  JsonObject bay = d.createNestedObject("bay");
  bay["ok"] = s.bayOk; bay["c"] = s.bayC; bay["rh"] = s.bayRh;
  JsonObject ou = d.createNestedObject("outlet");
  ou["ok"] = s.outletOk; ou["c"] = s.outletC;
  JsonObject h = d.createNestedObject("heater");
  h["duty"] = s.duty; h["on"] = s.heaterOn;
  d["blower"] = s.blower;
  JsonObject sc = d.createNestedObject("scale");
  sc["ok"] = s.scaleOk; sc["grams"] = s.grams; sc["empty_reel_g"] = s.emptyReelG; sc["grams_left"] = s.gramsLeft; sc["metres_left"] = s.metresLeft;
#if DRYER_BOARD_V2
  d["board"] = "1roll-v2";
  d["max_c"] = 65;
  d["touch_flip"] = g_touchFlip;
  sc["calibrated"] = s.scaleCalibrated;
  sc["cal_status"] = s.calStatus;
  JsonArray cells = sc.createNestedArray("cells");
  cells.add(s.cellG[0]); cells.add(s.cellG[1]);
  JsonObject dr = sc.createNestedObject("drift");
  dr["learned"] = s.driftLearned; dr["learning"] = s.learning; dr["samples"] = s.learnSamples; dr["span_c"] = s.learnSpanC;
  dr["ref_c"] = s.refC;
  JsonArray gpc = dr.createNestedArray("g_per_c");
  gpc.add(s.driftGPerC[0]); gpc.add(s.driftGPerC[1]);
#else
  d["board"] = "1roll";
  d["exhaust"] = s.exhaust;
  JsonObject fi = d.createNestedObject("filament");
  fi["present"] = s.filamentPresent; fi["runout_pin_high"] = s.runoutPinHigh; fi["runout_invert"] = s.runoutInvert;
  fi["motion_mm"] = s.motionMm; fi["motion_pulses"] = s.motionPulses; fi["mm_per_pulse"] = s.mmPerPulse;
#endif
  String out;
  serializeJson(d, out);
  return out;
}

// One handler for REST bodies and WebSocket messages. Returns "" on success, else an error.
static String handleCommand(const String& cmd, JsonVariantConst body) {
  Cmd c{};
  if (cmd == "mode") {
    if (body.containsKey("material")) {
      int m = materialIndex(body["material"] | "");
      if (m < 0) return "unknown material";
      c.type = CmdType::SetMaterial; c.material = m; sendCmd(c);
    }
    if (body.containsKey("mode")) {
      Mode m;
      if (!parseMode(body["mode"] | "", &m)) return "unknown mode";
      c.type = CmdType::SetMode; c.mode = m; sendCmd(c);
    }
    return "";
  }
  if (cmd == "clear_fault") { c.type = CmdType::ClearFault; sendCmd(c); return ""; }
  if (cmd == "tare") { c.type = CmdType::Tare; sendCmd(c); return ""; }
  if (cmd == "reset_motion") { c.type = CmdType::ResetMotion; sendCmd(c); return ""; }
  if (cmd == "calibrate") {
    float g = body["grams"] | 0.0f;
    if (g <= 0) return "grams must be > 0";
#if DRYER_BOARD_V2
    // two load cells: {"grams":500,"step":"left"} then "right"; or one "middle" step
    String step = body["step"] | "";
    if (step == "left") c.material = (int)CalStep::Left;
    else if (step == "right") c.material = (int)CalStep::Right;
    else if (step == "middle" || step == "centre" || step == "center") c.material = (int)CalStep::Centre;
    else return "step must be left, right or middle";
    c.type = CmdType::CalPoint; c.value = g; sendCmd(c); return "";
#else
    c.type = CmdType::Calibrate; c.value = g; sendCmd(c); return "";
#endif
  }
#if DRYER_BOARD_V2
  if (cmd == "learn_drift") {
    c.type = CmdType::LearnDrift; c.value = (body["start"] | false) ? 1 : 0; sendCmd(c); return "";
  }
#endif
  if (cmd == "config") {
    if (body.containsKey("empty_reel_g")) { c.type = CmdType::SetEmptyReel; c.value = body["empty_reel_g"] | 0.0f; sendCmd(c); }
    if (body.containsKey("mm_per_pulse")) { c.type = CmdType::SetMmPerPulse; c.value = body["mm_per_pulse"] | 0.0f; sendCmd(c); }
    if (body.containsKey("runout_invert")) { c.type = CmdType::SetRunoutInvert; c.value = (body["runout_invert"] | false) ? 1 : 0; sendCmd(c); }
#if DRYER_BOARD_V2
    if (body.containsKey("touch_flip")) {   // 0..3: bit 0 mirrors x, bit 1 mirrors y
      int f = body["touch_flip"] | -1;
      if (f < 0 || f > 3) return "touch_flip must be 0-3";
      c.type = CmdType::SetTouchFlip; c.material = f; sendCmd(c);
    }
#endif
    return "";
  }
  return "unknown command";
}

static void reply(int code, const String& err) {
  g_http.sendHeader("Access-Control-Allow-Origin", "*");
  if (err.length()) g_http.send(code, "application/json", "{\"error\":\"" + err + "\"}");
  else g_http.send(200, "application/json", stateJson());
}

static void restCommand(const String& cmd) {
  StaticJsonDocument<256> body;
  if (g_http.hasArg("plain") && g_http.arg("plain").length()) {
    if (deserializeJson(body, g_http.arg("plain"))) { reply(400, "bad json"); return; }
  }
  String err = handleCommand(cmd, body.as<JsonVariantConst>());
  delay(60);   // let the control task apply it before the reply reads the state back
  reply(err.length() ? 400 : 200, err);
}

static void wsEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t len) {
  if (type == WStype_CONNECTED) {
    String s = stateJson();
    g_ws.sendTXT(num, s);
  } else if (type == WStype_TEXT) {
    StaticJsonDocument<256> body;
    if (deserializeJson(body, payload, len)) { g_ws.sendTXT(num, "{\"error\":\"bad json\"}"); return; }
    String err = handleCommand(body["cmd"] | "", body.as<JsonVariantConst>());
    if (err.length()) { String m = "{\"error\":\"" + err + "\"}"; g_ws.sendTXT(num, m); }
  }
}

static void startServices() {
  MDNS.begin(g_name.c_str());
  MDNS.addService("http", "tcp", 80);
  MDNS.addService("filament-dryer", "tcp", 81);

  g_http.on("/", HTTP_GET, [] { g_http.send_P(200, "text/html", PAGE_HTML); });
  g_http.on("/api/state", HTTP_GET, [] { reply(200, ""); });
  g_http.on("/api/mode", HTTP_POST, [] { restCommand("mode"); });
  g_http.on("/api/fault/clear", HTTP_POST, [] { restCommand("clear_fault"); });
  g_http.on("/api/tare", HTTP_POST, [] { restCommand("tare"); });
  g_http.on("/api/calibrate", HTTP_POST, [] { restCommand("calibrate"); });
  g_http.on("/api/config", HTTP_POST, [] { restCommand("config"); });
  g_http.on("/api/motion/reset", HTTP_POST, [] { restCommand("reset_motion"); });
  g_http.on("/api/scale/learn", HTTP_POST, [] { restCommand("learn_drift"); });   // 1-roll v2: {"start":true|false}
  // firmware update: POST the app .bin (dryer-1roll.bin) as a file field
  g_http.on("/update", HTTP_GET, [] { g_http.send_P(200, "text/html", UPDATE_HTML); });
  g_http.on(
      "/update", HTTP_POST,
      [] {
        bool ok = !Update.hasError();
        g_http.send(ok ? 200 : 500, "text/plain", ok ? "updated, restarting" : Update.errorString());
        if (ok) { delay(500); ESP.restart(); }
      },
      [] {
        HTTPUpload& up = g_http.upload();
        if (up.status == UPLOAD_FILE_START) Update.begin(UPDATE_SIZE_UNKNOWN);
        else if (up.status == UPLOAD_FILE_WRITE) Update.write(up.buf, up.currentSize);
        else if (up.status == UPLOAD_FILE_END) Update.end(true);
      });
  g_http.onNotFound([] { reply(404, "not found"); });
  g_http.begin();
  g_ws.begin();
  g_ws.onEvent(wsEvent);
  g_servicesUp = true;
}

#if DRYER_BOARD_V2
#include "ui_v2.h"
#endif

void setup() {
  // outputs low before anything else (the board also pulls the gates low)
  for (int p : {pin::HEATER, pin::BLOWER, pin::EXHAUST, pin::BUZZER})
    if (p >= 0) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }
  Serial.begin(115200);
  prefs.begin("dryer", false);
  g_cal.offset = prefs.getFloat("offset", 0);
  g_cal.scale = prefs.getFloat("scale", 1);
  g_cal.emptyReelG = prefs.getFloat("empty", 0);
#if DRYER_BOARD_V2
  loadTwin();
  g_touchFlip = prefs.getUChar("tflip", 0) & 3;
#endif

  uint8_t mac[6];
  WiFi.macAddress(mac);
  char name[32];
  snprintf(name, sizeof name, "filament-dryer-%02x%02x", mac[4], mac[5]);
  g_name = name;

  g_cmds = xQueueCreate(16, sizeof(Cmd));
  esp_task_wdt_init(10, true);              // the control task resets the chip if it ever stalls 10 s
  xTaskCreate(controlTask, "control", 8192, nullptr, 2, nullptr);
#if DRYER_BOARD_V2
  ui::start();                              // touch screen, its own task (ui_v2.h)
#endif

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(name);
  g_wm.setConfigPortalBlocking(false);
  g_wm.setHostname(name);
  char ap[32];
  snprintf(ap, sizeof ap, "FilamentDryer-%02X%02X", mac[4], mac[5]);
  if (!g_wm.autoConnect(ap)) Serial.printf("no saved Wi-Fi: setup hotspot %s is open\n", ap);
  Serial.printf("filament dryer %s, %s\n", VERSION, name);
}

void loop() {
  g_wm.process();
  bool up = WiFi.status() == WL_CONNECTED && !g_wm.getConfigPortalActive();
  if (up && !g_servicesUp) startServices();

  char line[32];
  if (up) snprintf(line, sizeof line, "%s", WiFi.localIP().toString().c_str());
  else if (g_wm.getConfigPortalActive()) snprintf(line, sizeof line, "Setup: %s", WiFi.softAPSSID().c_str());
  else snprintf(line, sizeof line, "Wi-Fi: connecting");
  portENTER_CRITICAL(&g_mux);
  memcpy(g_netLine, line, sizeof line);
  portEXIT_CRITICAL(&g_mux);

  if (g_servicesUp) {
    g_http.handleClient();
    g_ws.loop();
    static uint32_t lastPush = 0;
    if (millis() - lastPush >= 1000 && g_ws.connectedClients() > 0) {
      lastPush = millis();
      String s = stateJson();
      g_ws.broadcastTXT(s);
    }
  }
  if (g_wifiResetRequested) {
    g_wifiResetRequested = false;
    g_wm.resetSettings();
    delay(500);
    ESP.restart();
  }
  delay(2);
}
