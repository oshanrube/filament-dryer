# 2-roll feeder

Two reels, each on its own load cell, with a feeder pod that loads the second reel automatically when the printer reports a runout. ESP32-C3 SuperMini + MCP23017, K1C extruders as feeders, K1C runout sensors per lane, a BTT Smart Filament Sensor V2 after the merger, K1C fans, 12 V feed.

- `page.html`: page content (built into `docs/2-roll-feeder/` by `tools/build_site.py`)
- `bom.csv`: parts list
- `schematic.svg`: from `tools/gen_schematic.py`
- `images/`: architecture, housing and top-view drawings
