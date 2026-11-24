# 2-roll feeder

Two reels, each on its own load cell, with a feeder pod that loads the second reel automatically when the printer reports a runout. The shared JLCPCB-assembled controller board (ESP32-C3-WROOM-02, MCP23017, two HX711s, two TMC2209s), K1C extruders as feeders, K1C runout sensors per lane, a BTT Smart Filament Sensor V2 after the merger, 12 V dual-ball-bearing fans, 12 V feed.

- `page.html`: page content (built into `docs/2-roll-feeder/` by `tools/build_site.py`)
- `bom.csv`: parts list
- The electronics are on the shared controller board: schematic in `pcb/schematic.svg`, JLCPCB BOM in `pcb/jlcpcb/`
- `images/`: architecture, housing and top-view drawings
