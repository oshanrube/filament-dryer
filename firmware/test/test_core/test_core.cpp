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
  return UNITY_END();
}
