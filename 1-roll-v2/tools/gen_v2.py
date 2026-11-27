#!/usr/bin/env python3
"""Drawings for the 1-roll v2 "twin scale" dryer (perfboard build).

Writes 1-roll-v2/wiring.svg (the schematic), images/perfboard.svg and images/front-panel.svg.
Run from the repo root:
    python3 1-roll-v2/tools/gen_v2.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT.parent / "dumb" / "basic" / "tools"))
from gen_basic import Draw, RED, BLACK, ORANGE, YELLOW, BLUE, GREY, GREEN, PURPLE, BROWN  # noqa: E402

TEAL, PINK, WHITE_W = "#00838f", "#ad1457", "#bdbdbd"


class D(Draw):
    def flag_down(self, x, y, label, color=ORANGE):
        """Net label hanging below (x, y)."""
        self.wire([(x, y), (x, y + 14)], color, 2)
        self.wire([(x - 8, y + 14), (x + 8, y + 14)], color, 2)
        self.text(x, y + 28, label, "p", "middle")

    def plain(self, x, y, w, h, lines, cls="bx"):
        """Box with its own text lines (title first), placed from y + 40 down."""
        self.o.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>')
        for i, (s, c) in enumerate(lines):
            self.text(x + w / 2, y + 40 + i * 16, s, c, "middle")


def schematic():
    d = D(1560, 1160)
    d.text(30, 36, "1-roll v2 (twin scale): schematic, perfboard build", "t")
    d.text(30, 58, "ESP32-C3 SuperMini, two load cells under the axle ends, 150 W PTC heater, blower, SHT40 chamber probe, "
                   "DS18B20 heater-outlet probe, OLED, button, buzzer. Crossing wires are not joined unless a dot is shown.", "v")
    TOP = 110

    # 12 V in
    d.box(30, 80, 120, 60, "J1 XT60 12 V in", "shared supply")
    d.wire([(150, TOP), (190, TOP)], RED, 4)
    d.o.append(f'<rect x="190" y="{TOP - 9}" width="46" height="18" rx="3" fill="#fff" stroke="#111" stroke-width="1.4"/>')
    d.text(213, TOP - 16, "F1 20 A", "p", "middle")
    d.wire([(236, TOP), (1520, TOP)], RED, 3)
    d.text(1520, TOP - 10, "+12 V", "v", "end")
    d.wire([(150, 130), (170, 130), (170, 150)], BLACK, 4); d.gnd(170, 150)

    # MP1584
    d.box(255, 170, 130, 110, "U2 MP1584", "set to 5.0 V first")
    d.wire([(255, TOP), (255, 230)], RED, 2); d.dot(255, TOP, RED)
    d.wire([(255, 255), (215, 255), (215, 300)], BLACK, 2); d.gnd(215, 300)
    d.term(255, 230, "IN+"); d.term(255, 255, "IN−")
    d.term(385, 230, "OUT+", "end"); d.term(385, 255, "OUT−", "end")

    # SuperMini
    UX, UY, UW, UH = 470, 170, 260, 530
    d.o.append(f'<rect class="mod" x="{UX}" y="{UY}" width="{UW}" height="{UH}" rx="6"/>')
    d.text(UX + UW / 2, UY + 22, "U1 ESP32-C3 SuperMini", "r", "middle")
    d.text(UX + UW / 2, UY + 40, "USB-C: power + flashing", "p", "middle")
    d.wire([(385, 230), (470, 230)], ORANGE, 2); d.text(428, 222, "5 V", "p", "middle")
    d.wire([(385, 255), (470, 255)], BLACK, 2)
    d.dot(408, 255, BLACK); d.wire([(408, 255), (408, 300)], BLACK, 2); d.gnd(408, 300)
    d.term(470, 230, "5V"); d.term(470, 255, "GND")
    d.wire([(470, 320), (445, 320)], ORANGE, 2); d.flag(445, 320, "3V3", ORANGE); d.term(470, 320, "3V3 out")
    for y, lab in ((370, "GPIO0  SCK L"), (400, "GPIO1  DT L"), (550, "GPIO3  SCK R"), (580, "GPIO6  DT R")):
        d.term(470, y, lab)
    for y, lab in ((260, "blower  GPIO5"), (425, "buzzer  GPIO10"), (580, "heater  GPIO4")):
        d.term(730, y, lab, "end")
    for x, lab in ((500, "GPIO7"), (560, "GPIO8"), (640, "GPIO2"), (700, "GPIO20")):
        d.pin_bottom(x, 700, lab)
    d.text(600, 470, "spare: GPIO9 (BOOT button),", "p", "middle")
    d.text(600, 486, "GPIO21", "p", "middle")

    # load cells + HX711s
    for n, (y0, side) in enumerate(((330, "left"), (510, "right"))):
        hx = 180
        d.o.append(f'<rect class="mod" x="{hx}" y="{y0}" width="150" height="110" rx="6"/>')
        d.text(hx + 75, y0 + 22, f"U{3 + n} HX711 {'L' if n == 0 else 'R'}", "r", "middle")
        pins = [("E+", RED, "red"), ("E−", BLACK, "black"), ("A−", WHITE_W, "white"), ("A+", GREEN, "green")]
        cx = 30
        d.o.append(f'<rect class="bx" x="{cx}" y="{y0 + 5}" width="100" height="100" rx="6"/>')
        d.text(cx + 50, y0 + 45, f"LC{n + 1}", "r", "middle")
        d.text(cx + 50, y0 + 63, f"{side} end", "p", "middle")
        d.text(cx + 50, y0 + 79, "3 kg bar cell", "p", "middle")
        for i, (lab, col, name) in enumerate(pins):
            y = y0 + 38 + i * 18
            d.wire([(cx + 100, y), (hx, y)], col, 2.4)
            d.text(cx + 125, y - 4, name, "p", "middle")
            d.term(hx, y, lab)
        sck, dt = y0 + 40, y0 + 70
        d.term(hx + 150, sck, "SCK", "end"); d.term(hx + 150, dt, "DT", "end")
        d.wire([(hx + 150, sck), (470, sck)], TEAL, 2)
        d.wire([(hx + 150, dt), (470, dt)], PINK, 2)
        d.flag(hx + 75, y0, "3V3", ORANGE)
        d.wire([(hx + 75, y0 + 110), (hx + 75, y0 + 120)], BLACK, 2); d.gnd(hx + 75, y0 + 120)

    # I2C: SCL x=500, SDA x=560
    d.wire([(500, 700), (500, 900)], BLUE, 2); d.wire([(560, 700), (560, 900)], GREEN, 2)
    d.text(494, 722, "SCL", "p", "end"); d.text(566, 722, "SDA", "p")
    d.dot(560, 740, GREEN); d.res_h(560, 610, 740, "", GREEN); d.flag(610, 740, "3V3", ORANGE); d.text(585, 762, "R7 4.7k", "p", "middle")
    d.dot(500, 780, BLUE); d.res_h(500, 548, 780, "", BLUE); d.flag(548, 780, "3V3", ORANGE); d.text(524, 802, "R8 4.7k", "p", "middle")
    # SHT40 probe
    d.dot(500, 850, BLUE); d.wire([(500, 850), (290, 850), (290, 900)], BLUE, 2)
    d.dot(560, 870, GREEN); d.wire([(560, 870), (340, 870), (340, 900)], GREEN, 2)
    d.plain(230, 900, 160, 90, [("P1 SHT40 probe", "r"), ("chamber air, I2C 0x44", "p")])
    d.pin_top(290, 900, "SCL"); d.pin_top(340, 900, "SDA")
    d.flag_down(270, 990, "3V3"); d.wire([(360, 990), (360, 1000)], BLACK, 2); d.gnd(360, 1000)
    # OLED
    d.plain(430, 900, 180, 90, [("DISP1 OLED, I2C 0x3C", "r"), ("2.42\" SSD1309 (or 1.3\" SH1106)", "p")])
    d.pin_top(500, 900, "SCL"); d.pin_top(560, 900, "SDA")
    d.flag_down(470, 990, "3V3"); d.wire([(590, 990), (590, 1000)], BLACK, 2); d.gnd(590, 1000)
    # DS18B20
    d.wire([(640, 700), (640, 900)], PURPLE, 2); d.text(646, 722, "1-wire", "p")
    d.dot(640, 820, PURPLE); d.res_h(640, 688, 820, "", PURPLE); d.flag(688, 820, "3V3", ORANGE); d.text(664, 842, "R9 4.7k", "p", "middle")
    d.plain(620, 900, 150, 90, [("P2 DS18B20 probe", "r"), ("heater outlet", "p")])
    d.pin_top(640, 900, "DQ")
    d.flag_down(660, 990, "3V3"); d.wire([(740, 990), (740, 1000)], BLACK, 2); d.gnd(740, 1000)
    # button
    d.wire([(700, 700), (700, 760), (850, 760)], BROWN, 2)
    d.dot(770, 760, BROWN); d.res_v(770, 760, 708, "R10 10k", BROWN); d.flag(770, 708, "3V3", ORANGE)
    d.box(850, 735, 110, 50, "SW1 button", "12 mm, front")
    d.term(850, 760, "")
    d.wire([(960, 760), (985, 760), (985, 775)], BLACK, 2); d.gnd(985, 775)

    # blower: Q2 IRLZ44N low side
    BX = 880
    d.wire([(BX, TOP), (BX, 150)], RED, 3); d.dot(BX, TOP, RED)
    d.box(830, 150, 100, 50, "blower", "5015 12 V")
    d.wire([(BX, 200), (BX, 230)], BLACK, 3)
    d.dot(BX, 130, RED); d.wire([(BX, 130), (960, 130)], RED, 2)
    d.diode_v(960, 130, 215, "D1 1N5819")
    d.wire([(960, 215), (BX, 215)], BLACK, 2); d.dot(BX, 215, BLACK)
    d.box(855, 230, 50, 60, "Q2", "")
    d.text(912, 270, "IRLZ44N", "p")
    d.text(912, 244, "D", "p"); d.text(912, 290, "S", "p")
    d.wire([(BX, 290), (BX, 300)], BLACK, 2); d.gnd(BX, 300)
    d.wire([(730, 260), (752, 260)], GREEN, 2); d.res_h(752, 818, 260, "R4 100 Ω", GREEN)
    d.wire([(818, 260), (855, 260)], GREEN, 2)
    d.dot(838, 260, GREEN); d.res_v(838, 260, 335, "R5 10k", GREEN, right=False); d.gnd(838, 335)

    # buzzer: Q3 2N2222A
    ZX = 1060
    d.flag(ZX, 345, "5V", ORANGE)
    d.box(1015, 345, 90, 45, "BZ1 buzzer", "5 V active")
    d.wire([(ZX, 390), (ZX, 400)], BLACK, 2)
    d.box(1035, 400, 50, 60, "Q3", "")
    d.text(1092, 436, "2N2222A", "p")
    d.wire([(ZX, 460), (ZX, 470)], BLACK, 2); d.gnd(ZX, 470)
    d.wire([(730, 425), (880, 425)], YELLOW, 2); d.res_h(880, 960, 425, "R6 1 kΩ", YELLOW)
    d.wire([(960, 425), (1035, 425)], YELLOW, 2)

    # heater switch: PC817 -> IRF3205, gate from 12 V
    d.wire([(730, 580), (1060, 580)], PURPLE, 2)
    d.res_h(1060, 1150, 580, "R1 470 Ω", PURPLE)
    d.box(1150, 545, 100, 110, "OK1 PC817", "")
    d.term(1150, 580, "1"); d.term(1150, 620, "2")
    d.wire([(1150, 620), (1125, 620), (1125, 645)], BLACK, 2); d.gnd(1125, 645)
    d.term(1250, 580, "4", "end"); d.term(1250, 620, "3", "end")
    d.wire([(1250, 580), (1280, 580)], RED, 2)
    d.res_v(1280, 580, TOP, "R2 1 kΩ", RED, right=False); d.dot(1280, TOP, RED)
    d.wire([(1250, 620), (1340, 620), (1340, 520), (1390, 520)], YELLOW, 2)
    d.dot(1305, 620, YELLOW); d.res_v(1305, 620, 700, "R3 10k", YELLOW, right=False); d.gnd(1305, 700)
    d.text(1348, 512, "G", "p")

    # heater chain, heavy wire
    HX = 1420
    d.wire([(HX, TOP), (HX, 150)], RED, 4); d.dot(HX, TOP, RED)
    d.box(1355, 150, 130, 46, "TS1 KSD301", "85 °C, 16 A", "safe")
    d.wire([(HX, 196), (HX, 216)], RED, 4)
    d.box(1355, 216, 130, 46, "TF1 thermal fuse", "92 °C, 15 A", "safe")
    d.wire([(HX, 262), (HX, 300)], RED, 4)
    d.box(1360, 300, 120, 64, "H1 PTC heater", "12 V 150 W")
    d.wire([(HX, 364), (HX, 480)], BROWN, 4)
    d.text(HX + 8, 410, "heater −", "p"); d.text(HX + 8, 426, "14 AWG", "p")
    d.box(1390, 480, 60, 80, "Q1", "")
    d.text(HX, 528, "IRF3205", "p", "middle")
    d.text(HX + 36, 494, "D", "p"); d.text(HX + 36, 556, "S", "p")
    d.wire([(HX, 560), (HX, 620)], BLACK, 4); d.gnd(HX, 620)
    d.text(HX + 14, 640, "14 AWG back to J1", "p")
    d.text(HX + 14, 656, "Q1: 25 mm heatsink", "p")

    notes = [
        "Heater path (red/brown/black thick lines): 150 W at 12 V is about 12.5 A. 20 A fuse, 14 AWG silicone wire soldered straight to Q1's drain and source legs, "
        "not along perfboard tracks; KSD301 16 A and thermal fuse 15 A (the common 10 A ones are too small).",
        "Q1 gate is driven from 12 V through the PC817 (about 11 V on). At power-up GPIO4 floats: the PC817 stays dark and R3 holds Q1 off; R5 holds the blower's Q2 off.",
        "Strapping pins: R9 keeps GPIO2 and R7 keeps GPIO8 high at boot, as the ESP32-C3 needs. Each HX711 has its own clock pin.",
        "Load cell wire colours vary between makers: if a cell reads backwards it still works (the calibration takes the sign), but swap A+/A− for tidiness.",
        "On the board: C1 100 µF 25 V and C2 100 nF across the 12 V input, C3 100 nF across 3V3/GND near the HX711s. All grounds (⏚) meet at J1's black wire.",
    ]
    for i, n in enumerate(notes):
        d.text(30, 1050 + i * 19, n, "v")
    d.save(ROOT / "wiring.svg", "1-roll v2 schematic")


def perfboard():
    """Top view of a 70 x 90 mm dot board (component side), 6 px per mm."""
    S, OX, OY = 6, 60, 90
    W, H = 70, 90
    d = D(OX * 2 + W * S + 300, OY + H * S + 140)
    d.text(30, 36, "1-roll v2: perfboard layout (70 × 90 mm dot board, component side)", "t")
    d.text(30, 58, "Modules sit in female headers so they can be swapped. Sensor and fan leads use JST-XH sockets; only 12 V in uses a screw terminal.", "v")
    d.o.append(f'<rect x="{OX}" y="{OY}" width="{W * S}" height="{H * S}" fill="#f1ead2" stroke="#8d6e63" stroke-width="2"/>')
    # dot grid (every 2.54 mm)
    dots = []
    x = 2.0
    while x < W - 1:
        y = 2.0
        while y < H - 1:
            dots.append(f'<circle cx="{OX + x * S:.1f}" cy="{OY + y * S:.1f}" r="1.1" fill="#c8b98f"/>')
            y += 2.54
        x += 2.54
    d.o.append("".join(dots))

    def part(x, y, w, h, title, sub="", cls="bx"):
        d.o.append(f'<rect class="{cls}" x="{OX + x * S}" y="{OY + y * S}" width="{w * S}" height="{h * S}" rx="4" fill-opacity="0.92"/>')
        d.text(OX + (x + w / 2) * S, OY + (y + h / 2) * S - (2 if sub else -4), title, "r", "middle")
        if sub:
            d.text(OX + (x + w / 2) * S, OY + (y + h / 2) * S + 14, sub, "p", "middle")

    part(2, 2, 10, 8, "J1", "12 V in", "safe")
    part(2, 11, 9, 7, "C1 C2", "")
    part(14, 2, 22, 17, "U2 MP1584", "5.0 V")
    part(42, 2, 26, 24, "Q1 IRF3205", "on heatsink", "safe")
    part(42, 29, 16, 13, "OK1 PC817", "R1–R3")
    part(0, 24, 23, 18, "U1 SuperMini", "USB-C → left edge", "mod")
    part(26, 22, 14, 10, "R7–R10", "pull-ups")
    part(26, 34, 14, 16, "BZ1", "Q3, R6")
    part(42, 45, 16, 13, "Q2 IRLZ44N", "D1 R4 R5")
    part(60, 45, 8, 8, "J2", "blower")
    part(60, 30, 8, 13, "J4", "OLED")
    part(2, 45, 8, 12, "J3", "SHT40")
    part(12, 45, 10, 9, "J5", "DS18B")
    part(60, 55, 8, 6, "J6", "button")
    part(1, 62, 33, 20, "U3 HX711 L", "", "mod")
    part(36, 62, 33, 20, "U4 HX711 R", "", "mod")
    part(6, 83, 13, 6, "J7", "cell L")
    part(42, 83, 13, 6, "J8", "cell R")
    part(25, 52, 14, 8, "C3", "100 nF")
    # dimensions
    d.text(OX + W * S / 2, OY + H * S + 24, "70 mm", "v", "middle")
    d.text(OX - 12, OY + H * S / 2, "90 mm", "v", "end")
    notes = ["Heater current never runs on the board:",
             "14 AWG from TF1 to the heater, heater −",
             "soldered to Q1's drain leg, and Q1's",
             "source leg straight back to J1's black wire.",
             "",
             "Keep the HX711s away from Q1 and the",
             "MP1584: their switching adds scale noise.",
             "",
             "Wire 3V3 and GND as two bare buses",
             "along the board's underside."]
    for i, n in enumerate(notes):
        d.text(OX + W * S + 30, OY + 20 + i * 20, n, "v")
    d.save(ROOT / "images" / "perfboard.svg", "1-roll v2 perfboard layout")


def front_panel():
    """The 90 x 70 mm front, 6 px per mm."""
    S, OX, OY = 6, 60, 90
    W, H = 90, 70
    d = D(OX * 2 + W * S + 320, OY + H * S + 110)
    d.text(30, 36, "1-roll v2: front panel (90 × 70 mm)", "t")
    d.text(30, 58, "2.42\" OLED module (about 73 × 43 mm) and a 12 mm push button. Measure your module before printing: sizes vary a little.", "v")
    d.o.append(f'<rect x="{OX}" y="{OY}" width="{W * S}" height="{H * S}" rx="12" fill="#eceff1" stroke="#455a64" stroke-width="2"/>')
    # module outline (behind), window, holes
    mx, my, mw, mh = (W - 73.5) / 2, 4, 73.5, 43
    d.o.append(f'<rect x="{OX + mx * S}" y="{OY + my * S}" width="{mw * S}" height="{mh * S}" fill="none" stroke="#90a4ae" stroke-dasharray="6 4" stroke-width="1.5"/>')
    wx, wy, ww, wh = (W - 57) / 2, my + 7.5, 57, 30
    d.o.append(f'<rect x="{OX + wx * S}" y="{OY + wy * S}" width="{ww * S}" height="{wh * S}" fill="#111"/>')
    d.text(OX + W * S / 2, OY + (wy + wh / 2) * S + 5, "window 57 × 30 mm", "r", "middle")
    d.o[-1] = d.o[-1].replace('class="r"', 'class="r" fill="#fff" style="fill:#fff"')
    for hx, hy in ((mx + 2.5, my + 2.5), (mx + mw - 2.5, my + 2.5), (mx + 2.5, my + mh - 2.5), (mx + mw - 2.5, my + mh - 2.5)):
        d.o.append(f'<circle cx="{OX + hx * S}" cy="{OY + hy * S}" r="{1.4 * S}" fill="#fff" stroke="#455a64" stroke-width="1.4"/>')
    bx, by = W / 2, 58
    d.o.append(f'<circle cx="{OX + bx * S}" cy="{OY + by * S}" r="{6 * S}" fill="#fff" stroke="#455a64" stroke-width="2"/>')
    d.text(OX + bx * S, OY + by * S + 4, "Ø 12", "p", "middle")
    d.text(OX + W * S / 2, OY + H * S + 24, "90 mm", "v", "middle")
    d.text(OX - 12, OY + H * S / 2, "70 mm", "v", "end")
    notes = ["Dashed: the OLED module behind the",
             "panel, on M2.5 screws into printed",
             "standoffs (holes 2.5 mm from its",
             "corners on most modules).",
             "",
             "Button: short press = next mode or",
             "clear a fault; hold 3 s = tare;",
             "hold 10 s = forget Wi-Fi; held while",
             "powering up = switch display type.",
             "",
             "The buzzer sits on the board inside."]
    for i, n in enumerate(notes):
        d.text(OX + W * S + 30, OY + 20 + i * 20, n, "v")
    d.save(ROOT / "images" / "front-panel.svg", "1-roll v2 front panel")


if __name__ == "__main__":
    schematic()
    perfboard()
    front_panel()
