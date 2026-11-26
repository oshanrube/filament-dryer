// The basic dryer's whole decision: when the fan and heater run, and how hard the heater works.
// Plain C++ (no Arduino), tested on the host with `pio test -e native`.
#pragma once
#include <stdint.h>

namespace basic {

struct Settings {
  float stopRh = 15.0f;        // drying stops at or below this relative humidity
  float startRh = 17.0f;       // ...and starts again above this (2 % hysteresis)
  float maxC = 65.0f;          // the heater never pushes the chamber past this
  float taperC = 5.0f;         // full power until maxC - taperC, then tapering to zero at maxC
  float overC = 70.0f;         // above this the heater locks out ...
  float overResetC = 60.0f;    // ... until the chamber cools below this
  uint32_t sensorTimeoutMs = 10000;   // no good reading this long: heater off
  uint32_t fanRunOnMs = 120000;       // fan keeps running this long after the heater was last on
};

struct Reading {
  bool ok = false;
  float c = 0;
  float rh = 0;
};

struct Output {
  float heaterDuty = 0;   // 0..1, applied as slow PWM
  bool fan = false;
  bool drying = false;    // humidity above target: the box is working
  bool sensorFault = false;
  bool overTemp = false;
};

class Controller {
 public:
  explicit Controller(const Settings& s = Settings()) : s_(s) {}
  // Call every couple of seconds. `fresh` = this call carries a new good reading.
  Output update(uint32_t nowMs, const Reading& r);

 private:
  Settings s_;
  bool drying_ = false;
  bool overTemp_ = false;
  bool haveReading_ = false;
  uint32_t lastGoodMs_ = 0;
  float c_ = 0, rh_ = 0;
  bool heaterEverOn_ = false;
  uint32_t heaterLastOnMs_ = 0;
};

// Duty -> on/off over a fixed window (2 s). The PC817 gate drive switches the MOSFET slowly,
// and a heater needs nothing faster.
class SlowPwm {
 public:
  explicit SlowPwm(uint32_t windowMs = 2000, uint32_t minPulseMs = 100) : window_(windowMs), minPulse_(minPulseMs) {}
  bool on(float duty, uint32_t nowMs);

 private:
  uint32_t window_, minPulse_, start_ = 0;
  bool started_ = false;
};

}  // namespace basic
