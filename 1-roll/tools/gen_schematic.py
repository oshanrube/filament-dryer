#!/usr/bin/env python3
"""Generate 1-roll/schematic.svg for the single-reel filament dryer.

Connections use net labels: two pins with the same label are wired together.
Run:  python3 1-roll/tools/gen_schematic.py
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
t(30, 44, "Single-reel filament dryer: schematic", 22, weight="bold")
t(30, 68, "ESP32-C3 SuperMini · 12 V feed · K1C fans · BTT motion sensor · nets with the same label are connected · rev 2026-11-23", 12.5, fill=QUIET)

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
     left=[("5V", "+5V"), ("GND", "GND"), ("3V3", "+3V3"), ("GPIO0", "HX_SCK"), ("GPIO1", "HX_DT"),
           ("GPIO2", "ONEWIRE"), ("GPIO3", "RUNOUT"), ("GPIO4", "HEAT_G")],
     right=[("GPIO5", "BLOW_G"), ("GPIO6", "EXH_G"), ("GPIO7", "SCL"), ("GPIO8", "SDA"), ("GPIO9", "BTN"),
            ("GPIO10", "BUZ_G"), ("GPIO20", None), ("GPIO21", None)],
     pitch=30, sub="on-board 3V3 regulator")
line(944, 388, 952, 388); resistor(952, 388, "R12 1k", vertical=False); line(982, 388, 992, 388); net(992, 388, "MOTION")
# pull-ups near MCU
resistor(680, 464, "R10 4.7k")
line(680, 456, 680, 464); net(680, 456, "+3V3", "left")
line(680, 494, 680, 506); net(680, 506, "ONEWIRE", "left")
t(950, 362, "free", 10.5, fill=QUIET)
t(880, 470, "I2C pull-ups: keep one", 10.5, fill=QUIET)
t(880, 486, "4.7 kΩ pair (a module's", 10.5, fill=QUIET)
t(880, 502, "own); remove the extras", 10.5, fill=QUIET)

# ---------------------------------------------------------------- I2C devices
section(1100, 90, 560, 440, "3  I2C bus")
chip(1150, 150, 140, "U4", "SHT40", left=[("VCC", "+3V3"), ("GND", "GND"), ("SCL", "SCL"), ("SDA", "SDA")], sub="chamber, 0x44")
chip(1150, 330, 140, "U5", "AHT20", left=[("VCC", "+3V3"), ("GND", "GND"), ("SCL", "SCL"), ("SDA", "SDA")], sub="bay, 0x38, optional")
chip(1420, 150, 130, "U6", "SH1106 OLED", left=[("VCC", "+3V3"), ("GND", "GND")], right=[("SCL", "SCL"), ("SDA", "SDA")], sub="0x3C, optional")

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
section(560, 550, 520, 470, "5  Weighing and outlet temperature")
for i, (ref, dt, cell) in enumerate([("U7", "HX_DT", "LC1 reel")]):
    yy = 610 + i * 250
    chip(680, yy, 120, ref, "HX711", left=[("VCC", "+3V3"), ("GND", "GND"), ("SCK", "HX_SCK"), ("DT", dt)],
         right=[("E+", None), ("E-", None), ("A-", None), ("A+", None)], sub="red board")
    for j, c in enumerate(["red", "black", "white", "green"]):
        py = yy + 28 + j * 22
        line(834, py, 880, py)
        t(884, py + 4, c, 10.5, fill=QUIET)
    box2(940, yy + 20, 110, 70, cell, "YZC-131 5 kg")
chip(680, 860, 150, "U9", "DS18B20", left=[("VDD", "+3V3"), ("GND", "GND"), ("DQ", "ONEWIRE")], sub="heater outlet probe")

# ---------------------------------------------------------------- filament sensor + button
section(1100, 550, 560, 470, "6  Filament sensor and button")
chip(1300, 620, 140, "U13", "BTT SFS V2", left=[("VCC", "+3V3"), ("GND", "GND"), ("RUNOUT", "RUNOUT"), ("MOTION", "MOTION")], sub="at the filament exit")
chip(1300, 830, 140, "SW1", "Push button", left=[("1", "BTN"), ("2", "GND")], sub="panel, momentary")
t(1130, 960, "RUNOUT and BTN use the ESP32's internal pull-ups.", 10.5, fill=QUIET)
t(1130, 976, "BTN shares GPIO9 with BOOT: holding it at power-on", 10.5, fill=QUIET)
t(1130, 992, "enters flashing mode.", 10.5, fill=QUIET)

svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}' {FONT}>"
       + "".join(out) + "</svg>\n")
dest = Path(__file__).resolve().parent.parent / "schematic.svg"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(svg)
print("wrote", dest)
