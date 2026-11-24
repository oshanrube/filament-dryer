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
W, H = 1160, 3340
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


def section(y, title):
    text(60, y, title, "r")
    o.append(f'<path class="dsh" d="M60 {y + 10} H{W - 60}" style="stroke:#bbbbbb"/>')


# ================================================================== header
text(60, 36, "Dryer controller board  ·  ESP32-C3 super mini  ·  for pcb layout and jlcpcb assembly")
text(60, 56, "one board for both dryers. parts in the dashed box are fitted on the 2-roll build only.", "v")

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
ex, ey, ew, eh = 110, 340, 190, 900
box(ex, ey, ew, eh, "esp32-c3 super mini", "module in sockets", ref="u1")
for y, name in ((370, "5v"), (400, "3v3"), (430, "gnd")):
    pin_l(ex, y, name)
net(70, ex, 370, "+5v")
net(70, ex, 400, "+3v3")
wire((ex, 430), (90, 430), (90, 446)); gnd(90, 446)
for y, gp, lab in ((1090, "gpio7", "scl"), (1120, "gpio8", "sda"), (1150, "gpio10", "step_a"), (1180, "gpio20", "step_b")):
    pin_l(ex, y, gp)
    net(70, ex, y, lab)
pin_l(ex, 1210, "gpio9"); text(ex - 8, 1214, "nc", "p", "end")
RP = {"gpio4": 480, "gpio5": 660, "gpio6": 810, "gpio2": 890, "gpio0": 1030, "gpio1": 1060, "gpio3": 1090, "gpio21": 1170}
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
conn(900, 0, "j6", "ds18b20, jst xh 3-pin", [("1 +3v3", 830), ("2 gnd", 860), ("3 dq", 890)], ["heater outlet probe"])
net(860, 900, 830, "+3v3"); net(860, 900, 860, "gnd")

# --- scales: gpio0 sck to both, gpio1 -> J11, gpio3 -> J12
wire((X0, 1030), (900, 1030)); dot(760, 1030)
wire((760, 1030), (760, 1190), (900, 1190))
wire((X0, 1060), (900, 1060))
wire((X0, 1090), (740, 1090), (740, 1220), (900, 1220))
conn(900, 0, "j11", "scale a, jst xh 4-pin", [("1 +3v3", 970), ("2 gnd", 1000), ("3 sck", 1030), ("4 dt", 1060)], ["hx711 board, then", "load cell lc1"])
conn(900, 0, "j12", "scale b, jst xh 4-pin", [("1 +3v3", 1130), ("2 gnd", 1160), ("3 sck", 1190), ("4 dt", 1220)], ["hx711 board, then", "load cell lc2", "(2-roll only)"])
for y in (970, 1130):
    net(860, 900, y, "+3v3")
for y in (1000, 1160):
    net(860, 900, y, "gnd")

# --- motion: gpio21 -> R4 -> "motion"
l, r = res_h(400, 1170, "1 kΩ", "r4")
wire((X0, 1170), (l, 1170))
net(r, r + 40, 1170, "motion", side="right")
text(330, 1214, "gpio21 is uart0 tx: the boot log comes out here, hence r4", "p")

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
for jx, ref, title, note in ((360, "j5", "sht40, xh 4", "in the chamber"), (590, "j7", "aht20, xh 4", "bay, optional"), (820, "j8", "sh1106 oled, xh 4", "front panel")):
    dot(jx - 30, 1370); dot(jx - 15, 1410)
    wire((jx - 30, 1370), (jx - 30, 1480), (jx, 1480))
    wire((jx - 15, 1410), (jx - 15, 1510), (jx, 1510))
    conn(jx, 0, ref, title, [("3 scl", 1480), ("4 sda", 1510), ("1 +3v3", 1540), ("2 gnd", 1570)], w=130)
    net(jx - 40, jx, 1540, "+3v3"); net(jx - 40, jx, 1570, "gnd")
    text(jx + 65, 1620, note, "p", "middle")
text(60, 1650, "r2, r3 are the only i2c pull-ups needed: if a module has its own, the total should not drop below about 2 kΩ", "p")

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

# ================================================================== 5. feeder drivers (2-roll)
section(2660, "feeder drivers: tmc2209 stepstick modules in sockets, standalone, 1/8 step")
o.append(f'<rect class="dsh" x="40" y="2680" width="{W - 80}" height="360" style="stroke:#999999"/>')
text(W - 56, 2700, "2-roll build only", "p", "end")


def driver(x, y, ref, step, jref, mlabel, cref, pullup=False):
    box(x, y, 170, 270, "tmc2209 stepstick", "fitted by us", ref=ref)
    L = [("en", 30, "feed_en"), ("ms1", 60, "gnd"), ("ms2", 90, "gnd"), ("pdn/uart", 120, "nc"), ("pdn/uart", 150, "nc"),
         ("clk", 180, "nc"), ("step", 210, step), ("dir", 240, "feed_dir")]
    for name, dy, lab in L:
        pin_l(x, y + dy, name)
        if lab == "nc":
            text(x - 8, y + dy + 4, "nc", "p", "end")
        elif name == "en" and pullup:
            wire((x, y + 30), (x - 40, y + 30)); dot(x - 40, y + 30)
            t, b = res_v(x - 40, y - 5, "")
            o.pop()
            text(x - 54, y, "r6 10 kΩ", "v", "end")
            wire((x - 40, y + 30), (x - 40, b)); net_up(x - 40, t, t - 8, "+3v3")
            net(x - 80, x - 40, y + 30, "feed_en")
        else:
            net(x - 40, x, y + dy, lab)
    R_ = [("vm", 30), ("gnd", 60), ("1a", 90), ("1b", 120), ("2a", 150), ("2b", 180), ("vio", 210), ("gnd", 240)]
    xr = x + 170
    for name, dy in R_:
        pin_r(xr, y + dy, name)
    wire((xr, y + 30), (xr + 60, y + 30)); dot(xr + 60, y + 30)
    net(xr + 60, xr + 90, y + 30, "+12v", side="right")
    t, b = cap_v(xr + 60, y + 46, "", True)
    wire((xr + 60, y + 30), (xr + 60, t)); gnd(xr + 60, b)
    text(xr + 78, y + 56, cref, "p"); text(xr + 78, y + 70, "100 µF", "p")
    wire((xr, y + 60), (xr + 22, y + 60), (xr + 22, y + 66)); gnd(xr + 22, y + 66)
    for name, dy in R_[2:6]:
        wire((xr, y + dy), (xr + 140, y + dy))
    net(xr, xr + 30, y + 210, "+3v3", side="right")
    net(xr, xr + 30, y + 240, "gnd", side="right")
    conn(xr + 140, 0, jref, f"{mlabel}, xh 4", [("1 1a", y + 90), ("2 1b", y + 120), ("3 2a", y + 150), ("4 2b", y + 180)], w=90)
    text(xr + 185, y + 230, "k1c extruder motor", "p", "middle")


driver(170, 2740, "u10", "step_a", "j16", "motor a", "c10", pullup=True)
driver(660, 2740, "u11", "step_b", "j17", "motor b", "c11")
text(60, 3070, "r6 holds feed_en high: both drivers stay off at boot and while printing, so the k1c extruder pulls freely through the idle gears", "p")

# ================================================================== notes
NOTES = [
    "1. one board for both dryers. 1-roll build: leave off u10, u11, c10, c11, j12, j13, j14, j16, j17. a 1-roll box uses this same pin map.",
    "2. the heater path tb1 → tb2 → q1 carries 12.5 a: wide copper pours, 2 oz copper, a copper area under q1's tab.",
    "3. u4 drives q1's gate at 12 v. r9 holds the driver input low until the firmware takes gpio4, so the heater stays off at boot.",
    "4. r8, r11, r13, r15 hold the mosfet gates low at boot. q2–q4 ao3400a in sot-23: pin 1 gate, 2 source, 3 drain.",
    "5. u1 and u10/u11 are modules we fit ourselves in 2.54 mm sockets. measure the super mini's header row spacing (footprint: 15.24 mm).",
    "6. tmc2209 pins 4–6 (pdn/uart, clk) differ between makers, so they're left unconnected. check your module.",
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
