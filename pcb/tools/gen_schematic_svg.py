#!/usr/bin/env python3
"""Draw the dryer controller board as a wired schematic: pcb/schematic.svg.

Same parts and nets as the KiCad design (pcb/tools/gen_kicad.py), drawn the way
a person reads a circuit: real wires from each ESP32 pin through its resistor
and MOSFET to its connector. Blue labels are power rails and the few signals
that run between sections. Crossing wires are not connected unless a dot is shown.

Run from the repo root:  python3 pcb/tools/gen_schematic_svg.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H = 1160, 5060
o = []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wire(*pts, blue=False):
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    o.append(f'<path class="{"nw" if blue else "w"}" d="{d}"/>')


def dot(x, y):
    o.append(f'<circle class="sld" cx="{x}" cy="{y}" r="3.2"/>')


def text(x, y, s, cls="r", anchor="start"):
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    o.append(f'<text class="{cls}" x="{x}" y="{y}"{a}>{esc(s)}</text>')


def gnd(x, y):
    o.append(f'<use href="#gnd" x="{x}" y="{y}"/>')


def net(x1, x2, y, name, side="left"):
    """Blue stub from x1 to x2 at y, label at the x1 end (side=left) or x2 end."""
    wire((x1, y), (x2, y), blue=True)
    if side == "left":
        text(x1 - 6, y + 4, name, "n", "end")
    else:
        text(x2 + 6, y + 4, name, "n")


def net_up(x, y1, y2, name):
    """Blue vertical stub up from y1 to y2 with the label above."""
    wire((x, y1), (x, y2), blue=True)
    text(x, y2 - 6, name, "n", "middle")


def res_h(cx, y, val, ref):
    """Horizontal resistor, 50 long; returns (left, right) x."""
    o.append(f'<rect class="bx" x="{cx - 25}" y="{y - 7}" width="50" height="14"/>')
    text(cx, y - 12, val, "v", "middle")
    text(cx, y + 24, ref, "p", "middle")
    return cx - 25, cx + 25


def res_v(x, cy, label):
    """Vertical resistor, 50 long; returns (top, bottom) y."""
    o.append(f'<rect class="bx" x="{x - 7}" y="{cy - 25}" width="14" height="50"/>')
    text(x + 14, cy + 4, label, "v")
    return cy - 25, cy + 25


def cap_v(x, cy, label, polar=False, label_left=False):
    """Vertical capacitor; plates at cy +/- 4; returns (top, bottom) y = cy -/+ 15."""
    if polar:
        o.append(f'<path class="w" d="M{x - 12} {cy - 4} H{x + 12} M{x - 12} {cy + 7} Q{x} {cy + 1} {x + 12} {cy + 7}"/>')
        text(x + 16, cy - 8, "+", "p")
    else:
        o.append(f'<path class="w" d="M{x - 12} {cy - 4} H{x + 12} M{x - 12} {cy + 4} H{x + 12}"/>')
    wire((x, cy - 15), (x, cy - 4))
    wire((x, cy + (4 if not polar else 3)), (x, cy + 15))
    if label_left:
        text(x - 16, cy + 4, label, "v", "end")
    else:
        text(x + 16, cy + 4, label, "v")
    return cy - 15, cy + 15


def cap_h(cx, y, val, ref):
    o.append(f'<path class="w" d="M{cx - 4} {y - 12} V{y + 12} M{cx + 4} {y - 12} V{y + 12}"/>')
    wire((cx - 15, y), (cx - 4, y))
    wire((cx + 4, y), (cx + 15, y))
    text(cx, y - 16, val, "v", "middle")
    text(cx, y + 28, ref, "p", "middle")
    return cx - 15, cx + 15


def inductor_h(x0, y, label):
    d = f"M{x0} {y}" + "".join(f" a8 8 0 0 1 16 0" for _ in range(4))
    o.append(f'<path class="w" d="{d}"/>')
    text(x0 + 32, y - 14, label, "v", "middle")
    return x0, x0 + 64


def diode_up(x, y_top, y_bot, label):
    """Diode with the cathode at the top (flyback across a fan)."""
    mid = (y_top + y_bot) / 2
    o.append(f'<polygon class="sld" points="{x - 8},{mid + 6} {x + 8},{mid + 6} {x},{mid - 6}"/>')
    o.append(f'<path class="w" d="M{x - 8} {mid - 6} H{x + 8}"/>')
    wire((x, y_top), (x, mid - 6))
    wire((x, mid + 6), (x, y_bot))
    text(x + 14, mid + 4, label, "v")


def nmos(x, y, label):
    """N-MOSFET (gate at x, y+30). Returns gate, drain, source points."""
    o.append(f'<use href="#nmos" x="{x}" y="{y}"/>')
    text(x + 56, y + 34, label, "r")
    return (x, y + 30), (x + 46, y), (x + 46, y + 60)


def box(x, y, w, h, title, sub=None, ref=None, dashed=False):
    o.append(f'<rect class="{"dsh" if dashed else "bx"}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    if ref:
        text(x, y - 10, ref, "p")
        text(x + 8 + 7 * len(ref), y - 10, title, "r")
    else:
        text(x, y - 10, title, "r")
    if sub:
        text(x + w / 2, y + h - 10, sub, "p", "middle")


def pin_l(x, y, name):
    text(x + 10, y + 4, name, "p")


def pin_r(x, y, name):
    text(x - 10, y + 4, name, "p", "end")


def conn(x, y, ref, title, pins, note=None, w=110):
    """Connector box; pins = list of (label, y). Pins on the left edge at x."""
    top = min(py for _, py in pins) - 22
    bot = max(py for _, py in pins) + 22
    box(x, top, w, bot - top, title, ref=ref)
    for lab, py in pins:
        text(x + 14, py + 4, lab, "r")
    if note:
        for i, line in enumerate(note):
            text(x + w + 14, top + 20 + i * 18, line, "v")


def sw_v(x, yt, label):
    """Push button between (x, yt) and (x, yt + 50); label to the right. Returns the bottom y."""
    wire((x, yt), (x, yt + 12))
    o.append(f'<circle class="w" cx="{x}" cy="{yt + 15}" r="3" style="fill:none"/>')
    o.append(f'<circle class="w" cx="{x}" cy="{yt + 35}" r="3" style="fill:none"/>')
    o.append(f'<path class="w" d="M{x - 12} {yt + 10} V{yt + 40} M{x - 12} {yt + 25} H{x - 20}"/>')
    wire((x, yt + 38), (x, yt + 50))
    text(x + 10, yt + 29, label, "v")
    return yt + 50


def pnp(x, y, label):
    """PNP with the base lead to the right at (x + 30, y); emitter top (x - 22, y - 24), collector bottom (x - 22, y + 24)."""
    o.append(f'<path class="w" d="M{x} {y - 16} V{y + 16} M{x} {y} H{x + 30} M{x} {y - 7} L{x - 22} {y - 22} V{y - 30} '
             f'M{x} {y + 7} L{x - 22} {y + 22} V{y + 30}"/>')
    o.append(f'<path class="sld" d="M{x + 1} {y - 8} l-9 -1 l4 -7 z"/>')
    text(x - 30, y + 14, label, "v", "end")
    return (x + 30, y), (x - 22, y - 30), (x - 22, y + 30)


def conn_r(xr, ref, title, pins, w=110):
    """Connector whose pins face right: box ends at xr; pins = [(label, y)]."""
    top = min(py for _, py in pins) - 22
    bot = max(py for _, py in pins) + 22
    box(xr - w, top, w, bot - top, title, ref=ref)
    for lab, py in pins:
        text(xr - 14, py + 4, lab, "r", "end")


def section(y, title):
    text(60, y, title, "r")
    o.append(f'<path class="dsh" d="M60 {y + 10} H{W - 60}" style="stroke:#bbbbbb"/>')


# ================================================================== header
text(60, 36, "Dryer controller board  ·  ESP32-C3 super mini  ·  for pcb layout and jlcpcb assembly")
text(60, 56, "one board for both dryers. parts in dashed boxes marked 2-roll build only are left off the 1-roll build.", "v")

# ================================================================== 1. power in and 5 v buck
section(84, "12 v in and 5 v buck")
conn(60, 0, "tb1", "screw terminal, 5.08 mm", [("1 +12 v", 150), ("2 gnd", 180)], w=110)
wire((170, 150), (500, 150))
wire((170, 180), (196, 180), (196, 196)); gnd(196, 196)
for x, lab, polar in ((250, "c1 100 µF 25 v", True), (330, "c2 100 nF", False), (410, "c3 10 µF 25 v", False)):
    dot(x, 150)
    t, b = cap_v(x, 195, "", polar)
    wire((x, 150), (x, t)); gnd(x, b)
    text(x, 250, lab, "v", "middle")
text(60, 272, "12 v feed: xt60 lead with an inline 15 a fuse", "p")
box(520, 125, 130, 105, "ap63205wu-7  5 v buck", ref="u2")
pin_l(520, 150, "vin"); pin_l(520, 180, "en")
pin_r(650, 150, "sw"); pin_r(650, 180, "bst"); pin_r(650, 210, "fb")
text(585, 222, "gnd", "p", "middle")
wire((585, 230), (585, 246)); gnd(585, 246)
wire((470, 150), (470, 180), (520, 180)); dot(470, 150)
wire((500, 150), (520, 150))
wire((650, 150), (730, 150)); dot(730, 150)
l0, l1 = inductor_h(750, 150, "l1 4.7 µH")
wire((730, 150), (750, 150))
wire((650, 180), (690, 180))
cap_h(705, 180, "c4 100 nF", "")
wire((720, 180), (730, 180), (730, 150))
wire((l1, 150), (1000, 150)); dot(840, 150)
wire((650, 210), (840, 210), (840, 150))
for x, lab in ((900, "c5 22 µF"), (960, "c6 22 µF")):
    dot(x, 150)
    t, b = cap_v(x, 195, "", False)
    wire((x, 150), (x, t)); gnd(x, b)
    text(x, 250, lab, "v", "middle")
net(1000, 1040, 150, "+5v", side="right")

# ================================================================== 2. controller + output stages
section(300, "controller and output stages")
ex, ey, ew, eh = 110, 340, 190, 940
box(ex, ey, ew, eh, "esp32-c3-wroom-02-n4", ref="u1")
for y, name in ((370, "3v3"), (400, "en"), (430, "gnd")):
    pin_l(ex, y, name)
net(70, ex, 370, "+3v3")
net(70, ex, 400, "en")
wire((ex, 430), (90, 430), (90, 446)); gnd(90, 446)
for y, gp, lab in ((1090, "gpio7", "scl"), (1120, "gpio8", "sda"), (1150, "gpio10", "step_a"), (1180, "gpio20", "step_b"), (1210, "gpio9", "boot")):
    pin_l(ex, y, gp)
    net(70, ex, y, lab)
RP = {"gpio4": 480, "gpio5": 660, "gpio6": 810, "gpio2": 890, "gpio0": 1030, "gpio1": 1060, "gpio3": 1090, "gpio21": 1150,
      "gpio18": 1220, "gpio19": 1250}
for name, y in RP.items():
    pin_r(ex + ew, y, name)
X0 = ex + ew

# --- heater: gpio4 -> UCC27517 -> R7 -> Q1 -> TB2
text(420, 336, "heater switch: 12 v gate drive for the 12.5 a heater", "p")
wire((X0, 480), (420, 480)); dot(325, 480)
t, b = res_v(325, 515, "r9 10 kΩ")
wire((325, 480), (325, t)); gnd(325, b)
box(420, 450, 120, 90, "ucc27517", ref="u4")
pin_l(420, 480, "in+"); pin_l(420, 510, "in−")
pin_r(540, 480, "out")
text(480, 466, "vdd", "p", "middle"); text(480, 534, "gnd", "p", "middle")
wire((420, 510), (410, 510), (410, 524)); gnd(410, 524)
wire((480, 540), (480, 552)); gnd(480, 552)
wire((480, 450), (480, 400))
net(430, 480, 400, "+12v")
wire((480, 400), (660, 400)); dot(480, 400); dot(580, 400)
t, b = cap_v(580, 415, "c8 10 µF", False, label_left=True)
wire((580, 400), (580, t)); gnd(580, b)
t, b = cap_v(660, 415, "c9 100 nF", False)
wire((660, 400), (660, t)); gnd(660, b)
l, r = res_h(620, 480, "10 Ω", "r7")
wire((540, 480), (l, 480))
wire((r, 480), (740, 480)); dot(700, 480)
t, b = res_v(700, 510, "r8 10 kΩ")
wire((700, 480), (700, t)); gnd(700, b)
g, d, s = nmos(740, 450, "q1 aod4184a")
wire(s, (s[0], 520)); gnd(s[0], 520)
wire(d, (d[0], 410), (900, 410))
conn(900, 0, "tb2", "screw terminal → heater", [("1 +12 v", 380), ("2 heater −", 410)],
     ["ptc 12 v 150 w heater,", "via ksd301 and fuse", "(in the harness)"])
net(860, 900, 380, "+12v")


def fan_stage(gy, rg, rpd, q, d, j, title, label, note):
    l, r = res_h(400, gy, "100 Ω", rg)
    wire((X0, gy), (l, gy))
    wire((r, gy), (520, gy)); dot(470, gy)
    t, b = res_v(470, gy + 40, f"{rpd} 10 kΩ")
    wire((470, gy), (470, t)); gnd(470, b)
    g, dr, s = nmos(520, gy - 30, f"{q} ao3400a")
    wire(s, (s[0], s[1] + 10)); gnd(s[0], s[1] + 10)
    py1, py2 = gy - 90, gy - 60
    wire(dr, (dr[0], py2), (900, py2)); dot(780, py2)
    net(740, 900, py1, "+12v")
    dot(780, py1)
    diode_up(780, py1, py2, f"{d} b5819w")
    conn(900, 0, j, title, [("1 +12 v", py1), (f"2 {label} −", py2)], note)


fan_stage(660, "r10", "r11", "q2", "d1", "j3", "blower, jst xh 2-pin", "fan", ["5015 12 v blower"])
fan_stage(810, "r12", "r13", "q3", "d2", "j4", "exhaust fan, jst xh 2-pin", "fan", ["4010 12 v fan in the lid"])

# --- one-wire: gpio2 -> R1 pull-up -> J6
wire((X0, 890), (900, 890)); dot(345, 890)
t, b = res_v(345, 860, "r1 4.7 kΩ")
wire((345, 890), (345, b)); net_up(345, t, t - 10, "+3v3")
conn(900, 0, "j6", "sensor board s2, xh 3", [("1 +3v3", 830), ("2 gnd", 860), ("3 dq", 890)], ["→ s2 (ds18b20z)", "in the heater outlet"])
net(860, 900, 830, "+3v3"); net(860, 900, 860, "gnd")

# --- scale data lines (the hx711s are drawn further down)
for y, lab in ((1030, "hx_sck"), (1060, "hxa_dt"), (1090, "hxb_dt")):
    net(X0, X0 + 50, y, lab, side="right")
text(X0 + 110, 1064, "→ u7, u8 (scales)", "p")

# --- motion: gpio21 -> R4 -> "motion"
l, r = res_h(400, 1150, "1 kΩ", "r4")
wire((X0, 1150), (l, 1150))
net(r, r + 40, 1150, "motion", side="right")
text(330, 1194, "gpio21 is uart0 tx: the boot log comes out here, hence r4", "p")

# --- usb data lines
net(X0, X0 + 50, 1220, "usb_dn", side="right")
net(X0, X0 + 50, 1250, "usb_dp", side="right")

# --- reset and boot
net(700, 740, 1010, "en")
wire((740, 1010), (980, 1010)); dot(780, 1010); dot(860, 1010)
t, b = res_v(780, 970, "r16 10 kΩ")
wire((780, 1010), (780, b)); net_up(780, t, t - 8, "+3v3")
t, b = cap_v(860, 1035, "c16 1 µF")
wire((860, 1010), (860, t)); gnd(860, b)
gnd(980, sw_v(980, 1010, "sw2 reset"))
net(700, 740, 1190, "boot")
wire((740, 1190), (860, 1190)); dot(780, 1190)
t, b = res_v(780, 1150, "r17 10 kΩ")
wire((780, 1190), (780, b)); net_up(780, t, t - 8, "+3v3")
gnd(860, sw_v(860, 1190, "sw3 boot"))
text(700, 1276, "hold boot, tap reset: download mode", "p")

# ================================================================== 2b. usb and 3.3 v
y0 = 1320
section(y0, "usb (data only) and 3.3 v")
conn_r(210, "j2", "usb-c, type-c-31-m-12", [("a6/b6  d+", y0 + 70), ("a7/b7  d−", y0 + 100), ("a5  cc1", y0 + 130),
                                             ("b5  cc2", y0 + 160), ("gnd, shell", y0 + 190), ("vbus  nc", y0 + 220)], w=150)
net(210, 260, y0 + 70, "usb_dp", side="right")
net(210, 260, y0 + 100, "usb_dn", side="right")
wire((210, y0 + 130), (360, y0 + 130))
t, b = res_v(360, y0 + 165, "r18 5.1 kΩ")
wire((360, y0 + 130), (360, t)); gnd(360, b)
wire((210, y0 + 160), (440, y0 + 160))
t, b = res_v(440, y0 + 195, "r19 5.1 kΩ")
wire((440, y0 + 160), (440, t)); gnd(440, b)
wire((210, y0 + 190), (240, y0 + 190), (240, y0 + 206)); gnd(240, y0 + 206)
text(60, y0 + 270, "vbus is not connected: plug in the 12 v feed while flashing over usb", "p")
net(560, 620, y0 + 80, "+5v")
wire((620, y0 + 80), (720, y0 + 80)); dot(660, y0 + 80)
t, b = cap_v(660, y0 + 115, "c12 10 µF", label_left=True)
wire((660, y0 + 80), (660, t)); gnd(660, b)
box(720, y0 + 55, 110, 80, "ams1117-3.3", ref="u12")
pin_l(720, y0 + 80, "vi"); pin_r(830, y0 + 80, "vo")
text(775, y0 + 128, "gnd", "p", "middle")
wire((775, y0 + 135), (775, y0 + 150)); gnd(775, y0 + 150)
wire((830, y0 + 80), (960, y0 + 80)); dot(900, y0 + 80)
t, b = cap_v(900, y0 + 115, "c13 22 µF")
wire((900, y0 + 80), (900, t)); gnd(900, b)
net(960, 1000, y0 + 80, "+3v3", side="right")
t, b = cap_v(1000, y0 + 165, "")
net_up(1000, t, t - 10, "+3v3"); gnd(1000, b)
t, b = cap_v(1070, y0 + 165, "")
net_up(1070, t, t - 10, "+3v3"); gnd(1070, b)
text(1035, y0 + 226, "c14 10 µF, c15 100 nF", "v", "middle")
text(1035, y0 + 242, "at u1's 3v3 pin", "p", "middle")
text(560, y0 + 270, "u12 feeds u1, u3, the sensors and the logic of u7, u8, u10, u11 (about 0.4 a peak)", "p")

o.append('<g transform="translate(0,340)">')
# ================================================================== 3. i2c bus
section(1270, "i2c bus: sensors and display (the mcp23017 below is on the same bus)")
net(60, 100, 1370, "scl")
net(60, 100, 1410, "sda")
wire((100, 1370), (1000, 1370))
wire((100, 1410), (1000, 1410))
text(1006, 1374, "→ u3", "p"); text(1006, 1414, "→ u3", "p")
dot(150, 1370)
t, b = res_v(150, 1340, "r2 4.7 kΩ")
wire((150, 1370), (150, b)); net_up(150, t, t - 8, "+3v3")
dot(210, 1410)
t, b = res_v(210, 1450, "r3 4.7 kΩ")
wire((210, 1410), (210, t)); wire((210, b), (210, b + 8), blue=True); text(210, b + 24, "+3v3", "n", "middle")
for jx, ref, title, pins, note in ((360, "j5", "sensor board s1, xh 4", ("3 scl", "4 sda", "1 +3v3", "2 gnd"), "→ s1 in the chamber (sht40, 0x44)"),
                                   (590, "u13", "sht40-bd1b", ("2 scl", "1 sda", "3 vdd", "4 vss"), "on the board, in the bay (0x45); c38 100 nF"),
                                   (820, "j8", "sh1106 oled, xh 4", ("3 scl", "4 sda", "1 +3v3", "2 gnd"), "front panel")):
    dot(jx - 30, 1370); dot(jx - 15, 1410)
    wire((jx - 30, 1370), (jx - 30, 1480), (jx, 1480))
    wire((jx - 15, 1410), (jx - 15, 1510), (jx, 1510))
    conn(jx, 0, ref, title, list(zip(pins, (1480, 1510, 1540, 1570))), w=130)
    net(jx - 40, jx, 1540, "+3v3"); net(jx - 40, jx, 1570, "gnd")
    text(jx + 65, 1620, note, "p", "middle")
text(60, 1650, "r2, r3 are the pull-ups for the whole bus, sensor board s1 and the oled included (an oled module with its own pull-ups is fine above about 2 kΩ total)", "p")

# ================================================================== 4. mcp23017 and its outputs
section(1680, "i/o expander: filament sensors, button, buzzer, feeder enable and direction")
ux, uy, uw, uh = 380, 1760, 180, 560
box(ux, uy, uw, uh, "mcp23017-e/so", ref="u3")
text(530, uy + 18, "vdd", "p", "middle")
wire((530, uy), (530, uy - 30), (680, uy - 30)); dot(640, uy - 30)
net(680, 700, uy - 30, "+3v3", side="right")
t, b = cap_v(640, uy - 10, "c7 100 nF", False)
wire((640, uy - 30), (640, t)); gnd(640, b)
text(470, uy + uh - 26, "vss", "p", "middle")
wire((470, uy + uh), (470, uy + uh + 14)); gnd(470, uy + uh + 14)
for y, name in ((1800, "scl"), (1830, "sda")):
    pin_l(ux, y, name); net(ux - 50, ux, y, name)
pin_l(ux, 1890, "reset")
wire((ux, 1890), (260, 1890), (260, 1880))
t, b = res_v(260, 1855, "r5 10 kΩ")
net_up(260, t, t - 8, "+3v3")
for y, name in ((1950, "a0"), (1980, "a1"), (2010, "a2")):
    pin_l(ux, y, name)
    wire((ux, y), (340, y))
wire((340, 1950), (340, 2030)); dot(340, 1980); dot(340, 2010); gnd(340, 2030)
pin_l(ux, 2070, "inta"); pin_l(ux, 2100, "intb")
text(ux - 8, 2074, "nc", "p", "end"); text(ux - 8, 2104, "nc", "p", "end")
text(ux + 10, 2170, "addr 0x20", "p"); text(ux + 10, 2190, "gpa7, gpb0–7: nc", "p")
MX = ux + uw
GPA = {"gpa0": 1830, "gpa1": 1970, "gpa2": 2110, "gpa3": 2240, "gpa4": 2270, "gpa5": 2290, "gpa6": 2310}
GPA = {"gpa0": 1830, "gpa1": 1970, "gpa2": 2110, "gpa3": 2220, "gpa4": 2250, "gpa5": 2280, "gpa6": 2310}
for name, y in GPA.items():
    pin_r(MX, y, name)
wire((MX, 1830), (780, 1830))
conn(780, 0, "j13", "lane a sensor, xh 3", [("1 +3v3", 1770), ("2 gnd", 1800), ("3 s", 1830)], ["k1c runout sensor", "(2-roll only)"], w=120)
wire((MX, 1970), (780, 1970))
conn(780, 0, "j14", "lane b sensor, xh 3", [("1 +3v3", 1910), ("2 gnd", 1940), ("3 s", 1970)], ["k1c runout sensor", "(2-roll only)"], w=120)
wire((MX, 2110), (780, 2110))
conn(780, 0, "j15", "btt sfs v2, xh 4", [("1 +3v3", 2050), ("2 gnd", 2080), ("3 runout", 2110), ("4 motion", 2140)], ["after the y-merger", "(1-roll: at the exit)"], w=120)
net(720, 780, 2140, "motion")
wire((MX, 2220), (780, 2220))
conn(780, 0, "j9", "button, xh 2", [("1 btn", 2220), ("2 gnd", 2250)], ["front panel"], w=120)
for y in (1770, 1910, 2050):
    net(740, 780, y, "+3v3")
for y in (1800, 1940, 2080, 2250):
    net(740, 780, y, "gnd")
net(MX, MX + 50, 2250, "buzzer", side="right")
net(MX, MX + 50, 2280, "feed_en", side="right")
net(MX, MX + 50, 2310, "feed_dir", side="right")
text(60, 2380, "the mcp23017's internal pull-ups are switched on for gpa0–gpa3", "p")

# --- buzzer
section(2420, "buzzer")
net(100, 140, 2540, "buzzer")
l, r = res_h(190, 2540, "100 Ω", "r14")
wire((140, 2540), (l, 2540))
wire((r, 2540), (300, 2540)); dot(260, 2540)
t, b = res_v(260, 2580, "r15 10 kΩ")
wire((260, 2540), (260, t)); gnd(260, b)
g, d, s = nmos(300, 2510, "q4 ao3400a")
wire(s, (s[0], s[1] + 10)); gnd(s[0], s[1] + 10)
o.append(f'<rect class="bx" x="{d[0] - 10}" y="2464" width="20" height="26"/>')
o.append(f'<path class="w" d="M{d[0] + 16} 2469 q6 8 0 16 M{d[0] + 22} 2465 q9 12 0 24"/>')
text(d[0] + 40, 2474, "bz1 kxg1205c", "r"); text(d[0] + 40, 2492, "active, 5 v, 12 mm", "v")
text(d[0] - 16, 2470, "+", "p")
wire(d, (d[0], 2490))
net_up(d[0], 2464, 2452, "+5v")

o.append('</g>')

# ================================================================== 6. scales (hx711 on the board)
YS = 2990
section(YS, "scales: hx711 load-cell amplifiers on the board, load cells plug straight in")


def scale(X, Y, k, u, q, rt, rb, caps, jref, dt):
    bx, bw = X + 250, 140
    exc, vfb, vbg = f"exc_{k}", f"vfb_{k}", f"vbg_{k}"
    box(bx, Y + 40, bw, 270, "hx711", ref=u)
    for name, dy in (("vsup", 70), ("base", 100), ("avdd", 130), ("vfb", 160), ("agnd", 190), ("vbg", 220), ("ina−", 250), ("ina+", 280)):
        pin_l(bx, Y + dy, name)
    xr = bx + bw
    for name, dy in (("dvdd", 70), ("rate", 100), ("xi", 130), ("xo", 160), ("dout", 190), ("pd_sck", 220), ("inb+", 250), ("inb−", 280)):
        pin_r(xr, Y + dy, name)
    base, e, c = pnp(bx - 60, Y + 100, f"{q} s8550")
    wire(base, (bx, Y + 100))
    wire((bx, Y + 70), (X + 120, Y + 70)); dot(e[0], Y + 70); wire(e, (e[0], Y + 70))
    net(X + 80, X + 120, Y + 70, "+5v")
    wire((bx, Y + 130), (X + 120, Y + 130)); dot(c[0], Y + 130); wire(c, (c[0], Y + 130))
    net(X + 80, X + 120, Y + 130, exc)
    net(bx - 40, bx, Y + 160, vfb)
    net(bx - 40, bx, Y + 190, "gnd")
    net(bx - 40, bx, Y + 220, vbg)
    conn_r(X + 110, jref, f"load cell {k}, xh 4", [("3 a−", Y + 250), ("4 a+", Y + 280), ("1 e+", Y + 310), ("2 e−", Y + 340)])
    wire((bx, Y + 250), (X + 110, Y + 250))
    wire((bx, Y + 280), (X + 110, Y + 280))
    net(X + 110, X + 150, Y + 310, exc, side="right")
    wire((X + 110, Y + 340), (X + 130, Y + 340), (X + 130, Y + 352)); gnd(X + 130, Y + 352)
    text(X, Y + 386, "red e+, black e−, white a−, green a+", "p")
    net(xr, xr + 40, Y + 70, "+3v3", side="right")
    wire((xr, Y + 100), (xr + 20, Y + 100), (xr + 20, Y + 136)); wire((xr, Y + 130), (xr + 20, Y + 130)); dot(xr + 20, Y + 130)
    gnd(xr + 20, Y + 136)
    text(xr + 36, Y + 164, "nc", "p")
    net(xr, xr + 50, Y + 190, dt, side="right")
    net(xr, xr + 50, Y + 220, "hx_sck", side="right")
    text(xr + 8, Y + 254, "nc", "p"); text(xr + 8, Y + 284, "nc", "p")
    # decoupling and the excitation divider
    for i, (lab, ref, val, polar) in enumerate(((exc, caps[0], "10 µF", False), (exc, caps[1], "100 nF", False), (vbg, caps[2], "100 nF", False),
                                                ("+5v", caps[3], "100 nF", False), ("+3v3", caps[4], "100 nF", False))):
        x = X + 40 + i * 72
        t, b = cap_v(x, Y + 460, "")
        net_up(x, t, t - 12, lab); gnd(x, b)
        text(x, b + 36, ref, "p", "middle"); text(x, b + 50, val, "p", "middle")
    x = X + 430
    t, b = res_v(x, Y + 450, f"{rt} 20 kΩ")
    net_up(x, t, t - 12, exc)
    wire((x, b), (x, Y + 510)); dot(x, Y + 490)
    net(x, x + 40, Y + 490, vfb, side="right")
    t2, b2 = res_v(x, Y + 535, f"{rb} 8.2 kΩ")
    gnd(x, b2)
    text(X, Y + 600, "excitation avdd = 1.25 v × (20 k + 8.2 k) / 8.2 k = 4.3 v", "p")


scale(40, YS + 10, "a", "u7", "q5", "r20", "r21", ("c17", "c18", "c19", "c20", "c21"), "j11", "hxa_dt")
o.append(f'<rect class="dsh" x="590" y="{YS + 24}" width="530" height="600" style="stroke:#999999"/>')
text(W - 56, YS + 44, "2-roll build only", "p", "end")
scale(600, YS + 10, "b", "u8", "q6", "r22", "r23", ("c22", "c23", "c24", "c25", "c26"), "j12", "hxb_dt")

# ================================================================== 7. feeder drivers (2-roll)
FS = YS + 660
section(FS, "feeder drivers: tmc2209 on the board, standalone, 1/8 step")
o.append(f'<rect class="dsh" x="40" y="{FS + 24}" width="{W - 80}" height="760" style="stroke:#999999"/>')
text(W - 56, FS + 44, "2-roll build only", "p", "end")


def driver(X, Y, u, step, jref, k, m, cb, cs, rs, pullup=False):
    bx, bw = X + 150, 150
    xr = bx + bw
    box(bx, Y + 40, bw, 410, "tmc2209-la-t", ref=u)
    L = [("en", "feed_en"), ("step", step), ("dir", "feed_dir"), ("ms1", "gnd"), ("ms2", "gnd"), ("pdn/uart", "gnd"), ("spread", "gnd"),
         ("clk", "gnd"), ("stdby", "gnd"), ("vcc_io", "+3v3"), ("diag", None), ("index", None), ("gnd, pad", "GND")]
    for i, (name, lab) in enumerate(L):
        y = Y + 70 + 30 * i
        pin_l(bx, y, name)
        if lab is None:
            text(bx - 8, y + 4, "nc", "p", "end")
        elif lab == "GND":
            wire((bx, y), (bx - 20, y), (bx - 20, y + 12)); gnd(bx - 20, y + 12)
        elif name == "en" and pullup:
            wire((bx, y), (bx - 40, y)); dot(bx - 40, y)
            t, b = res_v(bx - 40, y - 35, "")
            o.pop()
            text(bx - 54, y - 30, "r6 10 kΩ", "v", "end")
            wire((bx - 40, y), (bx - 40, b)); net_up(bx - 40, t, t - 8, "+3v3")
            net(bx - 80, bx - 40, y, lab)
        else:
            net(bx - 40, bx, y, lab)
    Rn = ["vs", "vs", "vcp", "cpo", "cpi", "5vout", "vref", "oa1", "oa2", "ob1", "ob2", "bra", "brb"]
    for i, name in enumerate(Rn):
        pin_r(xr, Y + 70 + 30 * i, name)
    wire((xr, Y + 70), (xr + 20, Y + 70), (xr + 20, Y + 100), (xr, Y + 100))
    net(xr + 20, xr + 60, Y + 70, "+12v", side="right")
    wire((xr, Y + 130), (xr + 25, Y + 130))
    cap_h(xr + 40, Y + 130, f"{cs[2]} 100 nF", "")
    net(xr + 55, xr + 85, Y + 130, "+12v", side="right")
    wire((xr, Y + 160), (xr + 40, Y + 160)); wire((xr, Y + 190), (xr + 40, Y + 190))
    cap_v(xr + 40, Y + 175, f"{cs[1]} 22 nF")
    net(xr, xr + 40, Y + 220, f"{m}_5v", side="right")
    net(xr, xr + 40, Y + 250, f"{m}_vref", side="right")
    for i, nm in enumerate(("1 1a", "2 1b", "3 2a", "4 2b")):
        wire((xr, Y + 280 + 30 * i), (xr + 110, Y + 280 + 30 * i))
    conn(xr + 110, 0, jref, f"motor {k}", [("1 1a", Y + 280), ("2 1b", Y + 310), ("3 2a", Y + 340), ("4 2b", Y + 370)], w=80)
    text(xr + 125, Y + 424, "k1c extruder", "p"); text(xr + 125, Y + 438, "motor", "p")
    wire((xr, Y + 400), (xr + 110, Y + 400))
    t, b = res_v(xr + 110, Y + 470, f"{rs[2]} 0.11 Ω")
    wire((xr + 110, Y + 400), (xr + 110, t)); gnd(xr + 110, b)
    wire((xr, Y + 430), (xr + 30, Y + 430))
    t, b = res_v(xr + 30, Y + 470, f"{rs[3]} 0.11 Ω")
    wire((xr + 30, Y + 430), (xr + 30, t)); gnd(xr + 30, b)
    # decoupling and the current-setting divider
    for i, (lab, ref, val, polar) in enumerate((("+12v", cb, "100 µF", True), ("+12v", cs[0], "100 nF", False),
                                                ("+3v3", cs[4], "100 nF", False), (f"{m}_5v", cs[3], "2.2 µF", False))):
        x = X + 40 + i * 64
        t, b = cap_v(x, Y + 570, "", polar)
        net_up(x, t, t - 12, lab); gnd(x, b)
        text(x, b + 36, ref, "p", "middle"); text(x, b + 50, val, "p", "middle")
    x = X + 330
    t, b = res_v(x, Y + 580, f"{rs[0]} 39 kΩ")
    net_up(x, t, t - 12, f"{m}_5v")
    wire((x, b), (x, Y + 640)); dot(x, Y + 620)
    net(x, x + 40, Y + 620, f"{m}_vref", side="right")
    t2, b2 = res_v(x, Y + 665, f"{rs[1]} 10 kΩ")
    gnd(x, b2)


driver(40, FS + 30, "u10", "step_a", "j16", "a", "ma", "c10", ("c27", "c28", "c29", "c30", "c31"), ("r24", "r25", "r26", "r27"), pullup=True)
driver(600, FS + 30, "u11", "step_b", "j17", "b", "mb", "c11", ("c32", "c33", "c34", "c35", "c36"), ("r28", "r29", "r30", "r31"))
text(60, FS + 800, "r6 holds feed_en high: both drivers stay off at boot and while printing, so the k1c extruder pulls freely through the idle gears", "p")
text(60, FS + 818, "vref = 5 v × 10 k / 49 k = 1.0 v → about 0.72 a rms (1.0 a peak) per motor. change r24/r28 to change it.", "p")

# ================================================================== 8. sensor boards
SB = FS + 870
section(SB, "sensor boards s1, s2: break off the main board, solder the harness wires to their pads")


def sensor_board(X, Y, title, jref, pads, uref, chip, chip_pins, cref, extra):
    o.append(f'<rect class="dsh" x="{X}" y="{Y}" width="520" height="250" style="stroke:#999999"/>')
    text(X + 14, Y + 20, title, "p")
    conn_r(X + 130, jref, "wire pads", [(p_, Y + 70 + 30 * i) for i, p_ in enumerate(pads)])
    box(X + 270, Y + 50, 130, 30 * len(chip_pins) + 10, chip, ref=uref)
    for i, nm in enumerate(chip_pins):
        y = Y + 70 + 30 * i
        pin_l(X + 270, y, nm)
        wire((X + 130, y), (X + 270, y))
    dot(X + 210, Y + 70); dot(X + 210, Y + 100)
    cap_v(X + 210, Y + 85, f"{cref} 100 nF", label_left=True)
    for i, line in enumerate(extra):
        text(X + 14, Y + 206 + 18 * i, line, "p")


sensor_board(40, SB + 30, "s1: chamber air", "j18", ("1 +3v3", "2 gnd", "3 scl", "4 sda"), "u14", "sht40-ad1b",
             ("3 vdd", "4 vss", "2 scl", "1 sda"), "c37", ["address 0x44. same pin order as j5.", "solder silicone wires: the chamber reaches 70 °C"])
sensor_board(600, SB + 30, "s2: heater outlet air", "j19", ("1 +3v3", "2 gnd", "3 dq"), "u15", "ds18b20z",
             ("3 vdd", "5 gnd", "4 dq"), "c39", ["pins 1, 2, 6–8 nc. pull-up r1 is on the main board.", "rated to 125 °C; the firmware cuts the heater at 100 °C"])

# ================================================================== notes
NOTES = [
    "1. one board for both dryers, every part assembled by jlcpcb. 1-roll build: the 1-roll bom leaves off the boxes marked 2-roll build only, and j12–j14.",
    "2. the heater path tb1 → tb2 → q1 carries 12.5 a: wide copper pours, 2 oz copper, a copper area under q1's tab.",
    "3. u4 drives q1's gate at 12 v. r9 holds the driver input low until the firmware takes gpio4, so the heater stays off at boot.",
    "4. r8, r11, r13, r15 hold the mosfet gates low at boot. q2–q4 ao3400a in sot-23: pin 1 gate, 2 source, 3 drain.",
    "5. u1's antenna at the board edge with no copper under it. u13 at an edge away from u2, u12, u10, u11. s1, s2 on break-off tabs.",
    "6. u10, u11 exposed pads to gnd with thermal vias into a ground pour on the back.",
    "7. u2 values from the ap63205 datasheet, table 3: 4.7 µH, 10 µF in, 2 × 22 µF out, 100 nF bootstrap.",
    "8. crossing wires are not connected unless a dot is shown. blue labels with the same name are the same net.",
    "9. part numbers and lcsc codes: pcb/jlcpcb/bom-2-roll.csv. same nets as the kicad schematic pcb/dryer-controller.kicad_sch.",
]
o.append(f'<path class="w" d="M60 {H - 230} H{W - 60}" style="stroke:#999999"/>')
text(60, H - 206, "notes", "r")
for i, n in enumerate(NOTES):
    text(60, H - 182 + i * 20, n, "v")

STYLE = """<style>
.w{stroke:#1a1a1a;stroke-width:1.6;fill:none;stroke-linecap:round;stroke-linejoin:round}
.bx{stroke:#1a1a1a;stroke-width:1.6;fill:#ffffff}
.dsh{stroke:#1a1a1a;stroke-width:1.3;fill:none;stroke-dasharray:5 4}
.sld{fill:#1a1a1a;stroke:none}
.r{font:13px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#1a1a1a}
.v{font:12px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#555555}
.p{font:11px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#777777}
.n{font:12px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#0b5cad}
.nw{stroke:#0b5cad;stroke-width:1.6;fill:none;stroke-linecap:round}
</style>"""
DEFS = """<defs>
<g id="gnd"><path class="w" d="M0 0 V9 M-9 9 H9 M-6 14 H6 M-3 19 H3"/></g>
<g id="nmos">
<path class="w" d="M0 30 H18 M18 12 V48"/>
<path class="w" d="M26 12 V20 M26 26 V34 M26 40 V48"/>
<path class="w" d="M26 16 H46 M46 16 V0"/>
<path class="w" d="M26 44 H46 M46 44 V60"/>
<path class="w" d="M26 30 H46 M46 30 V44"/>
<polygon class="sld" points="29,30 38,26 38,34"/>
</g>
</defs>"""
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="ttl">\n'
       '<title id="ttl">Dryer controller board schematic: ESP32-C3 super mini, AP63205 buck, MCP23017, heater gate driver and MOSFETs, TMC2209 sockets</title>\n'
       + STYLE + "\n" + DEFS + f'\n<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>\n' + "\n".join(o) + "\n</svg>\n")
(ROOT / "schematic.svg").write_text(svg, encoding="utf-8")
print("wrote", ROOT / "schematic.svg")
