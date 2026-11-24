# Dryer controller board (JLCPCB assembly)

One controller board for both dryer versions. The 2-roll build fits everything; the 1-roll build leaves the feeder parts off. KiCad 7 project, generated from one table in `tools/gen_kicad.py`.

| File | What |
| --- | --- |
| `schematic.svg`, `schematic.pdf` | The board with every wire drawn, for reading (from `tools/gen_schematic_svg.py`; PDF via `node tools/svg_to_pdf.js`) |
| `dryer-controller.kicad_sch` | Schematic (open in KiCad 7 or newer) |
| `dryer.kicad_sym` | Project symbols: ESP32-C3-WROOM-02, TMC2209-LA, UCC27517 (footprints all come from KiCad's own libraries) |
| `export/dryer-controller.pdf`, `.svg`, `.net` | Schematic PDF/SVG and netlist |
| `jlcpcb/bom-2-roll.csv`, `jlcpcb/bom-1-roll.csv` | JLCPCB assembly BOMs (Comment, Designator, Footprint, LCSC Part #) |

## Status

- **Done:** schematic and BOMs. Every LCSC number was checked on its JLCPCB page on 2026-11-24 (manufacturer part matches, all in stock). The exported netlist was checked pin by pin against the design table, and every symbol pin was checked against a pad in its footprint.
- **Not done yet:** PCB layout. JLCPCB also needs Gerbers and a placement (CPL) file, which come from the layout.

## What's on the board

| Block | Parts | Notes |
| --- | --- | --- |
| 12 V in | J1 XT60PW-M at the board edge, F1 ATO blade-fuse holder (fit a 15 A fuse), C1 100 µF, C2 | The supply lead ends in an XT60-F plug; J1 pokes through the base wall |
| 5 V buck | U2 AP63205WU-7, L1 4.7 µH, C3 10 µF, C5/C6 2×22 µF, C4 100 nF | Values from the AP63205 datasheet, Table 3 |
| Controller | U1 ESP32-C3-WROOM-02-N4 module (4 MB flash, PCB antenna), SW2 reset, SW3 boot, R16/C16 EN delay, R17 boot pull-up | R1-R3 4.7 k (1-wire, I2C), R4 1 k (motion signal) |
| USB and 3.3 V | J2 USB-C (data only, R18/R19 5.1 k on CC), U12 AMS1117-3.3, C12-C15 | Flash and logs over the C3's built-in USB; VBUS isn't connected |
| I/O expander | U3 MCP23017 | Lane sensors, BTT runout, button, buzzer, feeder EN/DIR |
| Heater switch | U4 UCC27517 gate driver, Q1 AOD4184A, R7 10 Ω, R8/R9 10 k | 12 V gate drive (see below) |
| Fans, buzzer | Q2-Q4 AO3400A, D1/D2 B5819W flyback diodes | Low-side switches |
| Scales | U7 (and U8 on the 2-roll) HX711, Q5/Q6 S8550, R20-R23, C17-C26 | Load cells plug straight into J11/J12; 4.3 V excitation |
| Bay sensor | U13 SHT40-BD1B (I2C 0x45), C38 | On the board, which sits in the bay; place it at an edge away from U2, U12, U10, U11 |
| Sensor boards | SB1: U14 SHT40-AD1B (0x44), C37, J18 pads. SB2: U15 DS18B20Z, C39, J19 pads | Small boards on break-off tabs; harness wires solder to their pads and plug into J5/J6 |
| Connectors | JST XH (J3-J17), TB2 heater | Same numbering as the wiring diagrams |
| Feeders (2-roll) | U10/U11 TMC2209-LA-T, C10/C11 100 µF, C27-C36, R24-R31, J16/J17 | Standalone, 1/8 step, about 0.72 A RMS |

**Heater switch:** the earlier plan drove an IRLB8721 straight from the ESP32's 3.3 V. At 12.5 A that runs too hot (roughly 15 mΩ at 3.3 V, about 2.3 W in a TO-220 without a heatsink). The board drives the AOD4184A (7 mΩ at 10 V) from a UCC27517 running on 12 V instead: about 1-1.6 W, spread into a copper pour under the TO-252 tab. The driver input has a pull-down, so the heater stays off while the ESP32 boots.

**Pin map:** the same as the 2-roll pin map in the docs. A 1-roll box built on this board uses it too: the BTT runout switch, button and buzzer go through the MCP23017, not straight to GPIO3, GPIO9 and GPIO10.

## Check before ordering

- [ ] **U1 antenna:** put the module's antenna end at (or over) the board edge, with no copper, parts or traces under it.
- [ ] **U10/U11 TMC2209:** the QFN footprint's exposed pad is 3.75 mm (the datasheet's nominal is 3.7 mm); tie it to a ground pour with the footprint's thermal vias. The pin numbers follow KiCad's own TMC2209-LA symbol (current library); check them against the datasheet's pin table once more before ordering.
- [ ] **Sensor boards SB1, SB2:** lay them out as small boards joined to the main board by mouse-bite tabs, so one order assembles everything; snap them off after delivery. Their nets (SB1_*, SB2_*) reach the main board only through the harness. JLCPCB may count break-off boards as extra designs in the panel: check the quote, or order them as a separate small board. Leave U14's top open to the air, and keep U13 away from the warm parts (a routed slot around it helps).
- [ ] **Motor current:** R24/R28 (39 k) and R25/R29 (10 k) set VREF to about 1.0 V, so about 0.72 A RMS (1.0 A peak) with the 0.11 Ω sense resistors. That suits the K1C extruder motor at feeding speeds; change R24/R28 to change it (I_RMS ≈ VREF / 2.5 V × 1.77 A).
- [ ] **Footprints to compare with the part drawings:** L1 uses the 4030 Changjiang footprint for the XR XRNR4030; TB2 uses the Phoenix MKDS 5.08 mm footprint for the KF128 terminal. **J1 polarity:** KiCad's XT60PW-M footprint marks pad 1 as − and pad 2 as +; check that against the Amass drawing and the lead before the first power-up. **F1:** the Littelfuse 178.6165 holder is specified for boards up to 1.5 mm thick; order 1.6 mm boards only after checking its pins still seat, or ask for 1.2 mm.
- [ ] **Layout rules for the 12.5 A path** (J1 → F1 → TB2 → Q1): wide pours, 2 oz copper, copper area under Q1.
- [ ] **Stock:** check again when ordering; MCP23017 (C47023) has had low stock at times.

## Ordering at JLCPCB

1. Lay out the PCB in KiCad (open `dryer-controller.kicad_sch`, then Tools → Update PCB from Schematic).
2. Export Gerbers, drill files and the placement (CPL) file.
3. Order PCB assembly and upload `jlcpcb/bom-2-roll.csv` (or `bom-1-roll.csv`) as the BOM. Every part on the board is in JLCPCB's library, so it arrives fully assembled. The JST, screw-terminal and buzzer parts are through-hole: keep them for JLCPCB's through-hole assembly, or remove those lines and solder them yourself.
4. One order uses one BOM. For a mix of 2-roll and 1-roll boxes, either order all boards with the 2-roll BOM (the unused feeder and second-scale parts do no harm) or place two orders.
5. Flash the first firmware over USB-C with the 12 V feed plugged in (hold BOOT, tap RESET if it doesn't enter download mode); updates after that go over Wi-Fi.

**Cost (checked on JLCPCB 2026-11-24):** parts about US$16 per 2-roll board and US$9 per 1-roll board, plus JLCPCB's US$3 fee per extended part type per order (16 types on the 2-roll BOM, so about US$48 per order), the PCB, and assembly setup. For 5 boards, roughly US$30-35 per 2-roll board.

## Regenerate

```bash
python3 pcb/tools/gen_kicad.py
```
