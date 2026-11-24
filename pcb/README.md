# Dryer controller board (JLCPCB assembly)

One controller board for both dryer versions. The 2-roll build fits everything; the 1-roll build leaves the feeder parts off. KiCad 7 project, generated from one table in `tools/gen_kicad.py`.

| File | What |
| --- | --- |
| `schematic.svg`, `schematic.pdf` | The board with every wire drawn, for reading (from `tools/gen_schematic_svg.py`; PDF via `node tools/svg_to_pdf.js`) |
| `dryer-controller.kicad_sch` | Schematic (open in KiCad 7 or newer) |
| `dryer.kicad_sym`, `dryer.pretty/` | Project library: ESP32-C3 SuperMini socket, TMC2209 StepStick, UCC27517 |
| `export/dryer-controller.pdf`, `.svg`, `.net` | Schematic PDF/SVG and netlist |
| `jlcpcb/bom-2-roll.csv`, `jlcpcb/bom-1-roll.csv` | JLCPCB assembly BOMs (Comment, Designator, Footprint, LCSC Part #) |
| `jlcpcb/hand-fit-*.csv` | Sockets you solder yourself (the SuperMini and TMC2209 modules plug into them) |

## Status

- **Done:** schematic and BOMs. Every LCSC number was checked on its JLCPCB page on 2026-11-24 (manufacturer part matches, all in stock). The exported netlist was checked pin by pin against the design table, and every symbol pin was checked against a pad in its footprint.
- **Not done yet:** PCB layout. JLCPCB also needs Gerbers and a placement (CPL) file, which come from the layout.

## What's on the board

| Block | Parts | Notes |
| --- | --- | --- |
| 12 V in | TB1 (24 A screw terminal), C1 100 µF, C2 | Feed from the XT60 and the inline 15 A fuse |
| 5 V buck | U2 AP63205WU-7, L1 4.7 µH, C3 10 µF, C5/C6 2×22 µF, C4 100 nF | Values from the AP63205 datasheet, Table 3 |
| Controller | U1 ESP32-C3 SuperMini in two 1×8 sockets | R1-R3 4.7 k (1-wire, I2C), R4 1 k (motion signal) |
| I/O expander | U3 MCP23017 | Lane sensors, BTT runout, button, buzzer, feeder EN/DIR |
| Heater switch | U4 UCC27517 gate driver, Q1 AOD4184A, R7 10 Ω, R8/R9 10 k | 12 V gate drive (see below) |
| Fans, buzzer | Q2-Q4 AO3400A, D1/D2 B5819W flyback diodes | Low-side switches |
| Connectors | JST XH (J3-J17), TB2 heater | Same numbering as the wiring diagrams |
| Feeders (2-roll) | U10/U11 TMC2209 StepStick sockets, C10/C11 100 µF, J16/J17 | Standalone, 1/8 step |

**Heater switch:** the earlier plan drove an IRLB8721 straight from the ESP32's 3.3 V. At 12.5 A that runs too hot (roughly 15 mΩ at 3.3 V, about 2.3 W in a TO-220 without a heatsink). The board drives the AOD4184A (7 mΩ at 10 V) from a UCC27517 running on 12 V instead: about 1-1.6 W, spread into a copper pour under the TO-252 tab. The driver input has a pull-down, so the heater stays off while the ESP32 boots.

**Pin map:** the same as the 2-roll pin map in the docs. A 1-roll box built on this board uses it too: the BTT runout switch, button and buzzer go through the MCP23017, not straight to GPIO3, GPIO9 and GPIO10.

## Check before ordering

- [ ] **SuperMini socket spacing:** the footprint assumes the two header rows are 15.24 mm apart. Measure your board.
- [ ] **TMC2209 module pins 4-6** (PDN/UART, CLK) differ between makers; they're left unconnected. Check your module's silkscreen against `dryer.kicad_sym`.
- [ ] **Footprints to compare with the part drawings:** L1 uses the 4030 Changjiang footprint for the XR XRNR4030; TB1/TB2 use the Phoenix MKDS 5.08 mm footprint for the KF128 terminal.
- [ ] **Layout rules for the 12.5 A path** (TB1 → TB2 → Q1): wide pours, 2 oz copper, copper area under Q1.
- [ ] **Stock:** check again when ordering; MCP23017 (C47023) has had low stock at times.

## Ordering at JLCPCB

1. Lay out the PCB in KiCad (open `dryer-controller.kicad_sch`, then Tools → Update PCB from Schematic).
2. Export Gerbers, drill files and the placement (CPL) file.
3. Order PCB assembly and upload `jlcpcb/bom-2-roll.csv` (or `bom-1-roll.csv`) as the BOM. The JST, screw-terminal and buzzer parts are through-hole: keep them for JLCPCB's through-hole assembly, or remove those lines and solder them yourself.
4. Solder the sockets from `jlcpcb/hand-fit-*.csv` (C27438, 1×8 female, 2 per module).

## Regenerate

```bash
python3 pcb/tools/gen_kicad.py
```
