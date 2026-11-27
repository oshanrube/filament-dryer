# 1-roll v2: twin scale

The single-reel dryer with the axle on two load cells, a 150 W PTC heater, a blower, an SHT40 chamber probe, a DS18B20 heater-outlet probe, a 2.42" OLED and a button, hand-built on perfboard. No filament sensor in the box (the BTT SFS goes on the printer).

- `page.html`: the page (built into `docs/1-roll-v2/` by `tools/build_site.py`): the scale, temperature drift, pins, build steps
- `wiring.svg`: the schematic; `images/perfboard.svg`, `images/front-panel.svg`: drawn by `tools/gen_v2.py` (`python3 1-roll-v2/tools/gen_v2.py` from the repo root)
- `bom.csv`: AliExpress parts, through-hole where there's a choice
- Firmware: `firmware/`, build `dryer-1roll-v2` (`pio run -e dryer-1roll-v2`), released as `dryer-1roll-v2.bin` / `dryer-1roll-v2-full.bin`
