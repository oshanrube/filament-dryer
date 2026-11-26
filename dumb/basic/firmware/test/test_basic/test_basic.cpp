// pio test -e native
#include <unity.h>

#include "BasicControl.h"

using namespace basic;

static Reading rd(float c, float rh) { Reading r; r.ok = true; r.c = c; r.rh = rh; return r; }
void setUp() {}
void tearDown() {}

void test_humid_and_cool_runs_full() {
  Controller k;
  Output o = k.update(0, rd(30, 60));
  TEST_ASSERT_TRUE(o.drying);
  TEST_ASSERT_TRUE(o.fan);
  TEST_ASSERT_EQUAL_FLOAT(1.0f, o.heaterDuty);
}

void test_tapers_between_60_and_65() {
  Controller k;
  TEST_ASSERT_EQUAL_FLOAT(1.0f, k.update(0, rd(60, 40)).heaterDuty);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, k.update(1, rd(62.5f, 40)).heaterDuty);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, k.update(2, rd(65, 40)).heaterDuty);
  Output o = k.update(3, rd(66, 40));
  TEST_ASSERT_EQUAL_FLOAT(0.0f, o.heaterDuty);
  TEST_ASSERT_TRUE(o.fan);                 // still drying: air keeps moving
}

void test_stops_at_15_percent_with_hysteresis() {
  Controller k;
  k.update(0, rd(50, 30));
  Output o = k.update(1000, rd(50, 15.0f));
  TEST_ASSERT_FALSE(o.drying);
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
  TEST_ASSERT_TRUE(o.fan);                 // run-on after the heater
  o = k.update(2000, rd(50, 16.5f));       // between 15 and 17: stays off
  TEST_ASSERT_FALSE(o.drying);
  o = k.update(3000, rd(50, 17.5f));       // above 17: starts again
  TEST_ASSERT_TRUE(o.drying);
}

void test_fan_stops_two_minutes_after_heat() {
  Controller k;
  k.update(0, rd(40, 30));
  k.update(1000, rd(40, 14));
  TEST_ASSERT_TRUE(k.update(100000, rd(40, 14)).fan);
  TEST_ASSERT_FALSE(k.update(122000, rd(40, 14)).fan);
}

void test_dry_box_never_heats() {
  Controller k;
  Output o = k.update(0, rd(25, 12));
  TEST_ASSERT_FALSE(o.drying);
  TEST_ASSERT_FALSE(o.fan);
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
}

void test_lost_sensor_stops_heat() {
  Controller k;
  k.update(0, rd(40, 50));
  Reading bad;                              // ok = false
  Output o = k.update(5000, bad);
  TEST_ASSERT_TRUE(o.heaterDuty > 0);       // within the 10 s grace: last good reading stands
  o = k.update(11000, bad);
  TEST_ASSERT_TRUE(o.sensorFault);
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
  Controller fresh;                         // never had a reading: never heats
  TEST_ASSERT_EQUAL_FLOAT(0, fresh.update(0, bad).heaterDuty);
}

void test_over_temperature_lockout() {
  Controller k;
  Output o = k.update(0, rd(71, 50));
  TEST_ASSERT_TRUE(o.overTemp);
  TEST_ASSERT_EQUAL_FLOAT(0, o.heaterDuty);
  TEST_ASSERT_TRUE(o.fan);
  o = k.update(1000, rd(62, 50));           // cooler, but not below 60 yet
  TEST_ASSERT_TRUE(o.overTemp);
  o = k.update(2000, rd(59, 50));
  TEST_ASSERT_FALSE(o.overTemp);
  TEST_ASSERT_EQUAL_FLOAT(1.0f, o.heaterDuty);
}

void test_slow_pwm() {
  SlowPwm p;
  int on = 0;
  for (uint32_t t = 0; t < 2000; t += 10) on += p.on(0.5f, t);
  TEST_ASSERT_INT_WITHIN(2, 100, on);
  SlowPwm q;
  TEST_ASSERT_FALSE(q.on(0.03f, 0));       // under the 100 ms minimum pulse
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_humid_and_cool_runs_full);
  RUN_TEST(test_tapers_between_60_and_65);
  RUN_TEST(test_stops_at_15_percent_with_hysteresis);
  RUN_TEST(test_fan_stops_two_minutes_after_heat);
  RUN_TEST(test_dry_box_never_heats);
  RUN_TEST(test_lost_sensor_stops_heat);
  RUN_TEST(test_over_temperature_lockout);
  RUN_TEST(test_slow_pwm);
  return UNITY_END();
}
