// Host tests for the control logic:  pio test -e native
#include <unity.h>

#include "DryerCore.h"

using namespace dryer;

static Inputs ok(uint32_t t, float c, float rh = 40, float outlet = 60) {
  Inputs in;
  in.nowMs = t; in.chamberOk = true; in.chamberC = c; in.chamberRh = rh; in.outletOk = true; in.outletC = outlet;
  return in;
}

void setUp() {}
void tearDown() {}

void test_materials_and_modes() {
  TEST_ASSERT_EQUAL_INT(0, materialIndex("pla"));
  TEST_ASSERT_EQUAL_INT(1, materialIndex("PETG"));
  TEST_ASSERT_EQUAL_INT(-1, materialIndex("wood"));
  Mode m;
  TEST_ASSERT_TRUE(parseMode("keep_dry", &m));
  TEST_ASSERT_EQUAL(Mode::KeepDry, m);
  TEST_ASSERT_FALSE(parseMode("boil", &m));
}

void test_off_means_no_heat() {
  Controller c;
  Outputs o = c.update(ok(0, 25));
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
  TEST_ASSERT_FALSE(o.blower);
  TEST_ASSERT_FALSE(o.exhaust);
}

void test_dry_heats_and_runs_blower() {
  Controller c;
  c.setMaterial(materialIndex("PETG"));
  c.setMode(Mode::Dry, 0);
  Outputs o = c.update(ok(1000, 25));
  TEST_ASSERT_EQUAL_FLOAT(65, c.setpoint());
  TEST_ASSERT_TRUE(o.heaterDuty > 0.9f);
  TEST_ASSERT_TRUE(o.blower);
  TEST_ASSERT_TRUE(o.exhaust);               // first 10 s of the first minute
  o = c.update(ok(20000, 26));
  TEST_ASSERT_FALSE(o.exhaust);              // 20 s in: between pulses
}

void test_no_heat_without_chamber_reading_and_fault_after_grace() {
  Controller c;
  c.setMode(Mode::Dry, 0);
  Inputs in = ok(1000, 25);
  in.chamberOk = false;
  Outputs o = c.update(in);
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
  TEST_ASSERT_EQUAL(Fault::None, c.fault());
  in.nowMs = 7000;
  c.update(in);
  TEST_ASSERT_EQUAL(Fault::ChamberSensor, c.fault());
}

void test_outlet_probe_missing_trips() {
  Controller c;
  c.setMode(Mode::Dry, 0);
  Inputs in = ok(1000, 30);
  in.outletOk = false;
  c.update(in);
  in.nowMs = 7000;
  c.update(in);
  TEST_ASSERT_EQUAL(Fault::OutletSensor, c.fault());
}

void test_over_temperature_cutouts() {
  Controller c;
  c.setMaterial(materialIndex("PLA"));       // 50 °C
  c.setMode(Mode::Dry, 0);
  c.update(ok(1000, 57));
  TEST_ASSERT_EQUAL(Fault::None, c.fault());
  Outputs o = c.update(ok(2000, 58.5f));     // above 50 + 8
  TEST_ASSERT_EQUAL(Fault::ChamberOverTemp, c.fault());
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
  TEST_ASSERT_TRUE(o.blower);                // runs on to cool down

  Controller d;                              // heat with the heater off: a stuck MOSFET
  d.update(ok(0, 76));
  TEST_ASSERT_EQUAL(Fault::ChamberOverTemp, d.fault());

  Controller e;
  e.setMode(Mode::Dry, 0);
  e.update(ok(1000, 40, 40, 101));
  TEST_ASSERT_EQUAL(Fault::OutletOverTemp, e.fault());
}

void test_fault_latches_until_cleared() {
  Controller c;
  c.setMode(Mode::Dry, 0);
  c.update(ok(1000, 80));
  TEST_ASSERT_EQUAL(Fault::ChamberOverTemp, c.fault());
  c.setMode(Mode::Dry, 2000);                // refused while latched
  TEST_ASSERT_EQUAL_FLOAT(0, c.setpoint());
  c.clearFault(3000);
  TEST_ASSERT_EQUAL(Fault::None, c.fault());
  TEST_ASSERT_EQUAL(Mode::Off, c.mode());
}

void test_outlet_soft_limit_tapers_duty() {
  Controller c;
  c.setMode(Mode::Dry, 0);
  Outputs cool = c.update(ok(1000, 25, 40, 60));
  Controller d;
  d.setMode(Mode::Dry, 0);
  Outputs hot = d.update(ok(1000, 25, 40, 92));
  TEST_ASSERT_TRUE(hot.heaterDuty < cool.heaterDuty * 0.5f);
}

void test_no_temperature_rise_trips() {
  Controller c;
  c.setMaterial(materialIndex("PETG"));
  c.setMode(Mode::Dry, 0);
  uint32_t t = 0;
  for (int i = 0; i <= 11 * 60; i++) { c.update(ok(t, 25.5f)); t += 1000; }   // 11 min flat at full power
  TEST_ASSERT_EQUAL(Fault::NoTempRise, c.fault());

  Controller d;                                                                // warming normally: no fault
  d.setMaterial(materialIndex("PETG"));
  d.setMode(Mode::Dry, 0);
  t = 0;
  for (int i = 0; i <= 11 * 60; i++) { d.update(ok(t, 25 + i * 0.01f)); t += 1000; }
  TEST_ASSERT_EQUAL(Fault::None, d.fault());
}

void test_dry_ends_at_preset_time() {
  Controller c;
  c.setMaterial(materialIndex("ABS"));      // 4 h
  c.setMode(Mode::Dry, 0);
  c.update(ok(1000, 70));
  TEST_ASSERT_EQUAL(Mode::Dry, c.mode());
  TEST_ASSERT_EQUAL_UINT32(4 * 3600 - 1, c.dryRemainingS(1000));
  c.update(ok(4UL * 3600 * 1000 + 1, 70));
  TEST_ASSERT_EQUAL(Mode::KeepDry, c.mode());
}

void test_dry_ends_early_when_dry_air_after_half_time() {
  Controller c;
  c.setMaterial(materialIndex("PLA"));      // 5 h, half = 2.5 h
  c.setMode(Mode::Dry, 0);
  uint32_t t = 2UL * 3600 * 1000;           // 2 h: too early even if dry
  c.update(ok(t, 50, 10));
  c.update(ok(t + 31UL * 60 * 1000, 50, 10));
  TEST_ASSERT_EQUAL(Mode::Dry, c.mode());
  t = 3UL * 3600 * 1000;                    // past half time, dry for 30 min
  c.update(ok(t, 50, 10));
  c.update(ok(t + 31UL * 60 * 1000, 50, 10));
  TEST_ASSERT_EQUAL(Mode::KeepDry, c.mode());
}

void test_keep_dry_boost() {
  Controller c;
  c.setMode(Mode::KeepDry, 0);
  Outputs o = c.update(ok(1000, 30, 30));
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
  TEST_ASSERT_FALSE(o.blower);
  c.update(ok(16UL * 60 * 1000 + 2000, 30, 30));    // humid for over 15 min
  TEST_ASSERT_TRUE(c.boosting());
  TEST_ASSERT_EQUAL_FLOAT(45, c.setpoint());
  c.update(ok(16UL * 60 * 1000 + 2000 + 61UL * 60 * 1000, 45, 20));   // an hour later
  TEST_ASSERT_FALSE(c.boosting());
  TEST_ASSERT_EQUAL_FLOAT(0, c.setpoint());
}

void test_blower_runs_on_for_two_minutes() {
  Controller c;
  c.setMode(Mode::Print, 0);
  Outputs o = c.update(ok(1000, 30));
  TEST_ASSERT_TRUE(o.heaterDuty > 0);
  c.setMode(Mode::Off, 2000);
  o = c.update(ok(60000, 40));
  TEST_ASSERT_TRUE(o.blower);
  o = c.update(ok(1000 + 121000, 40));
  TEST_ASSERT_FALSE(o.blower);
}

void test_print_mode_runs_cool_and_no_vent() {
  Controller c;
  c.setMaterial(materialIndex("PLA"));
  c.setMode(Mode::Print, 0);
  Outputs o = c.update(ok(1000, 30));
  TEST_ASSERT_EQUAL_FLOAT(40, c.setpoint());
  TEST_ASSERT_FALSE(o.exhaust);
}

void test_heater_window() {
  HeaterWindow w(2000, 100);
  int on = 0;
  for (uint32_t t = 0; t < 2000; t += 10) on += w.on(0.25f, t);
  TEST_ASSERT_INT_WITHIN(2, 50, on);                // 25 % of 200 steps
  HeaterWindow z(2000, 100);
  TEST_ASSERT_FALSE(z.on(0.02f, 0));                 // below the minimum pulse: off
  HeaterWindow f(2000, 100);
  TEST_ASSERT_TRUE(f.on(0.98f, 1990));               // near full: stays on
}

void test_median_and_scale() {
  Median<5> m;
  m.add(10); m.add(1000); m.add(12); m.add(11); m.add(13);
  TEST_ASSERT_EQUAL_FLOAT(12, m.value());            // one spike ignored
  ScaleCal s;
  s.tare(8000);
  TEST_ASSERT_TRUE(s.calibrate(8000 + 500 * 420.0f, 500));
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 250, s.gramsFromRaw(8000 + 250 * 420.0f));
  TEST_ASSERT_FALSE(s.calibrate(8000, 500));
  TEST_ASSERT_FLOAT_WITHIN(0.5f, 335.4f, metresLeft(1000, 1.24f));   // 1 kg PLA is about 335 m
}

// ---- 1-roll v2: two load cells
void test_max_c_caps_setpoints() {
  Controller c;
  c.setMaxC(65);
  c.setMaterial(materialIndex("ABS"));      // dry preset 70 °C
  c.setMode(Mode::Dry, 0);
  TEST_ASSERT_EQUAL_FLOAT(65, c.setpoint());
  c.setMaterial(materialIndex("PLA"));      // 50 °C: under the cap, unchanged
  TEST_ASSERT_EQUAL_FLOAT(50, c.setpoint());
}

void test_two_point_calibration_is_position_independent() {
  // true cells: left 400 counts/g... expressed as grams per count
  const float kLtrue = 1.0f / 400, kRtrue = 1.0f / 520;
  const float w = 500;
  // weight at 20 % of the axle from the left: left carries 80 %, right 20 %
  float l1 = 0.8f * w / kLtrue, r1 = 0.2f * w / kRtrue;
  float l2 = 0.25f * w / kLtrue, r2 = 0.75f * w / kRtrue;
  float kL, kR;
  TEST_ASSERT_TRUE(solveTwoPoint(l1, r1, l2, r2, w, &kL, &kR));
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, kLtrue, kL);
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, kRtrue, kR);
  // a 1000 g reel anywhere on the axle reads 1000 g
  for (float share = 0.1f; share < 0.95f; share += 0.2f) {
    TwinScaleCal cal;
    cal.gramsPerCount[0] = kL; cal.gramsPerCount[1] = kR;
    float g = cal.grams(share * 1000 / kLtrue, (1 - share) * 1000 / kRtrue, 25);
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 1000, g);
  }
}

void test_two_point_rejects_bad_input() {
  float kL, kR;
  TEST_ASSERT_FALSE(solveTwoPoint(1000, 1000, 1000, 1000, 500, &kL, &kR));   // weight not moved
  TEST_ASSERT_FALSE(solveTwoPoint(1000, 0, 900, 0, 500, &kL, &kR));          // right cell dead
  TEST_ASSERT_FALSE(solveTwoPoint(1000, 200, 300, 900, 0, &kL, &kR));        // no weight
}

void test_negative_counts_still_work() {
  // a cell wired the other way round gives negative counts: the factor comes out negative too
  const float kLtrue = -1.0f / 400, kRtrue = 1.0f / 400;
  float kL, kR;
  TEST_ASSERT_TRUE(solveTwoPoint(0.7f * 500 / kLtrue, 0.3f * 500 / kRtrue, 0.3f * 500 / kLtrue, 0.7f * 500 / kRtrue, 500, &kL, &kR));
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, kLtrue, kL);
}

void test_centre_calibration() {
  float kL, kR;
  TEST_ASSERT_TRUE(solveCentre(100000, 130000, 500, &kL, &kR));
  TEST_ASSERT_FLOAT_WITHIN(1e-7f, 250.0f / 100000, kL);
  TEST_ASSERT_FLOAT_WITHIN(1e-7f, 250.0f / 130000, kR);
  TEST_ASSERT_FALSE(solveCentre(100000, 10000, 500, &kL, &kR));   // weight nowhere near the middle
}

void test_drift_fit_and_compensation() {
  // each cell's zero rises 30 and falls 45 counts per °C; the reel itself never changes
  DriftFit fit;
  for (int i = 0; i < 40; i++) {
    float t = 25 + i;                       // 25 -> 64 °C over a heat-up
    fit.add(t, 100000 + 30 * (t - 25), 80000 - 45 * (t - 25));
  }
  float dL, dR;
  TEST_ASSERT_TRUE(fit.solve(&dL, &dR));
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 30, dL);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, -45, dR);

  TwinScaleCal cal;
  cal.gramsPerCount[0] = cal.gramsPerCount[1] = 1.0f / 400;
  cal.tare(20000, 20000, 25);
  // 80000 counts on each cell above tare = 400 g total, at 25 °C
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 400, cal.grams(100000, 100000, 25));
  // at 65 °C without compensation the drift reads as weight: 40 °C x (30 - 45) counts = -600 counts = -1.5 g
  float hotL = 100000 + 30 * 40, hotR = 100000 - 45 * 40;
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 398.5f, cal.grams(hotL, hotR, 65));
  cal.driftPerC[0] = dL; cal.driftPerC[1] = dR;
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 400, cal.grams(hotL, hotR, 65));
}

void test_drift_fit_needs_a_real_heat_cycle() {
  DriftFit fit;
  for (int i = 0; i < 40; i++) fit.add(25 + i * 0.2f, 1000, 1000);   // only 8 °C of range
  float a, b;
  TEST_ASSERT_FALSE(fit.solve(&a, &b));
  DriftFit few;
  for (int i = 0; i < 5; i++) few.add(25 + i * 10, 1000, 1000);       // too few samples
  TEST_ASSERT_FALSE(few.solve(&a, &b));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_materials_and_modes);
  RUN_TEST(test_off_means_no_heat);
  RUN_TEST(test_dry_heats_and_runs_blower);
  RUN_TEST(test_no_heat_without_chamber_reading_and_fault_after_grace);
  RUN_TEST(test_outlet_probe_missing_trips);
  RUN_TEST(test_over_temperature_cutouts);
  RUN_TEST(test_fault_latches_until_cleared);
  RUN_TEST(test_outlet_soft_limit_tapers_duty);
  RUN_TEST(test_no_temperature_rise_trips);
  RUN_TEST(test_dry_ends_at_preset_time);
  RUN_TEST(test_dry_ends_early_when_dry_air_after_half_time);
  RUN_TEST(test_keep_dry_boost);
  RUN_TEST(test_blower_runs_on_for_two_minutes);
  RUN_TEST(test_print_mode_runs_cool_and_no_vent);
  RUN_TEST(test_heater_window);
  RUN_TEST(test_median_and_scale);
  RUN_TEST(test_max_c_caps_setpoints);
  RUN_TEST(test_two_point_calibration_is_position_independent);
  RUN_TEST(test_two_point_rejects_bad_input);
  RUN_TEST(test_negative_counts_still_work);
  RUN_TEST(test_centre_calibration);
  RUN_TEST(test_drift_fit_and_compensation);
  RUN_TEST(test_drift_fit_needs_a_real_heat_cycle);
  return UNITY_END();
}
