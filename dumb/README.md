# Dumb dryer

The cheapest version: one reel, a 96 W heater (two 50 W resistors), an STC-3028 humidity + temperature controller and a W1209 thermostat for a second heat step. No microcontroller, firmware, scale or Wi-Fi. Runs from the shared 12 V supply.

- `page.html`: the page (built into `docs/dumb/` by `tools/build_site.py`): how it works, settings per material, housing notes, build steps
- `bom.csv`: parts list, Tronic.lk where it stocks the part, AliExpress otherwise (about US$53 per box including the housing filament)
- `wiring.svg`, `images/heat-steps.svg`: drawn by `tools/gen_dumb.py` (`python3 dumb/tools/gen_dumb.py`)

How it works in one line: the STC-3028's humidity relay (dehumidify mode) and temperature relay (heat mode) are in series, so the heater runs only while the box is too humid **and** below the cap. The W1209, set 5 °C under the cap, switches off half the heater for the last few degrees. The KSD301 85 °C thermostat and the 92 °C thermal fuse protect both halves.
