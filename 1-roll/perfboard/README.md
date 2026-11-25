# 1-roll controller on perfboard (parts from Tronic.lk)

A hand-built version of the 1-roll controller from modules and through-hole parts in stock at [Tronic.lk](https://tronic.lk), for a first box while the PCB is routed and ordered. **Same pin map as the 1-roll PCB**, so the same firmware image runs on both (`firmware/`, build `dryer-1roll`; it detects which chamber sensor is fitted).

- `schematic.svg`: every wire, module level
- `layout.svg`: where everything sits on a 120 × 80 mm FR4 dot board, plus the wire list
- `gen_perfboard.py`: draws both (`python3 1-roll/perfboard/gen_perfboard.py`)

## Parts at Tronic.lk (prices and stock checked 2026-11-25)

To re-check prices and stock before buying: `python3 tools/tronic_search.py "HX711" "IRF3205" "AHT20" ...` (prints name, price, stock and link for each match).

| Part | Qty per box | Tronic item | Rs. each | In stock |
| --- | --- | --- | --- | --- |
| ESP32-C3 SuperMini | 1 | [SuperMini ESP32-C3](https://tronic.lk/product/supermini-esp32-c3-dev-board-type-c-wifi-bluetooth-iot) (you have spares) | 850 | 31 |
| 12 → 5 V buck (set to 5.0 V first) | 1 | [MP1584 adjustable buck module](https://tronic.lk/product/mp1584-4-5-28v-to-0-8v-18v-3a-dc-to-dc-adjustable-step-) | 230 | 379 |
| Load-cell amplifier | 1 | [HX711 module](https://tronic.lk/product/hx711-dual-channel-24-bit-ad-conversion-weighing-sensor) | 160 | 42 |
| Load cell | 1 | [Load cell 10 kg](https://tronic.lk/product/load-cell-10kg) (the 5 kg one is out of stock; 10 kg still reads to about 2-3 g) | 430 | 8 |
| Heater MOSFET (Q1) | 1 | [IRF3205](https://tronic.lk/product/original-irf3205-hexfet-power-mosfet-55v-110a) | 160 | 71 |
| Heatsink for Q1 | 1 | [TO-220 heatsink 19×15×10](https://tronic.lk/product/aluminum-heat-sink-19x15x10mm-to220-black) | 70 | 52 |
| Gate-drive optocoupler | 1 | [PC817](https://tronic.lk/product/pc817-optocoupler) | 10 | 1115 |
| Fan and buzzer switches (Q2-Q4) | 3 | [2N2222A TO-92](https://tronic.lk/product/original-2n2222a-npn-transistor-to-92) | 5 | 659 |
| Fan flyback diodes | 2 | [1N5819](https://tronic.lk/product/original-1n5819-40v-1a-diode) | 10 | 300 |
| Chamber temperature + humidity | 1 | [AHT20 in AM2301 housing, I2C](https://tronic.lk/product/am2301-aht20-digital-temperature-humidity-sensor-i2c-hi) (no SHT40/SHT30 in stock) | 1,450 | 8 |
| Heater outlet temperature | 1 | [DS18B20 waterproof probe, 1 m](https://tronic.lk/product/ds18b20-waterproof-digital-temperature-sensor-probe-wit) | 320 | 90 |
| Buzzer | 1 | [5 V mini buzzer (active)](https://tronic.lk/product/5v-mini-buzzer), not the "(Passive)" one | 50 | 155 |
| Display | 1 | [1.3" 128×64 OLED, I2C](https://tronic.lk/product/1-3-inch-128x64-oled-display-module-white-i2c-iic) | 960 | 79 |
| Front button | 1 | [DS-212 16 mm metal push button](https://tronic.lk/product/ds-212-black-16mm-round-metal-push-button-momentary-swi) | 60 | 152 |
| Board | 1 | [Dot board, FR4 epoxy, 12×8 cm](https://tronic.lk/product/vero-board-dot-epoxy-fr4-12x8cm) (FR4 copes with the warm bay better than paper board) | 170 | 128 |
| Screw terminals, 2-way 5.08 mm | 7 | [2-pin 5.08 mm](https://tronic.lk/product/5-08mm-pitch-2-pin-2-way-screw-terminal-block-pcb-mount) (T1-T4, T7, and two side by side for T6) | 20 | 783 |
| Screw terminal, 3-way 5.08 mm | 1 | [3-pin 5.08 mm](https://tronic.lk/product/5-08mm-pitch-3-pin-3-way-screw-terminal-block-pcb-mount) (T5) | 30 | 369 |
| Female headers | 2 strips | [40-pin single row 2.54 mm](https://tronic.lk/product/40-pin-single-row-female-headers-2-54mm) (SuperMini, HX711, I2C headers) | 30 | 870 |
| Fuse | 1 (+ spares) | [15 A ATO blade fuse](https://tronic.lk/product/atcato-blade-fuse-auto-car-fuse-15a) | 30 | 70 |
| Fuse holder | 1 | [ATO blade fuse holder](https://tronic.lk/product/atcato-blade-fuse-holder) (check it's the inline, wire-lead type) | 80 | 120 |
| Bulk capacitor C1 | 1 | [100 µF 25 V](https://tronic.lk/product/100uf-25v-electrolytic-capacitor-tht) | 5 | 1050 |
| Decoupling C2 | 1 | [100 nF 50 V ceramic](https://tronic.lk/product/100nf-50v-ceramic-capacitor-tht) | 2 | 2664 |
| Resistors 1 kΩ | 9 | [1 k ¼ W, pack of ~40](https://tronic.lk/product/1k-14w-resistor-pack-carbon-film-tht-5-approx-40pcs) (R1 and R4, R5 are two in parallel) | 50 / pack | 40 |
| Resistors 10 kΩ | 3 | [10 k ¼ W, pack of ~40](https://tronic.lk/product/10k-14w-resistor-pack-carbon-film-tht-5-approx-40pcs) | 50 / pack | 87 |
| Resistors 4.7 kΩ | 3 | [4.7 k ¼ W, pack of ~40](https://tronic.lk/product/4-7k-14w-resistor-pack-carbon-film-tht-5-approx-40pcs) | 50 / pack | 56 |
| Exhaust fan | 1 | [4010 axial fan 12 V](https://tronic.lk/product/cooling-fan-4010-axial-40x40x10mm-12v) | 200 | 25 |
| Blower | 1 | [4010 blower 12 V](https://tronic.lk/product/cooling-fan-4010-blower-40x40x10mm-12v) (no 5015 at Tronic; this one moves less air) | 440 | 8 |
| Reel bearings | 4 | [608ZZ](https://tronic.lk/product/608zz-deep-groove-ball-bearing-8x22x7mm) | 40 | 150 |

About **Rs. 3,600 per box** for the controller (board, modules, sensors, passives), plus about Rs. 1,700 for the OLED, button and fans.

**Not at Tronic** (from AliExpress or a local RC/auto shop): the XT60 pair, the KSD301 85 °C thermostat, the 92 °C thermal fuse, the 12 V 150 W PTC heater (Tronic's 12 V PTC plates don't list a wattage), the BTT Smart Filament Sensor V2, and silicone wire (14 AWG for the heater path, 22 AWG for the rest). JST XH connectors aren't stocked either, which is why this version uses screw terminals.

## Differences from the PCB

| | PCB | Perfboard |
| --- | --- | --- |
| Heater switch | UCC27517 + AOD4184A | PC817 + IRF3205 on a heatsink (gate driven from 12 V, slow switching: use slow PWM, about 1 s period) |
| Fan and buzzer switches | AO3400A | 2N2222A with 500 Ω / 1 kΩ base resistors |
| 5 V | AP63205 on the board | MP1584 module, set to 5.0 V before connecting |
| 3.3 V | AMS1117 | The SuperMini's own regulator |
| Chamber sensor | SHT40 (0x44) on sensor board SB1 | AHT20 probe (0x38): the firmware finds it on its own |
| Bay sensor | SHT40-BD1B | Left out |
| Connectors | JST XH | 5.08 mm screw terminals, female headers for I2C |

Pins are the same: GPIO0/1 HX711, GPIO2 DS18B20, GPIO3 runout, GPIO4 heater, GPIO5/6 fans, GPIO7/8 I2C, GPIO10 buzzer, GPIO20 button, GPIO21 motion (through 1 kΩ).

## Build notes

1. **Keep the 12.5 A heater current off the perfboard.** 14 AWG from the fuse to T1 and T2, and from the heater's minus straight to Q1's drain leg; Q1's source leg straight to T1 GND. Solder these to the parts' legs, not along the board.
2. **Set the MP1584 to 5.0 V** with a meter before connecting the SuperMini.
3. **Check before closing the box:** with the heater disconnected, toggle GPIO4 and measure Q1's gate: about 11 V on, 0 V off. At power-up it must read 0 V.
4. The KSD301 thermostat and the thermal fuse stay in series with the heater in the harness, as in the main design.
