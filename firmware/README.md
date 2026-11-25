# Filament dryer firmware

PlatformIO + Arduino firmware for the ESP32-C3, set up like the gate controller. One build, `dryer-1roll`, runs both 1-roll controllers: the 1-roll PCB (`pcb/1-roll/`) and the perfboard build (`1-roll/perfboard/`). They share a pin map. The 2-roll feeder board (MCP23017, feeder drivers) is not covered yet.

**Status:** builds, and the control logic passes its 16 host tests. It has **not run on real hardware yet**: check the bench steps below before trusting it with a heater.

## Files

| Path | What |
| --- | --- |
| `src/main.cpp` | Hardware, the two tasks, Wi-Fi, web API, OTA |
| `src/page.h` | The dryer's own web page and the update form |
| `lib/DryerCore/` | The control logic: modes, material presets, PID, safety cut-outs, scale maths. Plain C++, no Arduino |
| `test/test_core/` | Host tests for that logic (`pio test -e native`) |
| `platformio.ini` | Same platform pin as the gate controller (espressif32 6.9.0, Arduino core 2.0.17) |
| `../.github/workflows/firmware.yml` | Builds on a `fw-v*` tag and attaches the images to a GitHub release |

## The two images

| File | Flash it | When |
| --- | --- | --- |
| `dryer-1roll-full.bin` | at **0x0** over USB | A blank board: bootloader, partition table, boot_app0 and the app in one image |
| `dryer-1roll.bin` | through the dryer's web page, `http://filament-dryer-xxxx.local/update` | Updates over Wi-Fi |

Flashing the full image over USB-C, either way:

- **In a browser (Chrome or Edge):** <https://espressif.github.io/esptool-js/>, Connect, add `dryer-1roll-full.bin` at address `0x0`, Program.
- **From a terminal:**

  ```bash
  esptool.py --chip esp32c3 write_flash 0x0 dryer-1roll-full.bin
  ```

On the 1-roll PCB the USB port carries data only: **plug in the 12 V feed while flashing.** If the board doesn't show up, hold BOOT, tap RESET, release BOOT. The SuperMini has its own BOOT button.

## Building

```bash
cd firmware
pio test -e native        # control-logic tests on this computer
pio run -e dryer-1roll    # build
pio run -e dryer-1roll -t upload
```

Releases: push a tag like `fw-v0.1.0` and the workflow stamps that version into the build, runs the tests, builds, and attaches both images to the release. Manual runs (Actions → firmware → Run workflow) keep them as a one-day artifact instead.

## First setup

1. **Wi-Fi:** with no saved network the dryer opens a hotspot `FilamentDryer-XXXX`. Join it, pick your Wi-Fi in the page that opens, save. The OLED shows the hotspot name, then the dryer's IP. The heater control keeps running while the hotspot is open.
2. **Scale:** with the cradle empty, *Tare*. Put a known weight on it (the 500 g calibration weight), type its grams and *Calibrate*. Then weigh an empty reel of the brand you use and set *empty reel weight*. All three are saved.
3. **Runout switch polarity:** the page shows *Filament: present / not detected*. If it reads backwards, `POST /api/config {"runout_invert": true}`.
4. **Motion sensor scale:** `mm_per_pulse` defaults to 2.88 mm. Check it by pulling 100 mm of filament through and comparing `motion_mm`.

## Front button

| Press | Does |
| --- | --- |
| Short | Next mode: Off → Dry → Keep dry → Print → Off. While a fault is showing: acknowledges it (back to Off) |
| 3 s | Tare the scale |
| 10 s | Forget Wi-Fi and restart into the setup hotspot |

The OLED says what a long press will do before you let go.

## What it does

- **Modes:** *Dry* at the material's preset (PLA 50 °C 5 h, PETG 65 °C 6 h, ABS/ASA 70 °C 4 h, TPU 55 °C 6 h, Nylon 70 °C 10 h, PC 70 °C 8 h). It ends when the time is up, or early when the air stays under 15 % RH for 30 min past half the time. Then *Keep dry*: heater off, and a 1 h boost at 45 °C if the air sits above 25 % RH for 15 min. *Print*: the material's feed temperature (PLA 40 °C, others 45-50 °C) until told otherwise. *Off*.
- **Heater:** PID on the chamber temperature, applied as slow PWM over a 2 s window (min. 100 ms pulses). The perfboard's PC817 gate drive needs that, and the PCB doesn't mind. Duty tapers off as the heater outlet passes 85 °C.
- **Fans:** the blower runs whenever the heater may run, and for 2 min after it was last on or after a fault. The exhaust fan vents 10 s every minute for the first hour of drying, then every 5 min.
- **Safety cut-outs** latch the heater off, beep, and show on the OLED and in the API until acknowledged:

  | Fault | Trips when |
  | --- | --- |
  | `chamber_over_temp` | chamber > setpoint + 8 °C, or > 75 °C in any mode |
  | `outlet_over_temp` | heater outlet > 100 °C in any mode |
  | `chamber_sensor`, `outlet_sensor` | a sensor stops answering for 5 s while heating (it never heats without a chamber reading) |
  | `no_temp_rise` | 10 min at ≥ 90 % duty and the chamber rose < 2 °C |
  | `run_too_long` | a dry cycle past 24 h, print mode past 72 h |

  These sit on top of the hardware ones: the KSD301 85 °C thermostat, the 92 °C thermal fuse, gate pull-downs that keep the heater off at boot, and a task watchdog that restarts the chip if the control loop ever stalls. After a power cut the dryer comes back in *Keep dry* if it was in it, otherwise *Off*.
- **Sensors:** the chamber sensor is found automatically: SHT40 at 0x44 (PCB) or AHT20 at 0x38 (perfboard), re-checked every 10 s if missing. The bay SHT40 at 0x45 (PCB only) is optional. DS18B20 at the heater outlet. HX711 at 10 Hz with a 10 s median. BTT SFS V2 runout switch and motion pulses.

## API (for the Printer Control Center)

No login: the dryer is meant to sit on the local network (like the rest of the control center), so keep it off anything public.

- `GET /api/state`: everything, as JSON:

  ```json
  {"version":"0.1.0","name":"filament-dryer-ab12","mode":"dry","boost":false,"material":"PETG",
   "setpoint_c":65,"dry_remaining_s":18000,"fault":"none",
   "chamber":{"ok":true,"c":64.8,"rh":12,"sensor":"sht40"},"outlet":{"ok":true,"c":81.5},
   "bay":{"ok":false},"heater":{"duty":0.42,"on":true},"blower":true,"exhaust":false,
   "scale":{"ok":true,"grams":1062,"empty_reel_g":250,"grams_left":812,"metres_left":265},
   "filament":{"present":true,"motion_mm":1234.5,"motion_pulses":428,"mm_per_pulse":2.88}}
  ```

- **Commands** (POST, JSON body; each replies with the new state):
  - `/api/mode` `{"mode":"dry|keep_dry|print|off","material":"PETG"}` (either field alone works)
  - `/api/fault/clear`
  - `/api/tare`
  - `/api/calibrate` `{"grams":500}`
  - `/api/config` `{"empty_reel_g":250,"mm_per_pulse":2.88,"runout_invert":false}`
  - `/api/motion/reset`
- **WebSocket** on port **81**: sends the state on connect and every second, and takes the same commands as `{"cmd":"mode","mode":"print"}`, `{"cmd":"tare"}`, and so on. This is the "one live connection per dryer".
- **mDNS:** `filament-dryer-xxxx.local`, with `_http._tcp` on 80 and `_filament-dryer._tcp` on 81 for discovery.
- **OTA:** `POST /update` with the app image, or the form at `/update`.

## Bench checks before the first real heat

1. Heater **disconnected**. Power up and confirm the heater output (GPIO4, or Q1's gate) is low.
2. Check both sensors read sensibly, then unplug each. With *Dry* selected it should fault within 5 s.
3. Select *Dry* and watch the heater output pulse (2 s window) while the blower runs.
4. Warm the chamber sensor with your hand or a hair dryer past setpoint + 8 °C. It must trip `chamber_over_temp` and stay tripped until acknowledged.
5. Only then connect the heater, with the KSD301 and thermal fuse in series, and watch a full warm-up.
