#include "BasicControl.h"

namespace basic {

static float clamp01(float v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }

Output Controller::update(uint32_t now, const Reading& r) {
  if (r.ok) {
    haveReading_ = true;
    lastGoodMs_ = now;
    c_ = r.c;
    rh_ = r.rh;
  }
  Output out;
  bool sensorOk = haveReading_ && (now - lastGoodMs_) < s_.sensorTimeoutMs;
  out.sensorFault = !sensorOk;

  if (sensorOk) {
    // humidity decides whether the box works at all
    if (!drying_ && rh_ > s_.startRh) drying_ = true;
    else if (drying_ && rh_ <= s_.stopRh) drying_ = false;
    // over-temperature lockout (the KSD301 and thermal fuse sit behind this in hardware)
    if (c_ >= s_.overC) overTemp_ = true;
    else if (overTemp_ && c_ < s_.overResetC) overTemp_ = false;
  } else {
    drying_ = false;   // no reading: never heat blind
  }

  float duty = 0;
  if (sensorOk && drying_ && !overTemp_) duty = clamp01((s_.maxC - c_) / s_.taperC);
  out.heaterDuty = duty;
  if (duty > 0) { heaterEverOn_ = true; heaterLastOnMs_ = now; }
  bool runOn = heaterEverOn_ && (now - heaterLastOnMs_) < s_.fanRunOnMs;
  out.fan = (sensorOk && drying_) || runOn || overTemp_;
  out.drying = drying_;
  out.overTemp = overTemp_;
  return out;
}

bool SlowPwm::on(float duty, uint32_t now) {
  if (!started_ || now - start_ >= window_) { start_ = now; started_ = true; }
  uint32_t onMs = (uint32_t)(clamp01(duty) * window_);
  if (onMs < minPulse_) onMs = 0;
  if (window_ - onMs < minPulse_) onMs = window_;
  return (now - start_) < onMs;
}

}  // namespace basic
