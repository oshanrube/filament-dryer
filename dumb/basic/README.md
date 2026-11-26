# Basic dryer controller (Wemos D1 Mini or ESP-01S)

A small controller for the dumb box in place of the STC-3028 + W1209: one temperature + humidity probe, a fan and the heater.

- **Fan and heater run while the box is above 15 % RH.** They stop at 15 % and start again above 17 %. After the heater was last on, the fan keeps going for 2 minutes to carry the heat off the heatsink.
- **The heater never pushes the box past 65 °C.** It runs at full power up to 60 °C, then less and less (slow PWM, 2 s period) until it's off at 65 °C. That gives less overshoot than any on/off thermostat.
- **Safety:**
  - At 70 °C the heater locks out until the box is back under 60 °C.
  - With no good reading for 10 s, the heater stays off.
  - At power-up the heater stays off until there's a reading.
  - The KSD301 and thermal fuse cut the heater in hardware if all of that fails.
- **Wi-Fi reporting on the D1 Mini** for the Printer Control Center (below). No display, no buttons. The on-board LED shows the state:

  | LED | State |
  |---|---|
  | On | Heating |
  | Slow blink | Fan only |
  | Short flash every 3 s | Dry, idle |
  | Fast blink | Probe fault or too hot |

  The USB serial port (115200 baud) logs the temperature, humidity, heater % and fan every 10 s.

Files:
- `wiring.svg` (D1 Mini) and `wiring-esp01.svg` (ESP-01S): the circuits, drawn by `tools/gen_basic.py` (`python3 dumb/basic/tools/gen_basic.py` from the repo root).
- `firmware/`: PlatformIO project.
  - `src/main.cpp`: pins, probe drivers, LED and log.
  - `lib/BasicControl/`: the decisions, tested on a PC with `pio test -e native`.

## Wi-Fi and the Printer Control Center (D1 Mini)

The D1 Mini reports over Wi-Fi with **the same API as the smart dryer** (`firmware/README.md`), so one control-center integration reads both. `"model":"basic"` tells them apart. **The control stays on the board:** the heater and fan decisions don't depend on Wi-Fi, the Pi or the API, and a lost network changes nothing.

**First boot:**
1. With no saved network, it opens a hotspot `FilamentDryer-XXXX`.
2. Join it from your phone. The setup page opens; pick RubeHomeAP (or RubeHomeIOT) and enter the password.
3. It joins the network as `filament-dryer-xxxx` (the last 4 hex digits of its MAC).

If the saved network can't be reached at power-up, the hotspot opens for 3 min, then it goes back to trying the saved network.

**What it serves:**
- **`http://filament-dryer-xxxx.local/`**: a small status page with temperature, humidity, state, and Auto/Off buttons.
- **`GET /api/state`**:

  ```json
  {"version":"0.1.0","name":"filament-dryer-ab12","model":"basic","mode":"auto","drying":true,
   "setpoint_c":65,"stop_rh":15,"start_rh":17,"fault":"none",
   "chamber":{"ok":true,"c":58.4,"rh":19.2,"sensor":"am2301"},
   "heater":{"duty":1.00,"on":true},"blower":true,"uptime_s":3600,"wifi_rssi":-61}
  ```

  `fault` is `none`, `chamber_sensor` (no good reading for 10 s) or `chamber_over_temp` (70 °C lockout).
- **`POST /api/mode`** with `{"mode":"auto"}` or `{"mode":"off"}`. Off stops the heater and fan; it's kept across power cuts.
- **WebSocket on port 81**: the state on connect and every second, and it takes `{"cmd":"mode","mode":"off"}`.
- **mDNS:** `_filament-dryer._tcp` on 81 (TXT `model=basic`), the same service as the smart dryer, for discovery.
- **Firmware update over Wi-Fi:** `http://filament-dryer-xxxx.local/update`; upload `basic-dryer-d1mini.bin`.
- **`POST /api/wifi/reset`** forgets the network and reopens the hotspot.

No login, like the smart dryer: keep it on the home network.

**Control-center support for dryers isn't built yet**, for either model. The API is ready for it.

## Probe: not a DHT11

The probe has to read below 15 % RH and above 65 °C. A **DHT11 can't**: it only measures 20–90 % RH and 0–50 °C, so in a drying box it would sit at "20 %" for ever and run the heater non-stop. Any of these work, and the firmware detects which one is fitted:

| Probe | Range | Wiring | Tronic |
|---|---|---|---|
| AM2301 (DHT21) on a lead, the same type as the M452's probe | −40…80 °C, 0–100 % RH | 3 wires: VCC, DATA → D7, GND; R5 4.7 kΩ DATA → 3V3 | [Rs 1,360](https://tronic.lk/product/am2301-dht21-digital-temperature-humidity-sensor) (28 in stock) |
| DHT22 / AM2302 module | −40…80 °C, 0–100 % RH | same as the AM2301 | [Rs 450](https://tronic.lk/product/dht22-am2302-digital-temperature-and-humidity-sensor-mo) (1 in stock) |
| AHT20 in an AM2301-style housing, I2C | −40…85 °C, 0–100 % RH | 4 wires: VCC → 3V3, GND, SDA → D2, SCL → D1; R6/R7 4.7 kΩ to 3V3 | [Rs 1,450](https://tronic.lk/product/am2301-aht20-digital-temperature-humidity-sensor-i2c-hi) (8 in stock) |

The M452's own probe works too if you'd rather not buy one: it's an AM2301. Note that 65 °C is near the top of these probes' range, so mount the probe in the chamber air, not in the heater outlet.

## Parts (Tronic.lk unless marked)

Prices checked 2026-11-26; re-check with `python3 tools/tronic_search.py "D1 mini" "AM2301" ...`.

| Part | Qty | Where | Rs |
|---|---|---|---|
| Wemos D1 Mini (ESP8266, CH340, micro-USB) | 1 | [NodeMCU D1 Mini](https://tronic.lk/product/nodemcu-d1-mini-lua-wemos-esp8266-dev-board-microusb-ch) (46 in stock) | 830 |
| Temperature + humidity probe | 1 | AM2301 / DHT22 / AHT20, see above | 450–1,450 |
| 12 → 5 V buck (set to 5.0 V **before** connecting the D1 Mini) | 1 | [MP1584](https://tronic.lk/product/mp1584-4-5-28v-to-0-8v-18v-3a-dc-to-dc-adjustable-step-) | 230 |
| Heater MOSFET Q1 | 1 | [IRF3205](https://tronic.lk/product/original-irf3205-hexfet-power-mosfet-55v-110a) | 160 |
| Heatsink for Q1 | 1 | [TO-220 heatsink](https://tronic.lk/product/aluminum-heat-sink-19x15x10mm-to220-black) | 70 |
| Gate-drive optocoupler | 1 | [PC817](https://tronic.lk/product/pc817-optocoupler) | 10 |
| Fan transistor Q2 | 1 | [2N2222A](https://tronic.lk/product/original-2n2222a-npn-transistor-to-92) | 5 |
| Fan flyback diode D1 | 1 | [1N5819](https://tronic.lk/product/original-1n5819-40v-1a-diode) | 10 |
| Resistors: 1 kΩ ×5 (R2, and R1/R4 as two in parallel each), 10 kΩ ×1, 4.7 kΩ ×1–2 | | [1 k](https://tronic.lk/product/1k-14w-resistor-pack-carbon-film-tht-5-approx-40pcs), [10 k](https://tronic.lk/product/10k-14w-resistor-pack-carbon-film-tht-5-approx-40pcs), [4.7 k](https://tronic.lk/product/4-7k-14w-resistor-pack-carbon-film-tht-5-approx-40pcs) packs | 150 |
| Blower | 1 | [4010 blower 12 V](https://tronic.lk/product/cooling-fan-4010-blower-40x40x10mm-12v) | 440 |
| Board | 1 | [Dot board FR4 12×8 cm](https://tronic.lk/product/vero-board-dot-epoxy-fr4-12x8cm) (cut in half: the circuit fits on 6×8 cm) | 170 |
| Screw terminals | 3× 2-pin, 1× 3-pin | [2-pin 5.08 mm](https://tronic.lk/product/5-08mm-pitch-2-pin-2-way-screw-terminal-block-pcb-mount), [3-pin](https://tronic.lk/product/5-08mm-pitch-3-pin-3-way-screw-terminal-block-pcb-mount) (12 V in, heater, fan, probe) | 90 |
| Female header strip for the D1 Mini | 1 | [40-pin 2.54 mm](https://tronic.lk/product/40-pin-single-row-female-headers-2-54mm) | 30 |
| Fuse + holder | 1 | [15 A ATO fuse](https://tronic.lk/product/atcato-blade-fuse-auto-car-fuse-15a) + [inline holder](https://tronic.lk/product/atcato-blade-fuse-holder) | 110 |
| **Controller total** | | | **about 2,800–3,800** |

Heater and safety parts (shared with the dumb box's list, `../bom.csv`):
- **Heater:** 2× RX24 50 W 3 Ω aluminium resistors (AliExpress), on the [200×56×30 mm heatsink](https://tronic.lk/product/aluminum-heat-sink-200x56x30mm-for-amplifier-ics) (Rs 1,000) cut in half.
- **KSD301 85 °C, normally closed:** AliExpress. ITEC has a [95 °C one at Rs 520](https://itecelectronic.lk/product/ksd301-thermostat-95c-16a-normally-closed-n-c-temperature-switch/) if you need it today; it trips later but still well before ABS/ASA softens.
- **92 °C thermal fuse:** AliExpress.

## ESP-01S instead of the D1 Mini

The same firmware runs on an ESP-01S (build `basic-esp01`, image `basic-dryer-esp01.bin`), wired as in `wiring-esp01.svg`. It has just enough pins:

| ESP-01S pin | Job | Why there |
|---|---|---|
| GPIO0 | Heater, **active low**: 3V3 → R1 470 Ω → PC817 LED → GPIO0, with R8 10 kΩ to 3V3 | GPIO0 must be high at boot, and high = heater off, so a booting or crashed board can't heat |
| GPIO2 | AM2301 / DHT22 data, R5 4.7 kΩ to 3V3 | Must be high at boot; the probe's pull-up does that |
| GPIO3 (RX) | Fan, through R4 500 Ω to the 2N2222A; R9 10 kΩ base → GND | RX isn't needed: the log only transmits |
| GPIO1 (TX) | Serial log, 115200 baud | |

Compared with the D1 Mini:

- **Cost:** Rs 490 instead of Rs 830 per board. You also need a [USB ESP-01 adapter](https://tronic.lk/product/usb-to-esp8266-esp-01-interface-module) (Rs 350, 36 in stock) once, to flash it.
- **Power:** set the MP1584 to **3.3 V**, not 5 V, and check it with a meter **before** plugging the ESP-01S in: above 3.6 V it's destroyed. Fit 100 µF + 100 nF across its 3V3 and GND at the socket.
- **Probe:** AM2301 or DHT22 only. The AHT20 needs two I2C pins that aren't left.
- **Status:** no status LED (the on-board LED shares GPIO2 with the probe and flickers on each reading). The state is only in the serial log, through the adapter.
- **Board:** mount the ESP-01S in a 2×4 female header, so you can pull it out to flash it.
- **ESP-01 (not "S"):** it doesn't pull EN up on the board. Add 10 kΩ from EN to 3V3.

**Flashing an ESP-01S:**
1. Plug it into the USB adapter with the adapter's GPIO0 jumper (or switch) set to ground, then plug the adapter in.
2. Flash `basic-dryer-esp01.bin` at `0x0`, as below.
3. Set the jumper back and replug the adapter to run it.

## Flashing

The release images are one file each, flashed at address 0: `basic-dryer-d1mini.bin` or `basic-dryer-esp01.bin`. Plug the D1 Mini (or the ESP-01 adapter) into USB; Windows needs the CH340 driver.

- **From a browser** (Chrome/Edge): open https://espressif.github.io/esptool-js/, click Connect and pick the CH340 port. Set the flash address to `0x0`, choose `basic-dryer-d1mini.bin`, then click Program.
- **Or with esptool:**

  ```bash
  esptool.py --chip esp8266 --baud 460800 write_flash 0x0 basic-dryer-d1mini.bin
  esptool.py --chip esp8266 --baud 115200 write_flash 0x0 basic-dryer-esp01.bin
  ```

- **Or build it:**

  ```bash
  cd dumb/basic/firmware && pio run -e basic-d1mini -t upload   # or -e basic-esp01
  ```

Then open the serial monitor at 115200 baud: it prints `probe: AM2301/DHT21` (or `AHT20`), and a line every 10 s.

## Build and test

1. **Before fitting the D1 Mini:** power the board from 12 V and set the MP1584 to 5.0 V.
2. **Heater disconnected:** fit the D1 Mini and the probe, and check the serial log reads sensible values.
   - Breathe on the probe: the humidity rises, and the fan and D5 come on. Q1's gate should read about 11 V, at least for part of every 2 s.
   - Unplug the probe: within 10 s the LED blinks fast and the gate reads 0 V.
3. **First heat, lid open, attended:** connect the heater. Watch the log as it nears 60 °C: the heater % should fall to 0 by 65 °C.
4. **Check the KSD301** opens with a hot-air gun (it clicks at its rating) before closing the box.

## Changing the numbers

They're in `firmware/lib/BasicControl/src/BasicControl.h` (`struct Settings`):

| Setting | Default | Meaning |
|---|---|---|
| `stopRh` / `startRh` | 15 / 17 % | humidity band |
| `maxC` | 65 °C | the heater's cap |
| `taperC` | 5 °C | taper band below the cap |
| `overC` / `overResetC` | 70 / 60 °C | lockout and reset |

Rebuild after changing them, and run `pio test -e native`. For PLA, set `maxC` to 50.
