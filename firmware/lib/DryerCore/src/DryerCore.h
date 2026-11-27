// Dryer control logic: modes, material presets, the heater PID, the safety cut-outs and the
// weight maths. Plain C++ with no Arduino calls, so it builds and is unit-tested on the host
// (pio test -e native) as well as on the ESP32-C3.
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace dryer {

enum class Mode : uint8_t { Off = 0, Dry, KeepDry, Print };
enum class Fault : uint8_t {
  None = 0,
  ChamberOverTemp,   // chamber above setpoint + 8 °C, or above 75 °C at any time
  OutletOverTemp,    // heater outlet above 100 °C (blower stalled?)
  ChamberSensor,     // chamber sensor missing while heating
  OutletSensor,      // outlet probe missing while heating
  NoTempRise,        // 10 min near full power and the chamber barely warmed
  RunTooLong,        // a dry cycle past 24 h, or print mode past 72 h
};

const char* modeName(Mode m);
const char* faultName(Fault f);
bool parseMode(const char* s, Mode* out);

struct Material {
  const char* name;
  float dryC;          // dry temperature
  uint32_t dryMin;     // dry time, minutes
  float feedC;         // print-mode temperature
  float density;       // g/cm³, for metres left
};
extern const Material MATERIALS[];
extern const size_t MATERIAL_COUNT;
int materialIndex(const char* name);   // -1 if unknown (case-insensitive)

// Limits and timings, all in one place.
struct Limits {
  static constexpr float kChamberAbsMaxC = 75.0f;
  static constexpr float kChamberOverSetC = 8.0f;
  static constexpr float kOutletMaxC = 100.0f;
  static constexpr float kOutletSoftC = 85.0f;      // duty tapers to 0 between here and kOutletSoftC + 10
  static constexpr uint32_t kSensorGraceMs = 5000;  // a sensor may miss reads this long before it is a fault
  static constexpr uint32_t kNoRiseWindowMs = 10UL * 60 * 1000;
  static constexpr float kNoRiseMinC = 2.0f;
  static constexpr float kNoRiseDuty = 0.9f;
  static constexpr uint32_t kDryMaxMs = 24UL * 3600 * 1000;
  static constexpr uint32_t kPrintMaxMs = 72UL * 3600 * 1000;
  static constexpr uint32_t kBlowerRunOnMs = 2UL * 60 * 1000;
  static constexpr float kDryEndRh = 15.0f;              // dry ends early below this RH ...
  static constexpr uint32_t kDryEndRhMs = 30UL * 60 * 1000;   // ... held this long, after half the preset time
  static constexpr float kKeepDryRh = 25.0f;             // keep dry: above this RH ...
  static constexpr uint32_t kKeepDryRhMs = 15UL * 60 * 1000;  // ... this long starts a boost dry
  static constexpr float kBoostC = 45.0f;
  static constexpr uint32_t kBoostMs = 60UL * 60 * 1000;
  static constexpr uint32_t kVentOnMs = 10UL * 1000;     // exhaust pulse length
  static constexpr uint32_t kVentEarlyPeriodMs = 60UL * 1000;   // first hour: every minute
  static constexpr uint32_t kVentLatePeriodMs = 5UL * 60 * 1000;  // then every 5 min
};

// Simple PID on the chamber temperature; output is a heater duty 0..1.
class Pid {
 public:
  Pid(float kp = 0.08f, float ki = 0.0008f, float kd = 0.0f) : kp_(kp), ki_(ki), kd_(kd) {}
  void reset() { integral_ = 0; havePrev_ = false; }
  float update(float setpoint, float measured, float dtS);
 private:
  float kp_, ki_, kd_;
  float integral_ = 0;
  float prev_ = 0;
  bool havePrev_ = false;
};

struct Inputs {
  uint32_t nowMs = 0;
  bool chamberOk = false;
  float chamberC = 0;
  float chamberRh = 0;
  bool outletOk = false;
  float outletC = 0;
};

struct Outputs {
  float heaterDuty = 0;   // apply with time-proportioning (see HeaterWindow)
  bool blower = false;
  bool exhaust = false;
};

class Controller {
 public:
  Controller();
  void setMaterial(int index);              // ignored if out of range
  void setMaxC(float c) { maxC_ = c; }      // cap every setpoint (1-roll v2: load cells in the chamber, 65 °C)
  float maxC() const { return maxC_; }
  int material() const { return material_; }
  void setMode(Mode m, uint32_t nowMs);     // ignored while a fault is latched (except Off)
  void clearFault(uint32_t nowMs);          // back to Off
  Outputs update(const Inputs& in);

  Mode mode() const { return mode_; }
  Fault fault() const { return fault_; }
  bool boosting() const { return boostActive_; }
  float setpoint() const;                   // 0 when not heating
  uint32_t modeElapsedMs(uint32_t nowMs) const { return nowMs - modeStartMs_; }
  uint32_t dryRemainingS(uint32_t nowMs) const;   // dry mode: seconds to the preset end, else 0
  float lastDuty() const { return lastDuty_; }

 private:
  void enter(Mode m, uint32_t nowMs);
  void trip(Fault f, uint32_t nowMs);
  bool heating() const { return setpoint() > 0; }

  int material_ = 0;
  float maxC_ = 1000.0f;
  Mode mode_ = Mode::Off;
  Fault fault_ = Fault::None;
  uint32_t modeStartMs_ = 0;
  uint32_t lastUpdateMs_ = 0;
  bool haveLastUpdate_ = false;
  // safety bookkeeping
  uint32_t chamberBadSinceMs_ = 0, outletBadSinceMs_ = 0;
  bool chamberBad_ = false, outletBad_ = false;
  bool fullPower_ = false;
  uint32_t fullPowerSinceMs_ = 0;
  float fullPowerStartC_ = 0;
  // humidity timers
  bool dryLowRh_ = false;
  uint32_t dryLowRhSinceMs_ = 0;
  bool keepHighRh_ = false;
  uint32_t keepHighRhSinceMs_ = 0;
  bool boostActive_ = false;
  uint32_t boostStartMs_ = 0;
  // blower run-on
  uint32_t heaterLastOnMs_ = 0;
  bool heaterEverOn_ = false;
  Pid pid_;
  float lastDuty_ = 0;
};

// Turns a duty into on/off over a fixed window (slow PWM). Slow on purpose: the perfboard's
// PC817 gate drive switches the MOSFET slowly, and a heater does not need anything faster.
class HeaterWindow {
 public:
  explicit HeaterWindow(uint32_t windowMs = 2000, uint32_t minPulseMs = 100) : windowMs_(windowMs), minPulseMs_(minPulseMs) {}
  bool on(float duty, uint32_t nowMs);
 private:
  uint32_t windowMs_, minPulseMs_;
  uint32_t windowStartMs_ = 0;
  bool started_ = false;
};

// Median of the last N samples (the scale reports a 10 s median of 10 Hz reads).
template <size_t N>
class Median {
 public:
  void add(float v) { buf_[pos_] = v; pos_ = (pos_ + 1) % N; if (count_ < N) count_++; }
  size_t count() const { return count_; }
  void clear() { count_ = 0; pos_ = 0; }
  float value() const {
    if (count_ == 0) return 0;
    float tmp[N];
    for (size_t i = 0; i < count_; i++) tmp[i] = buf_[i];
    for (size_t i = 1; i < count_; i++) {          // insertion sort, N is small
      float x = tmp[i]; size_t j = i;
      while (j > 0 && tmp[j - 1] > x) { tmp[j] = tmp[j - 1]; j--; }
      tmp[j] = x;
    }
    return (count_ % 2) ? tmp[count_ / 2] : 0.5f * (tmp[count_ / 2 - 1] + tmp[count_ / 2]);
  }
 private:
  float buf_[N] = {};
  size_t pos_ = 0, count_ = 0;
};

// Scale maths. raw = HX711 counts; scale = counts per gram; offset = counts at tare.
struct ScaleCal {
  float offset = 0;
  float scale = 1;     // set by calibrate()
  float emptyReelG = 0;
  float gramsFromRaw(float raw) const { return (raw - offset) / scale; }
  void tare(float raw) { offset = raw; }
  bool calibrate(float raw, float knownGrams);   // false if the reading did not change
};
// metres of 1.75 mm filament in the given grams: 1 m is 2.405 cm³
float metresLeft(float grams, float density);

// ---- 1-roll v2: the axle rests on two load cells, one at each end, each with its own HX711.
// Total = left + right, wherever the reel sits on the axle, once each cell has its own scale
// factor. Those come from a two-point calibration (the weight near the left end, then near the
// right end) or, less exactly, one point with the weight in the middle.
// The cells sit in the heated chamber, so each cell's zero drifts with temperature. driftPerC
// (counts per °C, learned once by DriftFit) corrects it from the chamber temperature.
struct TwinScaleCal {
  float offset[2] = {0, 0};          // counts at tare
  float gramsPerCount[2] = {0, 0};   // 0 = not calibrated
  float driftPerC[2] = {0, 0};       // zero drift, counts per °C
  float refC = 25;                   // chamber temperature at tare
  float emptyReelG = 0;

  bool calibrated() const { return gramsPerCount[0] != 0 && gramsPerCount[1] != 0; }
  // counts above the tare, with the zero drift since the tare taken out
  float net(int i, float raw, float tempC) const { return raw - offset[i] - driftPerC[i] * (tempC - refC); }
  float cellGrams(int i, float raw, float tempC) const { return net(i, raw, tempC) * gramsPerCount[i]; }
  float grams(float rawL, float rawR, float tempC) const { return cellGrams(0, rawL, tempC) + cellGrams(1, rawR, tempC); }
  void tare(float rawL, float rawR, float tempC) { offset[0] = rawL; offset[1] = rawR; refC = tempC; }
};

// Two-point calibration. netL1/netR1: net counts with the weight near the left end; netL2/netR2:
// near the right end. Solves kL*netL + kR*netR = grams for both points. False when the two points
// are too alike (the weight wasn't moved) or the result is nonsense (a cell not responding).
bool solveTwoPoint(float netL1, float netR1, float netL2, float netR2, float grams, float* kL, float* kR);
// One point with the weight in the middle of the axle: each cell carries half.
bool solveCentre(float netL, float netR, float grams, float* kL, float* kR);

// Least-squares fit of each cell's raw counts against chamber temperature, under a constant load,
// over one heat cycle. Needs at least kMinSamples samples spread over kMinSpanC.
class DriftFit {
 public:
  static constexpr size_t kMinSamples = 20;
  static constexpr float kMinSpanC = 15.0f;
  void reset() { *this = DriftFit(); }
  void add(float tempC, float rawL, float rawR);
  size_t count() const { return n_; }
  float spanC() const { return n_ ? maxC_ - minC_ : 0; }
  bool solve(float* perCL, float* perCR) const;   // counts per °C for each cell
 private:
  size_t n_ = 0;
  double st_ = 0, stt_ = 0, sl_ = 0, stl_ = 0, sr_ = 0, str_ = 0;
  float minC_ = 0, maxC_ = 0;
};

}  // namespace dryer
