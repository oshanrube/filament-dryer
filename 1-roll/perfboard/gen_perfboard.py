#!/usr/bin/env python3
"""Perfboard (dot board) version of the 1-roll controller, from parts in stock at Tronic.lk.

Same pin map as the 1-roll PCB, so one firmware runs on both. Writes, next to this file:
  schematic.svg   every wire, module level
  layout.svg      top view of a 120 x 80 mm FR4 dot board: where each module sits, terminals on the edges

Run from the repo root:  python3 1-roll/perfboard/gen_perfboard.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

STYLE = """<style>
.w{fill:none;stroke:#111;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.hv{fill:none;stroke:#c62828;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
.nw{fill:none;stroke:#1565c0;stroke-width:1.6}
.bx{fill:#fff;stroke:#111;stroke-width:1.6}
.mod{fill:#f4f8ff;stroke:#1565c0;stroke-width:1.6}
.dsh{fill:none;stroke:#999;stroke-width:1.2;stroke-dasharray:6 5}
.sld{fill:#111}
text{font-family:Inter,Arial,sans-serif}
.r{font-size:14px;fill:#111}
.v{font-size:12px;fill:#444}
.p{font-size:11px;fill:#666}
.n{font-size:12px;fill:#1565c0}
.t{font-size:16px;fill:#111;font-weight:600}
</style>"""
DEFS = """<defs>
<g id="gnd"><path class="w" d="M0 0 V9 M-9 9 H9 M-6 14 H6 M-3 19 H3"/></g>
<g id="nmos">
<path class="w" d="M0 30 H18 M18 12 V48"/>
<path class="w" d="M26 12 V20 M26 26 V34 M26 40 V48"/>
<path class="w" d="M26 16 H46 V0 M26 44 H46 V60 M26 30 H46 V44"/>
<path class="sld" d="M27 30 l8 -4 v8 z"/>
</g>
<g id="npn">
<path class="w" d="M0 30 H18 M18 14 V46 M18 24 L40 8 V0 M18 36 L40 52 V60"/>
<path class="sld" d="M40 52 l-9 -2 l5 -6 z"/>
</g>
</defs>"""


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.o = w, h, []

    def esc(self, s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def wire(self, *pts, cls="w"):
        self.o.append(f'<path class="{cls}" d="M' + " L".join(f"{x} {y}" for x, y in pts) + '"/>')

    def dot(self, x, y):
        self.o.append(f'<circle class="sld" cx="{x}" cy="{y}" r="3.2"/>')

    def text(self, x, y, s, cls="r", anchor="start"):
        self.o.append(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{self.esc(s)}</text>')

    def gnd(self, x, y):
        self.o.append(f'<use href="#gnd" x="{x}" y="{y}"/>')

    def net(self, x1, x2, y, name, side="left"):
        self.wire((x1, y), (x2, y), cls="nw")
        if side == "left":
            self.text(x1 - 6, y + 4, name, "n", "end")
        else:
            self.text(x2 + 6, y + 4, name, "n")

    def net_up(self, x, y1, y2, name):
        self.wire((x, y1), (x, y2), cls="nw")
        self.text(x, y2 - 5, name, "n", "middle")

    def res_v(self, x, cy, label):
        self.o.append(f'<rect class="bx" x="{x - 7}" y="{cy - 25}" width="14" height="50"/>')
        if label:
            self.text(x + 14, cy + 4, label, "v")
        return cy - 25, cy + 25

    def res_h(self, cx, y, label):
        self.o.append(f'<rect class="bx" x="{cx - 25}" y="{y - 7}" width="50" height="14"/>')
        self.text(cx, y - 12, label, "v", "middle")
        return cx - 25, cx + 25

    def cap_v(self, x, cy, label, polar=False):
        if polar:
            self.o.append(f'<path class="w" d="M{x - 12} {cy - 4} H{x + 12} M{x - 12} {cy + 7} Q{x} {cy + 1} {x + 12} {cy + 7}"/>')
            self.text(x + 16, cy - 8, "+", "p")
        else:
            self.o.append(f'<path class="w" d="M{x - 12} {cy - 4} H{x + 12} M{x - 12} {cy + 4} H{x + 12}"/>')
        self.wire((x, cy - 15), (x, cy - 4))
        self.wire((x, cy + 4), (x, cy + 15))
        if label:
            self.text(x + 16, cy + 4, label, "v")
        return cy - 15, cy + 15

    def diode_up(self, x, y_top, y_bot, label):
        m = (y_top + y_bot) / 2
        self.wire((x, y_top), (x, m - 7))
        self.wire((x, m + 7), (x, y_bot))
        self.o.append(f'<path class="sld" d="M{x - 8} {m + 7} L{x + 8} {m + 7} L{x} {m - 6} z"/>')
        self.o.append(f'<path class="w" d="M{x - 8} {m - 7} H{x + 8}"/>')
        self.text(x + 14, m + 4, label, "v")

    def box(self, x, y, w, h, title, sub=None, cls="bx"):
        self.o.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="3"/>')
        self.text(x, y - 9, title, "r")
        if sub:
            self.text(x, y + h + 16, sub, "p")

    def pin_l(self, x, y, name):
        self.text(x + 9, y + 4, name, "p")

    def pin_r(self, x, y, name):
        self.text(x - 9, y + 4, name, "p", "end")

    def terminal(self, x, pins, title, side="right", w=70):
        """Screw terminal: pins = [(label, y)], wires leave on `side`."""
        top, bot = min(y for _, y in pins) - 16, max(y for _, y in pins) + 16
        self.box(x, top, w, bot - top, title)
        for lab, y in pins:
            self.o.append(f'<circle class="w" cx="{x + 12}" cy="{y}" r="5" style="fill:#fff"/>')
            self.text(x + 24, y + 4, lab, "p")
        return x + w if side == "right" else x

    def section(self, y, title):
        self.text(40, y, title, "t")
        self.o.append(f'<path class="dsh" d="M40 {y + 10} H{self.w - 40}"/>')

    def save(self, path, title):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img">'
               f'<title>{self.esc(title)}</title>\n{STYLE}\n{DEFS}\n<rect width="{self.w}" height="{self.h}" fill="#fff"/>\n'
               + "\n".join(self.o) + "\n</svg>\n")
        path.write_text(svg, encoding="utf-8")
        print("wrote", path)


# ====================================================================== schematic
def schematic():
    d = Svg(1320, 1730)
    d.text(40, 36, "1-roll dryer controller, perfboard version  ·  ESP32-C3 SuperMini + modules from Tronic.lk", "t")
    d.text(40, 58, "same pin map as the 1-roll PCB. red = heavy 14 AWG wire, soldered straight to the parts (never along perfboard tracks).", "v")

    # ------------------------------------------------ power
    d.section(96, "12 v in and 5 v")
    d.box(40, 130, 110, 60, "12 v lead", "from the shared supply (XT60)", cls="mod")
    d.text(52, 156, "+12 v", "p"); d.text(52, 178, "gnd", "p")
    d.o.append('<rect class="bx" x="190" y="143" width="44" height="14"/><path class="w" d="M190 150 H234"/>')
    d.text(212, 136, "f1 15 a ato", "v", "middle"); d.text(212, 176, "inline holder", "p", "middle")
    d.wire((150, 150), (190, 150), cls="hv"); d.wire((234, 150), (300, 150), cls="hv")
    tx = d.terminal(300, [("+12 v", 150), ("gnd", 180)], "t1  12 v in")
    d.wire((150, 180), (300, 180), cls="hv")
    d.wire((tx, 150), (620, 150)); d.wire((tx, 180), (400, 180), (400, 200)); d.gnd(400, 200)
    for x, lab, pol in ((450, "c1 100 µF 25 v", True), (540, "c2 100 nF", False)):
        d.dot(x, 150); t, b = d.cap_v(x, 190, "", pol); d.wire((x, 150), (x, t)); d.gnd(x, b)
        d.text(x, 240, lab, "v", "middle")
    d.box(620, 130, 150, 80, "mp1584 buck module", "set to 5.0 v before connecting!", cls="mod")
    d.pin_l(620, 150, "in+"); d.pin_l(620, 190, "in−"); d.pin_r(770, 150, "out+"); d.pin_r(770, 190, "out−")
    d.wire((620, 190), (600, 190), (600, 205)); d.gnd(600, 205)
    d.wire((770, 190), (790, 190), (790, 205)); d.gnd(790, 205)
    d.net(770, 840, 150, "+5v", side="right")

    # ------------------------------------------------ the SuperMini
    d.section(290, "esp32-c3 supermini (in female headers)")
    ex, ey, ew, eh = 560, 330, 200, 680
    d.box(ex, ey, ew, eh, "u1  esp32-c3 supermini", "its own 3.3 v regulator feeds every sensor", cls="mod")
    L = [("5v", 360, "+5v"), ("gnd", 390, "GND"), ("3v3", 420, "+3v3"), ("gpio0", 470, "hx_sck"), ("gpio1", 500, "hx_dt"),
         ("gpio2", 550, "onewire"), ("gpio3", 600, "runout"), ("gpio21", 650, "motion"), ("gpio20", 700, "button"),
         ("gpio7", 760, "scl"), ("gpio8", 790, "sda")]
    for name, y, lab in L:
        d.pin_l(ex, y, name)
        if lab == "GND":
            d.wire((ex, y), (ex - 30, y), (ex - 30, y + 12)); d.gnd(ex - 30, y + 12)
        else:
            d.net(ex - 50, ex, y, lab)
    Rp = [("gpio4", 400), ("gpio5", 640), ("gpio6", 780), ("gpio10", 980)]
    for name, y in Rp:
        d.pin_r(ex + ew, y, name)
        d.wire((ex + ew, y), (940, y))           # straight to its output stage
    d.pin_r(ex + ew, 1002, "gpio9 = boot (unused)")

    # ------------------------------------------------ outputs (right column)
    X = 900
    # heater: PC817 + IRF3205, gate driven from 12 V
    d.text(X, 330, "heater switch (t2)", "p"); d.text(X, 346, "pc817 → irf3205 gate, 12 v drive", "p")
    l, r = d.res_h(X + 75, 400, "r1 500 Ω")
    d.text(X + 75, 424, "2 × 1 k in parallel", "p", "middle")
    d.wire((X + 40, 400), (l, 400)); d.wire((r, 400), (X + 130, 400))
    d.box(X + 130, 380, 60, 80, "pc817")
    d.o.append(f'<path class="sld" d="M{X + 144} 404 l14 0 l-7 12 z"/><path class="w" d="M{X + 144} 418 h14"/>')
    d.wire((X + 130, 400), (X + 151, 400), (X + 151, 404))
    d.wire((X + 151, 418), (X + 151, 440), (X + 130, 440)); d.wire((X + 130, 440), (X + 120, 440), (X + 120, 452)); d.gnd(X + 120, 452)
    d.text(X + 138, 396, "1", "p"); d.text(X + 138, 452, "2", "p"); d.text(X + 176, 396, "4", "p"); d.text(X + 176, 452, "3", "p")
    # opto output: pin 4 (collector) <- 1k <- +12V ; pin 3 (emitter) -> gate, 10k to gnd
    d.wire((X + 190, 400), (X + 230, 400)); d.dot(X + 230, 400)
    t, b = d.res_v(X + 230, 365, "r2 1 k"); d.wire((X + 230, 400), (X + 230, b)); d.net_up(X + 230, t, t - 10, "+12v")
    d.wire((X + 190, 440), (X + 270, 440)); d.dot(X + 250, 440)
    t, b = d.res_v(X + 250, 480, "r3 10 k"); d.wire((X + 250, 440), (X + 250, t)); d.gnd(X + 250, b)
    d.o.append(f'<use href="#nmos" x="{X + 270}" y="410"/>')
    d.text(X + 326, 446, "q1 irf3205", "r"); d.text(X + 326, 462, "+ to-220 heatsink", "p")
    d.wire((X + 316, 470), (X + 316, 500), cls="hv"); d.text(X + 326, 498, "→ t1 gnd", "p")
    d.wire((X + 316, 410), (X + 316, 360), cls="hv")
    d.text(X + 326, 372, "← t2 heater −", "p")

    # fans: 2N2222A low side
    def fan(y, gpio_net, q, d_, rb, title):
        l, r = d.res_h(X + 75, y, f"{rb} 500 Ω")
        d.wire((X + 40, y), (l, y)); d.wire((r, y), (X + 150, y))
        d.o.append(f'<use href="#npn" x="{X + 150}" y="{y - 30}"/>')
        d.text(X + 200, y + 4, f"{q} 2n2222a", "r")
        d.wire((X + 190, y + 30), (X + 190, y + 40)); d.gnd(X + 190, y + 40)
        d.wire((X + 190, y - 30), (X + 190, y - 50), (X + 330, y - 50))
        d.dot(X + 260, y - 50); d.dot(X + 260, y - 80)
        d.diode_up(X + 260, y - 80, y - 50, d_ + " 1n5819")
        d.net(X + 230, X + 330, y - 80, "+12v")
        d.terminal(X + 330, [("+12 v", y - 80), ("fan −", y - 50)], title)
    fan(640, "blower", "q2", "d1", "r4", "t3  blower")
    fan(780, "exhaust", "q3", "d2", "r5", "t4  exhaust")
    # buzzer
    y = 980
    l, r = d.res_h(X + 75, y, "r6 1 k")
    d.wire((X + 40, y), (l, y)); d.wire((r, y), (X + 150, y))
    d.o.append(f'<use href="#npn" x="{X + 150}" y="{y - 30}"/>')
    d.text(X + 200, y + 4, "q4 2n2222a", "r")
    d.wire((X + 190, y + 30), (X + 190, y + 40)); d.gnd(X + 190, y + 40)
    d.o.append(f'<rect class="bx" x="{X + 180}" y="{y - 82}" width="20" height="26"/>')
    d.wire((X + 190, y - 30), (X + 190, y - 56)); d.net_up(X + 190, y - 82, y - 92, "+5v")
    d.text(X + 210, y - 64, "bz1 5 v active buzzer", "v")

    # ------------------------------------------------ inputs (left column)
    X = 40
    d.text(X, 330, "inputs and sensors", "p")
    # HX711 module
    d.box(X + 150, 450, 120, 120, "hx711 module", cls="mod")
    for nm, yy in (("vcc", 470), ("gnd", 500), ("dt", 530), ("sck", 560)):
        d.pin_r(X + 270, yy, nm)
    d.net(X + 270, X + 310, 470, "+3v3", side="right"); d.net(X + 270, X + 310, 500, "gnd", side="right")
    d.net(X + 270, X + 310, 530, "hx_dt", side="right"); d.net(X + 270, X + 310, 560, "hx_sck", side="right")
    for nm, yy in (("e+", 470), ("e−", 500), ("a−", 530), ("a+", 560)):
        d.pin_l(X + 150, yy, nm)
    d.box(X, 450, 90, 120, "load cell", "10 kg bar cell", cls="mod")
    for nm, yy, col in (("red", 470, "#c62828"), ("black", 500, "#111"), ("white", 530, "#888"), ("green", 560, "#2e7d32")):
        d.o.append(f'<path d="M{X + 90} {yy} H{X + 150}" style="stroke:{col};stroke-width:2.4"/>')
        d.text(X + 84, yy + 4, nm, "p", "end")
    # DS18B20
    y0 = 650
    d.terminal(X, [("red 3v3", y0), ("black gnd", y0 + 30), ("yellow dq", y0 + 60)], "t5  ds18b20 probe (outlet)", w=90)
    d.net(X + 90, X + 120, y0, "+3v3", side="right"); d.net(X + 90, X + 120, y0 + 30, "gnd", side="right")
    d.wire((X + 90, y0 + 60), (X + 300, y0 + 60)); d.dot(X + 250, y0 + 60)
    t, b = d.res_v(X + 250, y0 + 25, "r7 4.7 k"); d.wire((X + 250, y0 + 60), (X + 250, b)); d.net_up(X + 250, t, t - 10, "+3v3")
    d.net(X + 300, X + 340, y0 + 60, "onewire", side="right")
    # BTT SFS V2
    y0 = 790
    d.terminal(X, [("3v3", y0), ("gnd", y0 + 30), ("runout", y0 + 60), ("motion", y0 + 90)], "t6  btt sfs v2")
    d.net(X + 70, X + 110, y0, "+3v3", side="right"); d.net(X + 70, X + 110, y0 + 30, "gnd", side="right")
    d.wire((X + 70, y0 + 60), (X + 300, y0 + 60)); d.dot(X + 220, y0 + 60)
    t, b = d.res_v(X + 220, y0 + 25, "r8 10 k"); d.wire((X + 220, y0 + 60), (X + 220, b)); d.net_up(X + 220, t, t - 10, "+3v3")
    d.net(X + 300, X + 340, y0 + 60, "runout", side="right")
    l, r = d.res_h(X + 200, y0 + 90, "r9 1 k")
    d.wire((X + 70, y0 + 90), (l, y0 + 90)); d.wire((r, y0 + 90), (X + 300, y0 + 90))
    d.net(X + 300, X + 340, y0 + 90, "motion", side="right")
    # button
    y0 = 970
    d.terminal(X, [("button", y0), ("gnd", y0 + 30)], "t7  front button")
    d.wire((X + 70, y0), (X + 300, y0)); d.dot(X + 260, y0)
    t, b = d.res_v(X + 260, y0 - 35, "r10 10 k"); d.wire((X + 260, y0), (X + 260, b)); d.net_up(X + 260, t, t - 10, "+3v3")
    d.net(X + 300, X + 340, y0, "button", side="right")
    d.net(X + 70, X + 110, y0 + 30, "gnd", side="right")

    # ------------------------------------------------ i2c
    d.section(1070, "i2c: chamber sensor and oled (4-pin female headers on the board)")
    d.net(80, 120, 1170, "scl"); d.net(80, 120, 1210, "sda")
    d.wire((120, 1170), (900, 1170)); d.wire((120, 1210), (900, 1210))
    d.dot(170, 1170); t, b = d.res_v(170, 1140, "r11 4.7 k"); d.wire((170, 1170), (170, b)); d.net_up(170, t, t - 8, "+3v3")
    d.dot(240, 1210); t, b = d.res_v(240, 1245, "r12 4.7 k"); d.wire((240, 1210), (240, t)); d.wire((240, b), (240, b + 8), cls="nw")
    d.text(240, b + 22, "+3v3", "n", "middle")
    for jx, title, sub in ((380, "aht20 probe (chamber)", "am2301-style housing, i2c 0x38"), (640, "1.3\" oled (front panel)", "sh1106, i2c 0x3c")):
        d.dot(jx - 30, 1170); d.dot(jx - 15, 1210)
        d.wire((jx - 30, 1170), (jx - 30, 1280), (jx, 1280)); d.wire((jx - 15, 1210), (jx - 15, 1310), (jx, 1310))
        d.box(jx, 1260, 150, 120, title, sub, cls="mod")
        for nm, yy in (("scl", 1280), ("sda", 1310), ("vcc", 1340), ("gnd", 1370)):
            d.pin_l(jx, yy, nm)
        d.net(jx - 40, jx, 1340, "+3v3"); d.net(jx - 40, jx, 1370, "gnd")
    d.text(60, 1450, "check the aht20 probe's wire colours against its label: they vary between makers. if it has its own pull-ups, leave r11/r12 in (the total stays above 2 kΩ).", "p")

    # ------------------------------------------------ notes
    notes = [
        "1. heater current (12.5 a) runs only in red wires: lead → fuse → t1 → heater, and heater − → q1 drain, q1 source → t1 gnd. solder 14 awg to the q1 legs.",
        "2. q1 is fully on with the 12 v gate drive from the pc817. its switching is slow, so drive the heater with slow pwm (about 1 s period).",
        "3. at boot every gpio floats: the pc817 led stays dark and r3 holds q1's gate low, so the heater stays off.",
        "4. 2n2222a fan switches: 500 Ω base (two 1 k in parallel) gives about 5 ma base current, enough for fans up to about 0.2 a.",
        "5. the ksd301 85 °c thermostat and 92 °c thermal fuse stay in series with the heater, in the harness, as in the main design.",
        "6. pin map = 1-roll pcb: gpio0/1 hx711, 2 ds18b20, 3 runout, 4 heater, 5/6 fans, 7/8 i2c, 10 buzzer, 20 button, 21 motion.",
        "7. chamber sensor here is an aht20 (0x38) instead of the pcb's sht40: the firmware (firmware/, build dryer-1roll) detects which one is fitted.",
    ]
    d.o.append(f'<path class="dsh" d="M40 1500 H1120"/>')
    d.text(40, 1530, "notes", "t")
    for i, n in enumerate(notes):
        d.text(40, 1558 + i * 22, n, "v")
    d.save(HERE / "schematic.svg", "Perfboard schematic, 1-roll")


# ====================================================================== layout
def layout():
    """Top view of a 120 x 80 mm dot board (47 x 31 holes): module positions and terminals on the edges."""
    S = 8                                       # px per mm
    W, H = 120, 80
    ox, oy = 130, 90
    d = Svg(ox * 2 + W * S, oy + H * S + 380)
    d.text(ox, 40, "perfboard layout: 120 × 80 mm fr4 dot board (tronic \"vero board dot epoxy fr4 12x8cm\"), component side", "t")
    d.text(ox, 64, "terminals on the two short ends, like the pcb. 1 grid square = 2.54 mm. heavy wires (red) go straight to t1, t2 and q1, not through the board.", "v")
    d.o.append(f'<rect x="{ox}" y="{oy}" width="{W * S}" height="{H * S}" rx="8" style="fill:#e8f0d8;stroke:#556b2f;stroke-width:2"/>')
    for i in range(47):
        for j in range(31):
            d.o.append(f'<circle cx="{ox + (2.5 + i * 2.54) * S:.1f}" cy="{oy + (1.9 + j * 2.54) * S:.1f}" r="1.6" fill="#b08d57"/>')

    def part(x, y, w, h, title, sub="", cls="mod", rot_text=False):
        d.o.append(f'<rect class="{cls}" x="{ox + x * S}" y="{oy + y * S}" width="{w * S}" height="{h * S}" rx="4" style="fill-opacity:0.92"/>')
        d.text(ox + (x + w / 2) * S, oy + (y + h / 2) * S - 2, title, "r", "middle")
        if sub:
            d.text(ox + (x + w / 2) * S, oy + (y + h / 2) * S + 15, sub, "p", "middle")

    def term(x, y, n, title, vertical=True):
        w, h = (8, 5.08 * n) if vertical else (5.08 * n, 8)
        d.o.append(f'<rect x="{ox + x * S}" y="{oy + y * S}" width="{w * S}" height="{h * S}" rx="3" style="fill:#2e7d32;stroke:#1b5e20"/>')
        for k in range(n):
            cx = ox + (x + (4 if vertical else 2.54 + 5.08 * k)) * S
            cy = oy + (y + (2.54 + 5.08 * k if vertical else 4)) * S
            d.o.append(f'<circle cx="{cx}" cy="{cy}" r="9" fill="#cfd8dc" stroke="#455a64"/>')
        tx = ox + (x + w / 2) * S
        ty = oy + (y + h) * S + 16 if not vertical else oy + y * S - 8
        d.text(tx, ty, title, "p", "middle")

    # left end: power, heater and fans (all 12 v), heavy parts
    term(1, 3, 2, "t1 12 v in")
    term(1, 16, 2, "t2 heater")
    term(1, 40, 2, "t3 blower")
    term(1, 54, 2, "t4 exhaust")
    part(12, 2, 21, 21, "q1 irf3205", "on heatsink", cls="bx")
    d.o.append(f'<path class="hv" d="M{ox - 40} {oy + 5.5 * S} H{ox + 1 * S}"/>')
    d.text(ox - 44, oy + 5.5 * S + 4, "+12 v lead", "p", "end")
    d.o.append(f'<path class="hv" d="M{ox - 40} {oy + 10.6 * S} H{ox + 1 * S}"/>')
    d.text(ox - 44, oy + 10.6 * S + 4, "gnd lead", "p", "end")
    d.o.append(f'<path class="hv" d="M{ox + 9 * S} {oy + 23.6 * S} H{ox + 17 * S} V{oy + 21 * S}"/>')
    d.o.append(f'<path class="hv" d="M{ox + 9 * S} {oy + 10.6 * S} H{ox + 24 * S} V{oy + 21 * S}"/>')
    part(12, 25, 16, 11, "pc817 + r1–r3", "gate drive", cls="bx")
    part(30, 25, 10, 11, "c1 c2", "", cls="bx")
    part(12, 39, 24, 19, "q2 q3 d1 d2", "fan switches, r4 r5", cls="bx")
    part(12, 61, 26, 17, "mp1584", "set 5.0 v first")
    # middle: SuperMini, pull-ups, buzzer, I2C headers
    part(42, 20, 19, 24, "u1 supermini", "in female headers")
    part(42, 48, 22, 11, "r7–r12", "pull-ups, r9", cls="bx")
    part(42, 63, 14, 13, "bz1", "+ q4, r6", cls="bx")
    part(66, 54, 14, 8, "i2c 1", "aht20", cls="bx")
    part(83, 54, 14, 8, "i2c 2", "oled", cls="bx")
    # right end: sensor and panel terminals, HX711 with the load-cell cable
    part(66, 3, 34, 15, "load cell cable", "enters here, solders to the hx711", cls="dsh")
    part(66, 22, 34, 22, "hx711 module", "e+ e− a− a+ on its left edge")
    term(111, 3, 3, "t5 ds18b20")
    term(111, 25, 4, "t6 btt sfs v2")
    term(111, 54, 2, "t7 button")
    rows = [
        ("t1 +12 v", "fuse f1 (inline, on the lead) → t1; t1 + → t2 +, c1 +, mp1584 in+, fan + (t3, t4)", "red 14 awg to t2; 22 awg to the rest"),
        ("t1 gnd", "q1 source, c1 −, mp1584 in−/out−, supermini gnd, every module gnd", "black 14 awg to q1; 22 awg to the rest"),
        ("t2 heater −", "q1 drain", "red/black 14 awg, as short as possible"),
        ("mp1584 out+ (5.0 v)", "supermini 5v, buzzer +", "22 awg"),
        ("supermini 3v3", "hx711 vcc, t5 red, t6 3v3, both i2c headers, all pull-ups", "22 awg, white"),
        ("gpio4", "r1 (500 Ω) → pc817 pin 1; pc817 pin 2 → gnd", ""),
        ("pc817 pin 4 / pin 3", "pin 4 → r2 1 k → +12 v; pin 3 → q1 gate, r3 10 k → gnd", ""),
        ("gpio5 / gpio6", "r4 / r5 500 Ω → q2 / q3 base; collector → t3− / t4−; d1 / d2 across each fan", ""),
        ("gpio10", "r6 1 k → q4 base; q4 collector → buzzer −", ""),
        ("gpio0 / gpio1", "hx711 sck / dt", ""),
        ("gpio2", "t5 yellow (dq), r7 4.7 k to 3v3", ""),
        ("gpio3 / gpio21", "t6 runout (r8 10 k to 3v3) / t6 motion through r9 1 k", ""),
        ("gpio20", "t7 button, r10 10 k to 3v3; t7 other side → gnd", ""),
        ("gpio7 / gpio8", "scl / sda to both i2c headers, r11 / r12 4.7 k to 3v3", ""),
    ]
    y = oy + H * S + 50
    d.text(ox, y, "wire list", "t")
    for i, (a, b, c) in enumerate(rows):
        yy = y + 26 + i * 21
        d.text(ox, yy, a, "r")
        d.text(ox + 190, yy, b, "v")
        if c:
            d.text(ox + W * S, yy, c, "p", "end")
    d.save(HERE / "layout.svg", "Perfboard layout, 1-roll")


if __name__ == "__main__":
    schematic()
    layout()
