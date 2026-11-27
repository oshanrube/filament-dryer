#include "DryerCore.h"

#include <ctype.h>
#include <string.h>

namespace dryer {

// name, dry °C, dry minutes, print-mode °C, density g/cm³
const Material MATERIALS[] = {
    {"PLA", 50.0f, 5 * 60, 40.0f, 1.24f},
    {"PETG", 65.0f, 6 * 60, 45.0f, 1.27f},
    {"ABS", 70.0f, 4 * 60, 50.0f, 1.04f},
    {"ASA", 70.0f, 4 * 60, 50.0f, 1.07f},
    {"TPU", 55.0f, 6 * 60, 45.0f, 1.21f},
    {"NYLON", 70.0f, 10 * 60, 50.0f, 1.14f},
    {"PC", 70.0f, 8 * 60, 50.0f, 1.20f},
};
const size_t MATERIAL_COUNT = sizeof(MATERIALS) / sizeof(MATERIALS[0]);

static bool ieq(const char* a, const char* b) {
  if (!a || !b) return false;
  while (*a && *b) {
    if (toupper((unsigned char)*a) != toupper((unsigned char)*b)) return false;
    a++; b++;
  }
  return *a == *b;
}

int materialIndex(const char* name) {
  for (size_t i = 0; i < MATERIAL_COUNT; i++)
    if (ieq(name, MATERIALS[i].name)) return (int)i;
  return -1;
}

const char* modeName(Mode m) {
  switch (m) {
    case Mode::Off: return "off";
    case Mode::Dry: return "dry";
    case Mode::KeepDry: return "keep_dry";
    case Mode::Print: return "print";
  }
  return "?";
}

bool parseMode(const char* s, Mode* out) {
  static const Mode all[] = {Mode::Off, Mode::Dry, Mode::KeepDry, Mode::Print};
  for (Mode m : all)
    if (ieq(s, modeName(m))) { *out = m; return true; }
  return false;
}

const char* faultName(Fault f) {
  switch (f) {
    case Fault::None: return "none";
    case Fault::ChamberOverTemp: return "chamber_over_temp";
    case Fault::OutletOverTemp: return "outlet_over_temp";
    case Fault::ChamberSensor: return "chamber_sensor";
    case Fault::OutletSensor: return "outlet_sensor";
    case Fault::NoTempRise: return "no_temp_rise";
    case Fault::RunTooLong: return "run_too_long";
  }
  return "?";
}

static float clamp01(float v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }

float Pid::update(float setpoint, float measured, float dtS) {
  float err = setpoint - measured;
  float deriv = havePrev_ && dtS > 0 ? -(measured - prev_) / dtS : 0;
  prev_ = measured;
  havePrev_ = true;
  float p = kp_ * err;
  float trial = integral_ + ki_ * err * dtS;
  float out = p + trial + kd_ * deriv;
  // anti-windup: only keep integrating while the output is not pinned, or when it pulls back
  if ((out < 1.0f || err < 0) && (out > 0.0f || err > 0)) integral_ = trial;
  if (integral_ > 1.0f) integral_ = 1.0f;
  if (integral_ < -0.5f) integral_ = -0.5f;
  return clamp01(p + integral_ + kd_ * deriv);
}

Controller::Controller() {}

void Controller::setMaterial(int index) {
  if (index >= 0 && (size_t)index < MATERIAL_COUNT) material_ = index;
}

float Controller::setpoint() const {
  if (fault_ != Fault::None) return 0;
  const Material& m = MATERIALS[material_];
  float sp = 0;
  switch (mode_) {
    case Mode::Dry: sp = m.dryC; break;
    case Mode::Print: sp = m.feedC; break;
    case Mode::KeepDry: sp = boostActive_ ? Limits::kBoostC : 0; break;
    case Mode::Off: sp = 0; break;
  }
  return sp > maxC_ ? maxC_ : sp;
}

uint32_t Controller::dryRemainingS(uint32_t nowMs) const {
  if (mode_ != Mode::Dry || fault_ != Fault::None) return 0;
  uint32_t total = MATERIALS[material_].dryMin * 60UL * 1000UL;
  uint32_t el = nowMs - modeStartMs_;
  return el >= total ? 0 : (total - el) / 1000;
}

void Controller::enter(Mode m, uint32_t nowMs) {
  mode_ = m;
  modeStartMs_ = nowMs;
  boostActive_ = false;
  dryLowRh_ = false;
  keepHighRh_ = false;
  fullPower_ = false;
  pid_.reset();
}

void Controller::setMode(Mode m, uint32_t nowMs) {
  if (fault_ != Fault::None && m != Mode::Off) return;
  enter(m, nowMs);
}

void Controller::clearFault(uint32_t nowMs) {
  fault_ = Fault::None;
  chamberBad_ = outletBad_ = false;
  enter(Mode::Off, nowMs);
}

void Controller::trip(Fault f, uint32_t nowMs) {
  if (fault_ == Fault::None) fault_ = f;
  boostActive_ = false;
  fullPower_ = false;
  pid_.reset();
  heaterLastOnMs_ = nowMs;   // the blower runs on for 2 min after a cut-out, to cool the heater
  heaterEverOn_ = true;
}

Outputs Controller::update(const Inputs& in) {
  const uint32_t now = in.nowMs;
  float dtS = haveLastUpdate_ ? (now - lastUpdateMs_) / 1000.0f : 0;
  lastUpdateMs_ = now;
  haveLastUpdate_ = true;

  // ---- sensor health (a missing sensor only matters while heating)
  if (!in.chamberOk) {
    if (!chamberBad_) { chamberBad_ = true; chamberBadSinceMs_ = now; }
  } else chamberBad_ = false;
  if (!in.outletOk) {
    if (!outletBad_) { outletBad_ = true; outletBadSinceMs_ = now; }
  } else outletBad_ = false;

  // ---- cut-outs that apply in every mode: these mean heat where there should be none
  if (in.chamberOk && in.chamberC > Limits::kChamberAbsMaxC) trip(Fault::ChamberOverTemp, now);
  if (in.outletOk && in.outletC > Limits::kOutletMaxC) trip(Fault::OutletOverTemp, now);

  // ---- mode timing (only while no fault)
  if (fault_ == Fault::None) {
    uint32_t el = now - modeStartMs_;
    const Material& mat = MATERIALS[material_];
    if (mode_ == Mode::Dry) {
      if (el >= Limits::kDryMaxMs) trip(Fault::RunTooLong, now);
      else if (el >= mat.dryMin * 60UL * 1000UL) enter(Mode::KeepDry, now);
      else if (in.chamberOk && el >= mat.dryMin * 30UL * 1000UL) {   // past half the preset
        if (in.chamberRh < Limits::kDryEndRh) {
          if (!dryLowRh_) { dryLowRh_ = true; dryLowRhSinceMs_ = now; }
          else if (now - dryLowRhSinceMs_ >= Limits::kDryEndRhMs) enter(Mode::KeepDry, now);
        } else dryLowRh_ = false;
      }
    } else if (mode_ == Mode::KeepDry) {
      if (boostActive_) {
        if (now - boostStartMs_ >= Limits::kBoostMs) { boostActive_ = false; keepHighRh_ = false; pid_.reset(); }
      } else if (in.chamberOk && in.chamberRh > Limits::kKeepDryRh) {
        if (!keepHighRh_) { keepHighRh_ = true; keepHighRhSinceMs_ = now; }
        else if (now - keepHighRhSinceMs_ >= Limits::kKeepDryRhMs) { boostActive_ = true; boostStartMs_ = now; pid_.reset(); }
      } else keepHighRh_ = false;
    } else if (mode_ == Mode::Print) {
      if (el >= Limits::kPrintMaxMs) trip(Fault::RunTooLong, now);
    }
  }

  // ---- heating-only cut-outs
  float sp = setpoint();
  if (sp > 0) {
    if (chamberBad_ && now - chamberBadSinceMs_ >= Limits::kSensorGraceMs) trip(Fault::ChamberSensor, now);
    if (outletBad_ && now - outletBadSinceMs_ >= Limits::kSensorGraceMs) trip(Fault::OutletSensor, now);
    if (in.chamberOk && in.chamberC > sp + Limits::kChamberOverSetC) trip(Fault::ChamberOverTemp, now);
    sp = setpoint();
  }

  // ---- heater duty
  float duty = 0;
  if (sp > 0 && in.chamberOk) {
    duty = pid_.update(sp, in.chamberC, dtS);
    if (in.outletOk && in.outletC > Limits::kOutletSoftC)   // taper before the hard outlet cut-out
      duty *= clamp01(1.0f - (in.outletC - Limits::kOutletSoftC) / 10.0f);
    // no temperature rise near full power: heater open circuit, thermostat open, fuse blown
    if (duty >= Limits::kNoRiseDuty) {
      if (!fullPower_) { fullPower_ = true; fullPowerSinceMs_ = now; fullPowerStartC_ = in.chamberC; }
      else if (now - fullPowerSinceMs_ >= Limits::kNoRiseWindowMs) {
        if (in.chamberC - fullPowerStartC_ < Limits::kNoRiseMinC) { trip(Fault::NoTempRise, now); duty = 0; }
        else { fullPowerSinceMs_ = now; fullPowerStartC_ = in.chamberC; }
      }
    } else fullPower_ = false;
  }
  if (fault_ != Fault::None) duty = 0;

  Outputs out;
  out.heaterDuty = duty;
  if (duty > 0) { heaterLastOnMs_ = now; heaterEverOn_ = true; }
  // blower: whenever we are in a heating mode, and for 2 min after the heater was last on
  bool runOn = heaterEverOn_ && (now - heaterLastOnMs_ < Limits::kBlowerRunOnMs);
  out.blower = (setpoint() > 0) || runOn;
  // exhaust: vent pulses while drying (dry mode and keep-dry boosts)
  bool venting = fault_ == Fault::None && (mode_ == Mode::Dry || (mode_ == Mode::KeepDry && boostActive_));
  if (venting) {
    uint32_t el = now - (mode_ == Mode::Dry ? modeStartMs_ : boostStartMs_);
    uint32_t period = el < 3600UL * 1000 ? Limits::kVentEarlyPeriodMs : Limits::kVentLatePeriodMs;
    out.exhaust = (el % period) < Limits::kVentOnMs;
  }
  lastDuty_ = duty;
  return out;
}

bool HeaterWindow::on(float duty, uint32_t nowMs) {
  if (!started_ || nowMs - windowStartMs_ >= windowMs_) { windowStartMs_ = nowMs; started_ = true; }
  uint32_t onMs = (uint32_t)(clamp01(duty) * windowMs_);
  if (onMs < minPulseMs_) onMs = 0;
  if (windowMs_ - onMs < minPulseMs_) onMs = windowMs_;
  return (nowMs - windowStartMs_) < onMs;
}

bool ScaleCal::calibrate(float raw, float knownGrams) {
  float delta = raw - offset;
  if (knownGrams <= 0 || delta == 0) return false;
  scale = delta / knownGrams;
  return true;
}

float metresLeft(float grams, float density) {
  if (grams <= 0 || density <= 0) return 0;
  return grams / (density * 2.405f);
}

static float fabsf_(float v) { return v < 0 ? -v : v; }

bool solveTwoPoint(float l1, float r1, float l2, float r2, float grams, float* kL, float* kR) {
  if (grams <= 0) return false;
  // [l1 r1; l2 r2] [kL kR]' = [g g]'
  double det = (double)l1 * r2 - (double)l2 * r1;
  double scale = (fabsf_(l1) + fabsf_(r1)) * (fabsf_(l2) + fabsf_(r2));
  if (scale <= 0 || fabsf_((float)det) < 0.05 * scale) return false;   // the weight wasn't moved enough
  double a = grams * ((double)r2 - r1) / det;
  double b = grams * ((double)l1 - l2) / det;
  if (a == 0 || b == 0) return false;
  // each cell must carry a sensible share at both points (catches a dead or unplugged cell)
  float shares[4] = {(float)(a * l1), (float)(b * r1), (float)(a * l2), (float)(b * r2)};
  for (float s : shares)
    if (s < -0.1f * grams || s > 1.1f * grams) return false;
  *kL = (float)a;
  *kR = (float)b;
  return true;
}

bool solveCentre(float netL, float netR, float grams, float* kL, float* kR) {
  if (grams <= 0 || netL == 0 || netR == 0) return false;
  // with the weight in the middle both cells should move a similar amount (within 3x)
  float ratio = fabsf_(netL) / fabsf_(netR);
  if (ratio > 3.0f || ratio < 1.0f / 3.0f) return false;
  *kL = grams / 2 / netL;
  *kR = grams / 2 / netR;
  return true;
}

void DriftFit::add(float t, float l, float r) {
  if (n_ == 0) { minC_ = maxC_ = t; }
  if (t < minC_) minC_ = t;
  if (t > maxC_) maxC_ = t;
  n_++;
  st_ += t; stt_ += (double)t * t;
  sl_ += l; stl_ += (double)t * l;
  sr_ += r; str_ += (double)t * r;
}

bool DriftFit::solve(float* perCL, float* perCR) const {
  if (n_ < kMinSamples || spanC() < kMinSpanC) return false;
  double n = (double)n_;
  double d = n * stt_ - st_ * st_;
  if (d <= 0) return false;
  *perCL = (float)((n * stl_ - st_ * sl_) / d);
  *perCR = (float)((n * str_ - st_ * sr_) / d);
  return true;
}

}  // namespace dryer
