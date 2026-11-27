#!/usr/bin/env python3
"""Drawings for the 1-roll v2 "twin scale" dryer (perfboard build, ESP32-S3, 2.8" touch screen).

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
    d = D(1740, 1170)
    d.text(30, 36, "1-roll v2 (twin scale): schematic, perfboard build", "t")
    d.text(30, 58, "ESP32-S3-DevKitC-1 N16R8, two load cells under the axle ends, 150 W PTC heater, blower, SHT40 chamber probe, "
                   "DS18B20 heater-outlet probe, 2.8\" capacitive touch screen, buzzer. Crossing wires are not joined unless a dot is shown.", "v")
    TOP = 110

    # 12 V in
    d.box(30, 80, 120, 60, "J1 XT60 12 V in", "shared supply")
    d.wire([(150, TOP), (190, TOP)], RED, 4)
    d.o.append(f'<rect x="190" y="{TOP - 9}" width="46" height="18" rx="3" fill="#fff" stroke="#111" stroke-width="1.4"/>')
    d.text(213, TOP - 16, "F1 20 A", "p", "middle")
    d.wire([(236, TOP), (1700, TOP)], RED, 3)
    d.text(1700, TOP - 10, "+12 V", "v", "end")
    d.wire([(150, 130), (170, 130), (170, 150)], BLACK, 4); d.gnd(170, 150)

    # MP1584
    d.box(255, 170, 130, 110, "U2 MP1584", "set to 5.0 V first")
    d.wire([(255, TOP), (255, 230)], RED, 2); d.dot(255, TOP, RED)
    d.wire([(255, 255), (215, 255), (215, 300)], BLACK, 2); d.gnd(215, 300)
    d.term(255, 230, "IN+"); d.term(255, 255, "IN−")
    d.term(385, 230, "OUT+", "end"); d.term(385, 255, "OUT−", "end")

    # ESP32-S3 DevKitC
    UX, UY, UW, UH = 470, 170, 440, 530
    d.o.append(f'<rect class="mod" x="{UX}" y="{UY}" width="{UW}" height="{UH}" rx="6"/>')
    d.text(UX + UW / 2, UY + 22, "U1 ESP32-S3-DevKitC-1 N16R8", "r", "middle")
    d.text(UX + UW / 2, UY + 40, "USB-C: power + flashing · 16 MB flash, 8 MB PSRAM", "p", "middle")
    d.wire([(385, 230), (470, 230)], ORANGE, 2); d.text(428, 222, "5 V", "p", "middle")
    d.wire([(385, 255), (470, 255)], BLACK, 2)
    d.dot(408, 255, BLACK); d.wire([(408, 255), (408, 300)], BLACK, 2); d.gnd(408, 300)
    d.term(470, 230, "5V"); d.term(470, 255, "GND")
    d.wire([(470, 320), (445, 320)], ORANGE, 2); d.flag(445, 320, "3V3", ORANGE); d.term(470, 320, "3V3 out")
    for y, lab in ((370, "GPIO1  SCK L"), (400, "GPIO2  DT L"), (550, "GPIO38  SCK R"), (580, "GPIO39  DT R")):
        d.term(470, y, lab)
    RX = UX + UW
    for y, lab in ((260, "blower  GPIO5"), (425, "buzzer  GPIO6"), (580, "heater  GPIO4")):
        d.term(RX, y, lab, "end")
    for x, lab in ((500, "GPIO9"), (560, "GPIO8"), (640, "GPIO7")):
        d.pin_bottom(x, 700, lab)
    disp = [("10", "CS"), ("11", "SDI/MOSI"), ("12", "SCK"), ("13", "DC/RS"), ("14", "RESET"), ("47", "LED"),
            ("15", "CTP_SDA"), ("16", "CTP_SCL"), ("17", "CTP_INT"), ("18", "CTP_RST")]
    DX0, DP = 700, 22
    for k, (g, name) in enumerate(disp):
        x = DX0 + k * DP
        d.o.append(f'<circle cx="{x}" cy="700" r="5" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        d.o.append(f'<text class="p" x="{x + 4}" y="690" transform="rotate(-90 {x + 4} 690)">GPIO{g}</text>')
    d.text(755, 640, "display (SPI)", "p", "middle"); d.text(865, 640, "touch (I2C 1)", "p", "middle")
    d.text(690, 480, "spare: GPIO21, 40, 41, 42", "p", "middle")
    d.text(690, 496, "(not 0, 3, 45, 46: strapping; 35-37: PSRAM)", "p", "middle")

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

    # sensor I2C: SCL x=500, SDA x=560, to the SHT40 probe
    d.wire([(500, 700), (500, 850)], BLUE, 2); d.wire([(560, 700), (560, 870)], GREEN, 2)
    d.text(494, 722, "SCL", "p", "end"); d.text(566, 722, "SDA", "p")
    d.dot(560, 740, GREEN); d.res_h(560, 610, 740, "", GREEN); d.flag(610, 740, "3V3", ORANGE); d.text(585, 762, "R7 4.7k", "p", "middle")
    d.dot(500, 780, BLUE); d.res_h(500, 548, 780, "", BLUE); d.flag(548, 780, "3V3", ORANGE); d.text(524, 802, "R8 4.7k", "p", "middle")
    d.wire([(500, 850), (290, 850), (290, 900)], BLUE, 2)
    d.wire([(560, 870), (340, 870), (340, 900)], GREEN, 2)
    d.plain(230, 900, 160, 90, [("P1 SHT40 probe", "r"), ("chamber air, I2C 0x44", "p")])
    d.pin_top(290, 900, "SCL"); d.pin_top(340, 900, "SDA")
    d.flag_down(270, 990, "3V3"); d.wire([(360, 990), (360, 1000)], BLACK, 2); d.gnd(360, 1000)
    # DS18B20
    d.wire([(640, 700), (640, 900)], PURPLE, 2); d.text(646, 722, "1-wire", "p")
    d.dot(640, 820, PURPLE); d.res_h(596, 640, 820, "", PURPLE); d.flag(596, 820, "3V3", ORANGE); d.text(618, 842, "R9 4.7k", "p", "middle")
    d.plain(592, 900, 92, 90, [("P2 DS18B20", "r"), ("heater outlet", "p")])
    d.pin_top(640, 900, "DQ")
    d.flag_down(612, 990, "3V3"); d.wire([(664, 990), (664, 1000)], BLACK, 2); d.gnd(664, 1000)
    # touch screen
    DY = 900
    d.o.append(f'<rect class="mod" x="690" y="{DY}" width="240" height="110" rx="6"/>')
    for k, (g, name) in enumerate(disp):
        x = DX0 + k * DP
        col = PURPLE if k < 6 else TEAL
        d.wire([(x, 700), (x, DY)], col, 2)
        d.o.append(f'<circle cx="{x}" cy="{DY}" r="5" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        d.o.append(f'<text class="p" x="{x + 4}" y="{DY + 12}" transform="rotate(90 {x + 4} {DY + 12})">{name}</text>')
    d.text(810, DY + 84, "DISP1 2.8\" ILI9341 320x240", "r", "middle")
    d.text(810, DY + 100, "+ FT6336 capacitive touch", "p", "middle")
    d.flag_down(712, DY + 110, "VCC 3V3")
    d.wire([(910, DY + 110), (910, DY + 118)], BLACK, 2); d.gnd(910, DY + 118)

    # blower: Q2 IRLZ44N low side
    BX = 1030
    d.wire([(BX, TOP), (BX, 150)], RED, 3); d.dot(BX, TOP, RED)
    d.box(BX - 50, 150, 100, 50, "blower", "5015 12 V")
    d.wire([(BX, 200), (BX, 230)], BLACK, 3)
    d.dot(BX, 130, RED); d.wire([(BX, 130), (BX + 80, 130)], RED, 2)
    d.diode_v(BX + 80, 130, 215, "D1 1N5819")
    d.wire([(BX + 80, 215), (BX, 215)], BLACK, 2); d.dot(BX, 215, BLACK)
    d.box(BX - 25, 230, 50, 60, "Q2", "")
    d.text(BX + 32, 270, "IRLZ44N", "p")
    d.text(BX + 32, 244, "D", "p"); d.text(BX + 32, 290, "S", "p")
    d.wire([(BX, 290), (BX, 300)], BLACK, 2); d.gnd(BX, 300)
    d.wire([(RX, 260), (RX + 18, 260)], GREEN, 2); d.res_h(RX + 18, RX + 68, 260, "R4 100 Ω", GREEN)
    d.wire([(RX + 68, 260), (BX - 25, 260)], GREEN, 2)
    d.dot(RX + 82, 260, GREEN); d.res_v(RX + 82, 260, 335, "R5 10k", GREEN, right=False); d.gnd(RX + 82, 335)

    # buzzer: Q3 2N2222A
    ZX = 1200
    d.flag(ZX, 345, "5V", ORANGE)
    d.box(ZX - 45, 345, 90, 45, "BZ1 buzzer", "5 V active")
    d.wire([(ZX, 390), (ZX, 400)], BLACK, 2)
    d.box(ZX - 25, 400, 50, 60, "Q3", "")
    d.text(ZX + 32, 436, "2N2222A", "p")
    d.wire([(ZX, 460), (ZX, 470)], BLACK, 2); d.gnd(ZX, 470)
    d.wire([(RX, 425), (1060, 425)], YELLOW, 2); d.res_h(1060, 1140, 425, "R6 1 kΩ", YELLOW)
    d.wire([(1140, 425), (ZX - 25, 425)], YELLOW, 2)

    # heater switch: PC817 -> IRF3205, gate from 12 V
    PX = 1290
    d.wire([(RX, 580), (1200, 580)], PURPLE, 2)
    d.res_h(1200, PX, 580, "R1 470 Ω", PURPLE)
    d.box(PX, 545, 100, 110, "OK1 PC817", "")
    d.term(PX, 580, "1"); d.term(PX, 620, "2")
    d.wire([(PX, 620), (PX - 25, 620), (PX - 25, 645)], BLACK, 2); d.gnd(PX - 25, 645)
    d.term(PX + 100, 580, "4", "end"); d.term(PX + 100, 620, "3", "end")
    d.wire([(PX + 100, 580), (PX + 130, 580)], RED, 2)
    d.res_v(PX + 130, 580, TOP, "R2 1 kΩ", RED, right=False); d.dot(PX + 130, TOP, RED)
    d.wire([(PX + 100, 620), (PX + 190, 620), (PX + 190, 520), (PX + 240, 520)], YELLOW, 2)
    d.dot(PX + 155, 620, YELLOW); d.res_v(PX + 155, 620, 700, "R3 10k", YELLOW, right=False); d.gnd(PX + 155, 700)
    d.text(PX + 198, 512, "G", "p")

    # heater chain, heavy wire
    HX = 1560
    d.wire([(HX, TOP), (HX, 150)], RED, 4); d.dot(HX, TOP, RED)
    d.box(HX - 65, 150, 130, 46, "TS1 KSD301", "85 °C, 16 A", "safe")
    d.wire([(HX, 196), (HX, 216)], RED, 4)
    d.box(HX - 65, 216, 130, 46, "TF1 thermal fuse", "92 °C, 15 A", "safe")
    d.wire([(HX, 262), (HX, 300)], RED, 4)
    d.box(HX - 60, 300, 120, 64, "H1 PTC heater", "12 V 150 W")
    d.wire([(HX, 364), (HX, 480)], BROWN, 4)
    d.text(HX + 8, 410, "heater −", "p"); d.text(HX + 8, 426, "14 AWG", "p")
    d.box(HX - 30, 480, 60, 80, "Q1", "")
    d.text(HX, 528, "IRF3205", "p", "middle")
    d.text(HX + 36, 494, "D", "p"); d.text(HX + 36, 556, "S", "p")
    d.wire([(HX, 560), (HX, 620)], BLACK, 4); d.gnd(HX, 620)
    d.text(HX + 14, 640, "14 AWG back to J1", "p")
    d.text(HX + 14, 656, "Q1: 25 mm heatsink", "p")

    notes = [
        "Heater path (thick lines): 150 W at 12 V is about 12.5 A. 20 A fuse, 14 AWG silicone wire soldered straight to Q1's drain and source legs, "
        "not along perfboard tracks; KSD301 16 A and thermal fuse 15 A (the common 10 A ones are too small).",
        "Q1's gate is driven from 12 V through the PC817 (about 11 V on). At power-up GPIO4 floats: the PC817 stays dark and R3 holds Q1 off; R5 holds the blower's Q2 off.",
        "Touch screen: SPI for the picture, its touch chip on a second I2C bus (address 0x38, the same as an AHT20). LED is the backlight's control input "
        "(the module switches it with its own transistor); if yours lights only with LED on 3V3, wire it there.",
        "Load cell wire colours vary between makers: a cell that reads backwards still works (the calibration takes the sign), but swap A+/A− for tidiness.",
        "On the board: C1 100 µF 25 V and C2 100 nF across the 12 V input, C3 100 nF across 3V3/GND near the HX711s. All grounds (⏚) meet at J1's black wire.",
    ]
    for i, n in enumerate(notes):
        d.text(30, 1060 + i * 19, n, "v")
    d.save(ROOT / "wiring.svg", "1-roll v2 schematic")


def perfboard():
    """Top view of a 90 x 150 mm dot board (component side), 5 px per mm."""
    S, OX, OY = 5, 60, 90
    W, H = 90, 150
    d = D(OX * 2 + W * S + 330, OY + H * S + 70)
    d.text(30, 36, "1-roll v2: perfboard layout (90 × 150 mm dot board, component side)", "t")
    d.text(30, 58, "Modules in female headers; probes, blower and cells on JST-XH sockets; the screen on a 14-pin header.", "v")
    d.o.append(f'<rect x="{OX}" y="{OY}" width="{W * S}" height="{H * S}" fill="#f1ead2" stroke="#8d6e63" stroke-width="2"/>')
    dots = []
    x = 2.0
    while x < W - 1:
        y = 2.0
        while y < H - 1:
            dots.append(f'<circle cx="{OX + x * S:.1f}" cy="{OY + y * S:.1f}" r="1.0" fill="#c8b98f"/>')
            y += 2.54
        x += 2.54
    d.o.append("".join(dots))

    def part(x, y, w, h, title, sub="", cls="bx"):
        d.o.append(f'<rect class="{cls}" x="{OX + x * S}" y="{OY + y * S}" width="{w * S}" height="{h * S}" rx="4" fill-opacity="0.92"/>')
        d.text(OX + (x + w / 2) * S, OY + (y + h / 2) * S - (2 if sub else -4), title, "r", "middle")
        if sub:
            d.text(OX + (x + w / 2) * S, OY + (y + h / 2) * S + 14, sub, "p", "middle")

    part(2, 2, 11, 9, "J1", "12 V in", "safe")
    part(2, 13, 11, 8, "C1 C2", "")
    part(15, 2, 22, 17, "U2 MP1584", "5.0 V")
    part(40, 2, 20, 15, "OK1 PC817", "R1–R3")
    part(62, 2, 26, 26, "Q1 IRF3205", "on heatsink", "safe")
    part(40, 20, 20, 15, "Q2 IRLZ44N", "D1 R4 R5")
    part(15, 22, 22, 14, "BZ1", "Q3 R6")
    part(0, 40, 70, 26, "U1 ESP32-S3-DevKitC-1", "USB-C → left edge", "mod")
    part(72, 40, 16, 14, "R7–R9", "C3")
    part(4, 72, 52, 8, "J9 screen", "14-pin header")
    part(62, 72, 26, 7, "J2", "blower")
    part(62, 82, 26, 9, "J3", "SHT40 probe")
    part(62, 94, 26, 8, "J5", "DS18B20")
    part(4, 116, 36, 21, "U3 HX711 L", "", "mod")
    part(50, 116, 36, 21, "U4 HX711 R", "", "mod")
    part(10, 139, 22, 8, "J7", "cell L")
    part(56, 139, 22, 8, "J8", "cell R")
    d.text(OX + W * S / 2, OY + H * S + 24, "90 mm", "v", "middle")
    d.text(OX - 12, OY + H * S / 2, "150 mm", "v", "end")
    notes = ["Heater current never runs on the board:",
             "14 AWG from TF1 to the heater, heater −",
             "soldered to Q1's drain leg, and Q1's",
             "source leg straight back to J1's black wire.",
             "",
             "The HX711s sit at the far end from Q1",
             "and the MP1584: switching adds scale noise.",
             "",
             "Wire 3V3 and GND as two bare buses",
             "along the board's underside.",
             "",
             "J9 to the screen: 14 short Dupont wires",
             "(or a ribbon), under 20 cm for 40 MHz SPI."]
    for i, n in enumerate(notes):
        d.text(OX + W * S + 30, OY + 20 + i * 20, n, "v")
    d.save(ROOT / "images" / "perfboard.svg", "1-roll v2 perfboard layout")


def front_panel():
    """The 90 x 70 mm front, 6 px per mm."""
    S, OX, OY = 6, 60, 90
    W, H = 90, 70
    d = D(OX * 2 + W * S + 330, OY + H * S + 110)
    d.text(30, 36, "1-roll v2: front panel (90 × 70 mm)", "t")
    d.text(30, 58, "2.8\" touch screen module (about 86 × 50 mm). Measure your module before printing: sizes and the screen's offset vary.", "v")
    d.o.append(f'<rect x="{OX}" y="{OY}" width="{W * S}" height="{H * S}" rx="12" fill="#eceff1" stroke="#455a64" stroke-width="2"/>')
    mx, my, mw, mh = (W - 86) / 2, (H - 50) / 2, 86, 50
    d.o.append(f'<rect x="{OX + mx * S}" y="{OY + my * S}" width="{mw * S}" height="{mh * S}" fill="none" stroke="#90a4ae" stroke-dasharray="6 4" stroke-width="1.5"/>')
    ww, wh = 59, 45
    wx, wy = (W - ww) / 2, (H - wh) / 2
    d.o.append(f'<rect x="{OX + wx * S}" y="{OY + wy * S}" width="{ww * S}" height="{wh * S}" fill="#111"/>')
    d.o.append(f'<text x="{OX + W * S / 2}" y="{OY + H * S / 2 + 5}" text-anchor="middle" style="font:14px Inter,Arial,sans-serif;fill:#fff">window 59 × 45 mm</text>')
    for hx, hy in ((mx + 3, my + 3), (mx + mw - 3, my + 3), (mx + 3, my + mh - 3), (mx + mw - 3, my + mh - 3)):
        d.o.append(f'<circle cx="{OX + hx * S}" cy="{OY + hy * S}" r="{1.6 * S}" fill="#fff" stroke="#455a64" stroke-width="1.4"/>')
    d.text(OX + W * S / 2, OY + H * S + 24, "90 mm", "v", "middle")
    d.text(OX - 12, OY + H * S / 2, "70 mm", "v", "end")
    notes = ["Dashed: the screen module behind the",
             "panel, on M3 screws into printed",
             "standoffs at its corner holes.",
             "The module is 86 mm wide: the panel",
             "needs about 87 mm clear behind it.",
             "",
             "The 59 × 45 mm window shows the",
             "57.6 × 43.2 mm picture; the glass",
             "touch surface sits in it.",
             "",
             "No button: everything is on the screen.",
             "The backlight goes off after 10 min;",
             "a touch wakes it, and a fault does too."]
    for i, n in enumerate(notes):
        d.text(OX + W * S + 30, OY + 20 + i * 20, n, "v")
    d.save(ROOT / "images" / "front-panel.svg", "1-roll v2 front panel")


if __name__ == "__main__":
    schematic()
    perfboard()
    front_panel()
