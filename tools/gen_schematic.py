#!/usr/bin/env python3
"""Generate docs/schematic.svg for the two-reel filament dryer.

Connections use net labels: two pins with the same label are wired together.
Run:  python3 tools/gen_schematic.py
"""
from pathlib import Path

W, H = 1680, 1300
INK, QUIET, LINE, ACCENT, PWR, HOT = "#1f2328", "#59636e", "#3d444d", "#0969da", "#bf3989", "#bc4c00"
FONT = "font-family='ui-monospace,SFMono-Regular,Menlo,Consolas,monospace'"
out: list[str] = []


def t(x, y, s, size=12, anchor="start", fill=INK, weight="normal"):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out.append(f"<text x='{x}' y='{y}' font-size='{size}' text-anchor='{anchor}' fill='{fill}' font-weight='{weight}'>{s}</text>")


def line(x1, y1, x2, y2, color=LINE, w=1.4):
    out.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color}' stroke-width='{w}'/>")


def dot(x, y):
    out.append(f"<circle cx='{x}' cy='{y}' r='3' fill='{LINE}'/>")


def net(x, y, name, side="right"):
    """Net label flag; side = where the flag points away from the wire end."""
    color = PWR if name.startswith(("+", "GND")) else ACCENT
    w = 8 + 7.3 * len(name)
    if side == "right":
        out.append(f"<path d='M{x} {y}l8 -9h{w}v18h-{w}z' fill='white' stroke='{color}' stroke-width='1.2'/>")
        t(x + 12, y + 4, name, 11, fill=color)
    else:
        out.append(f"<path d='M{x} {y}l-8 -9h-{w}v18h{w}z' fill='white' stroke='{color}' stroke-width='1.2'/>")
        t(x - 12, y + 4, name, 11, "end", fill=color)


def chip(x, y, w, ref, title, left=(), right=(), pitch=22, sub=None):
    """Rectangle with pins. left/right: lists of (pin_name, net or None)."""
    n = max(len(left), len(right))
    h = 36 + n * pitch + (14 if sub else 0)
    out.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='6' fill='#f6f8fa' stroke='{INK}' stroke-width='1.6'/>")
    t(x + w / 2, y - 22, ref, 12, "middle", QUIET)
    t(x + w / 2, y - 8, title, 13, "middle", INK, "bold")
    if sub:
        t(x + w / 2, y + h - 10, sub, 10.5, "middle", QUIET)
    for i, (pin, nt) in enumerate(left):
        py = y + 28 + i * pitch
        line(x - 34, py, x, py)
        t(x + 6, py + 4, pin, 11)
        if nt:
            net(x - 34, py, nt, "left")
    for i, (pin, nt) in enumerate(right):
        py = y + 28 + i * pitch
        line(x + w, py, x + w + 34, py)
        t(x + w - 6, py + 4, pin, 11, "end")
        if nt:
            net(x + w + 34, py, nt, "right")
    return h


def resistor(x, y, label, vertical=True):
    if vertical:
        out.append(f"<rect x='{x - 6}' y='{y}' width='12' height='30' fill='white' stroke='{LINE}' stroke-width='1.4'/>")
        t(x + 10, y + 19, label, 10.5, fill=QUIET)
    else:
        out.append(f"<rect x='{x}' y='{y - 6}' width='30' height='12' fill='white' stroke='{LINE}' stroke-width='1.4'/>")
        t(x + 15, y - 10, label, 10.5, "middle", QUIET)


def nmos(x, y, ref, part):
    """Low-side N-MOSFET; drain top (x, y-30), source bottom (x, y+30), gate left (x-34, y)."""
    line(x, y - 30, x, y - 12)
    line(x, y + 12, x, y + 30)
    line(x - 6, y - 14, x - 6, y + 14, w=2)
    line(x - 12, y - 10, x - 12, y + 10, w=2)
    line(x - 6, y - 12, x, y - 12)
    line(x - 6, y + 12, x, y + 12)
    line(x - 6, y, x, y)
    line(x - 34, y, x - 12, y)
    out.append(f"<path d='M{x - 6} {y}l6 -4v8z' fill='{LINE}'/>")
    t(x + 8, y - 2, ref, 11, fill=INK, weight="bold")
    t(x + 8, y + 12, part, 10.5, fill=QUIET)


def gnd(x, y):
    line(x, y, x, y + 8)
    line(x - 9, y + 8, x + 9, y + 8, w=1.8)
    line(x - 5, y + 12, x + 5, y + 12, w=1.6)
    line(x - 2, y + 16, x + 2, y + 16, w=1.4)


def box2(x, y, w, h, title, sub=None, color=INK):
    out.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='4' fill='white' stroke='{color}' stroke-width='1.4'/>")
    t(x + w / 2, y + h / 2 + (0 if sub else 4), title, 11.5, "middle", color, "bold")
    if sub:
        t(x + w / 2, y + h / 2 + 14, sub, 10, "middle", QUIET)


def section(x, y, w, h, title):
    out.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='10' fill='none' stroke='#d0d7de' stroke-width='1.2' stroke-dasharray='6 4'/>")
    t(x + 14, y + 22, title, 13, fill=QUIET, weight="bold")


# ---------------------------------------------------------------- frame
out.append(f"<rect width='{W}' height='{H}' fill='white'/>")
t(30, 44, "Two-reel filament dryer: schematic", 22, weight="bold")
t(30, 68, "ESP32-C3 SuperMini + MCP23017 · 12 V feed · K1C fans, feeders and runout sensors · nets with the same label are connected · rev 2026-11-23", 12.5, fill=QUIET)

# ---------------------------------------------------------------- power
section(20, 90, 520, 310, "1  Power in")
# XT60 -> F1 -> +12V
box2(50, 150, 70, 60, "J1", "XT60")
t(85, 230, "12 V feed", 10.5, "middle", QUIET)
line(120, 165, 170, 165)
out.append(f"<rect x='170' y='157' width='44' height='16' rx='3' fill='white' stroke='{LINE}' stroke-width='1.4'/>")
t(192, 150, "F1 15 A", 10.5, "middle", QUIET)
line(214, 165, 262, 165)
net(262, 165, "+12V")
line(120, 195, 150, 195)
gnd(150, 195)
# buck
chip(340, 166, 150, "U12", "XL6009 boost", left=[("IN+", "+12V"), ("IN-", "GND")], right=[("OUT+", "+24V"), ("OUT-", "GND")], sub="24 V for the K1C fans")
chip(340, 300, 150, "U2", "Mini560 buck", left=[("IN+", "+12V"), ("IN-", "GND")], right=[("OUT+", "+5V"), ("OUT-", "GND")], sub="5 V out, 7-20 V in")
t(50, 256, "Shared server PSU feeds every box;", 10.5, fill=QUIET)
t(50, 272, "a 15 A fuse per box also sits at", 10.5, fill=QUIET)
t(50, 288, "the supply's fuse block.", 10.5, fill=QUIET)

# ---------------------------------------------------------------- MCU
section(560, 90, 520, 440, "2  Controller")
chip(740, 150, 170, "U1", "ESP32-C3 SuperMini",
     left=[("5V", "+5V"), ("GND", "GND"), ("3V3", "+3V3"), ("GPIO0", "HX_SCK"), ("GPIO1", "HXA_DT"),
           ("GPIO2", "ONEWIRE"), ("GPIO3", "HXB_DT"), ("GPIO4", "HEAT_G")],
     right=[("GPIO5", "BLOW_G"), ("GPIO6", "EXH_G"), ("GPIO7", "SCL"), ("GPIO8", "SDA"), ("GPIO9", "TACH"),
            ("GPIO10", "STEP_A"), ("GPIO20", "STEP_B"), ("GPIO21", None)],
     pitch=30, sub="on-board 3V3 regulator")
t(950, 392, "spare", 10.5, fill=QUIET)
# pull-ups near MCU
resistor(680, 464, "R10 4.7k")
line(680, 456, 680, 464); net(680, 456, "+3V3", "left")
line(680, 494, 680, 506); net(680, 506, "ONEWIRE", "left")
resistor(800, 464, "R11 10k")
line(800, 456, 800, 464); net(800, 456, "+3V3", "left")
line(800, 494, 800, 506); net(800, 506, "TACH", "left")
t(880, 470, "I2C pull-ups: keep one", 10.5, fill=QUIET)
t(880, 486, "4.7 kΩ pair (a module's", 10.5, fill=QUIET)
t(880, 502, "own); remove the extras", 10.5, fill=QUIET)

# ---------------------------------------------------------------- I2C devices
section(1100, 90, 560, 440, "3  I2C bus and I/O expander")
chip(1150, 150, 140, "U4", "SHT40", left=[("VCC", "+3V3"), ("GND", "GND"), ("SCL", "SCL"), ("SDA", "SDA")], sub="chamber, 0x44")
chip(1150, 330, 140, "U5", "AHT20", left=[("VCC", "+3V3"), ("GND", "GND"), ("SCL", "SCL"), ("SDA", "SDA")], sub="bay, 0x38, optional")
chip(1420, 420, 130, "U6", "SH1106 OLED", left=[("VCC", "+3V3"), ("GND", "GND")], right=[("SCL", "SCL"), ("SDA", "SDA")], sub="0x3C, optional")
chip(1420, 150, 130, "U3", "MCP23017",
     left=[("VDD", "+3V3"), ("VSS", "GND"), ("SCL", "SCL"), ("SDA", "SDA"), ("RESET", "+3V3"), ("A0-A2", "GND")],
     right=[("GPA0", "LANE_A"), ("GPA1", "LANE_B"), ("GPA2", "MERGE"), ("GPA3", "BTN"), ("GPA4", "BUZ_G"),
            ("GPA5", "FEED_EN"), ("GPA6", "FEED_DIR")], sub="0x20")

# ---------------------------------------------------------------- heater + fans
section(20, 410, 520, 860, "4  Heater, fans, buzzer (low-side switches)")
# heater chain: +12V -> KSD301 -> TF1 -> PTC -> Q1
out.append("<g transform='translate(0,26)'>")
x0 = 120
net(x0, 450, "+12V", "left"); line(x0, 450, x0 + 40, 450)
box2(x0 + 40, 436, 92, 28, "TH1 KSD301", None, HOT); t(x0 + 86, 480, "85 °C NC, 16 A", 10, "middle", QUIET)
line(x0 + 132, 450, x0 + 170, 450)
box2(x0 + 170, 436, 92, 28, "TF1 92 °C", None, HOT); t(x0 + 216, 480, "one-shot, 15 A", 10, "middle", QUIET)
line(x0 + 262, 450, x0 + 300, 450)
line(x0 + 300, 450, x0 + 300, 500)
out.append(f"<rect x='{x0 + 280}' y='500' width='40' height='60' rx='3' fill='#fff4e5' stroke='{HOT}' stroke-width='1.6'/>")
out.append(f"<path d='M{x0 + 286} 512h28M{x0 + 286} 524h28M{x0 + 286} 536h28M{x0 + 286} 548h28' stroke='{HOT}' stroke-width='1.2'/>")
t(x0 + 270, 528, "HT1 PTC heater", 11, "end", INK, "bold"); t(x0 + 270, 543, "12 V 150 W, 12.5 A", 10.5, "end", QUIET)
line(x0 + 300, 560, x0 + 300, 590)
nmos(x0 + 300, 620, "Q1", "IRLB8721")
gnd(x0 + 300, 650)
# gate network
line(x0 + 200, 620, x0 + 266, 620)
resistor(x0 + 214, 620, "R1 100", vertical=False)
net(x0 + 200, 620, "HEAT_G", "left")
dot(x0 + 256, 620); line(x0 + 256, 620, x0 + 256, 640); resistor(x0 + 256, 640, "")
t(x0 + 222, 659, "R2 10k", 10.5, "end", QUIET); line(x0 + 256, 670, x0 + 256, 676); gnd(x0 + 256, 676)
t(40, 715, "Heater, thermostat and fuse wiring: 14 AWG silicone.", 10.5, fill=QUIET)
t(40, 731, "TH1 and TF1 sit in the chamber air near the lid.", 10.5, fill=QUIET)
out.append("</g>")


def fan_stage(y, ref, label, sub, gate_net, qref, rref, top_net="+12V"):
    xf = 360
    net(xf, y, top_net, "left")
    line(xf, y, xf, y + 10)
    box2(xf - 45, y + 10, 90, 34, ref, label)
    t(xf + 52, y + 32, sub, 10.5, fill=QUIET)
    line(xf, y + 44, xf, y + 62)
    nmos(xf, y + 92, qref, "AO3400")
    gnd(xf, y + 122)
    line(xf - 100, y + 92, xf - 34, y + 92)
    resistor(xf - 88, y + 92, f"{rref} 100", vertical=False)
    net(xf - 100, y + 92, gate_net, "left")
    dot(xf - 44, y + 92); line(xf - 44, y + 92, xf - 44, y + 104); resistor(xf - 44, y + 104, "10k"); line(xf - 44, y + 134, xf - 44, y + 138); gnd(xf - 44, y + 138)


fan_stage(775, "M1 blower", "K1C 4020 24V", "", "BLOW_G", "Q2", "R3", top_net="+24V")
fan_stage(940, "M2 exhaust", "K1C 3010 24V", "", "EXH_G", "Q3", "R5", top_net="+24V")
fan_stage(1105, "BZ1 buzzer", "active 5 V", "", "BUZ_G", "Q4", "R7", top_net="+5V")

# ---------------------------------------------------------------- scale + temp
section(560, 550, 520, 720, "5  Weighing and outlet temperature")
for i, (ref, dt, cell) in enumerate([("U7", "HXA_DT", "LC1 reel A"), ("U8", "HXB_DT", "LC2 reel B")]):
    yy = 610 + i * 250
    chip(680, yy, 120, ref, "HX711", left=[("VCC", "+3V3"), ("GND", "GND"), ("SCK", "HX_SCK"), ("DT", dt)],
         right=[("E+", None), ("E-", None), ("A-", None), ("A+", None)], sub="red board")
    for j, c in enumerate(["red", "black", "white", "green"]):
        py = yy + 28 + j * 22
        line(834, py, 880, py)
        t(884, py + 4, c, 10.5, fill=QUIET)
    box2(940, yy + 20, 110, 70, cell, "YZC-131 5 kg")
chip(680, 1130, 150, "U9", "DS18B20", left=[("VDD", "+3V3"), ("GND", "GND"), ("DQ", "ONEWIRE")], sub="heater outlet probe")

# ---------------------------------------------------------------- feeders
section(1100, 550, 560, 720, "6  Feeders and filament sensors (feeder pod)")
for i, (ref, step, mot) in enumerate([("U10", "STEP_A", "M3 feeder A"), ("U11", "STEP_B", "M4 feeder B")]):
    yy = 610 + i * 280
    chip(1230, yy, 160, ref, "TMC2209",
         left=[("VM", "+12V"), ("GND", "GND"), ("VIO", "+3V3"), ("STEP", step), ("DIR", "FEED_DIR"), ("EN", "FEED_EN"), ("MS1 MS2", "GND")],
         right=[("A1", None), ("A2", None), ("B1", None), ("B2", None)], sub="standalone, 1/8 step")
    for j in range(4):
        line(1424, yy + 28 + j * 22, 1470, yy + 28 + j * 22)
    box2(1470, yy + 30, 130, 60, mot, "K1C extruder motor")
    out.append(f"<rect x='1170' y='{yy + 216}' width='14' height='26' fill='white' stroke='{LINE}' stroke-width='1.4'/>")
    line(1166, yy + 216, 1188, yy + 216, w=2)
    t(1194, yy + 234, "C 100 µF 25 V across VM-GND, close to the driver", 10.5, fill=QUIET)
# EN pull-up and notes
resistor(1560, 1180, "R20 10k")
line(1560, 1172, 1560, 1180); net(1560, 1172, "+3V3", "left")
line(1560, 1210, 1560, 1222); net(1560, 1222, "FEED_EN", "left")
t(1640, 1250, "keeps both drivers off at boot", 10.5, "end", QUIET)
t(1130, 1172, "S1-S3: K1C runout sensors (3-pin switch).", 10.5, fill=QUIET)
t(1130, 1188, "Signal to LANE_A, LANE_B, MERGE; G to GND.", 10.5, fill=QUIET)
t(1130, 1204, "SW1 from BTN to GND. Pull-ups on the MCP.", 10.5, fill=QUIET)
t(1130, 1220, "Feeders: K1C extrusion kits, driver ~0.8 A.", 10.5, fill=QUIET)

svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}' {FONT}>"
       + "".join(out) + "</svg>\n")
dest = Path(__file__).resolve().parent.parent / "docs" / "schematic.svg"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(svg)
print("wrote", dest)
