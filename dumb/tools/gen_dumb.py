#!/usr/bin/env python3
"""Drawings for the "dumb" dryer: an STC-3028 humidity + temperature controller, a W1209 for the
second heat stage, no microcontroller.

Writes dumb/wiring.svg and dumb/images/heat-steps.svg.  Run from the repo root:
    python3 dumb/tools/gen_dumb.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RED, BLACK, ORANGE, YELLOW, BLUE, GREY = "#c62828", "#212121", "#ef6c00", "#f9a825", "#1565c0", "#9e9e9e"

STYLE = """<style>
text{font-family:Inter,Arial,sans-serif}
.t{font-size:18px;font-weight:600;fill:#111}.r{font-size:14px;fill:#111}.v{font-size:12px;fill:#444}.p{font-size:11px;fill:#666}
.bx{fill:#fff;stroke:#111;stroke-width:1.6}.mod{fill:#f4f8ff;stroke:#1565c0;stroke-width:1.6}.safe{fill:#fff4e5;stroke:#ef6c00;stroke-width:1.6}
</style>"""


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.o = w, h, []

    def esc(self, s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def text(self, x, y, s, cls="r", anchor="start"):
        self.o.append(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{self.esc(s)}</text>')

    def wire(self, pts, color, width=3):
        d = "M" + " L".join(f"{x} {y}" for x, y in pts)
        self.o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')

    def dot(self, x, y, color="#111"):
        self.o.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{color}"/>')

    def box(self, x, y, w, h, title, sub="", cls="bx"):
        self.o.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>')
        self.text(x + w / 2, y + 22, title, "r", "middle")
        if sub:
            self.text(x + w / 2, y + 40, sub, "p", "middle")

    def term(self, x, y, label, anchor="start"):
        self.o.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        dx = 10 if anchor == "start" else -10
        self.text(x + dx, y + 4, label, "p", anchor)

    def save(self, path, title):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img">'
                        f'<title>{self.esc(title)}</title>{STYLE}<rect width="{self.w}" height="{self.h}" fill="#fff"/>\n'
                        + "\n".join(self.o) + "\n</svg>\n", encoding="utf-8")
        print("wrote", path)


def wiring():
    d = Svg(1180, 900)
    d.text(30, 36, "Dumb dryer: wiring", "t")
    d.text(30, 58, "12 V from the shared supply. The heater only runs when the box is too humid AND below the temperature cap; "
                   "near the cap the W1209 drops half the heater.", "v")
    TOP, GND = 110, 800
    # 12 V in
    d.box(30, 80, 120, 60, "XT60 12 V in", "shared supply lead")
    d.wire([(150, TOP), (190, TOP)], RED)
    d.o.append(f'<rect x="190" y="{TOP - 9}" width="46" height="18" rx="3" fill="#fff" stroke="#111" stroke-width="1.4"/>')
    d.text(213, TOP - 16, "F1 15 A", "p", "middle")
    d.wire([(236, TOP), (1130, TOP)], RED)
    d.text(1130, TOP - 10, "+12 V", "v", "end")
    d.wire([(150, 130), (170, 130), (170, GND), (1130, GND)], BLACK)
    d.text(1130, GND + 20, "GND", "v", "end")

    # STC-3028: power and probe on the left, the two relays on the right
    sx, sy = 230, 200
    d.box(sx, sy, 300, 260, "STC-3028 (DC 12 V version)", "front-panel cut-out 71 × 29 mm", "mod")
    d.term(sx + 20, sy + 70, "12V +"); d.term(sx + 20, sy + 100, "12V −"); d.term(sx + 20, sy + 160, "probe")
    d.term(sx + 280, sy + 90, "humidity COM", "end"); d.term(sx + 280, sy + 120, "humidity NO (dehumidify)", "end")
    d.term(sx + 280, sy + 180, "temp COM", "end"); d.term(sx + 280, sy + 210, "temp NO (heat)", "end")
    d.wire([(sx + 20, TOP), (sx + 20, sy + 70)], RED, 2); d.dot(sx + 20, TOP, RED)
    d.wire([(sx + 20, sy + 100), (185, sy + 100), (185, GND)], BLACK, 2); d.dot(185, GND, BLACK)
    # probe
    d.wire([(sx + 20, sy + 160), (215, sy + 160), (215, 535), (305, 535), (305, 560)], GREY, 2)
    d.box(230, 560, 150, 50, "T + RH probe", "in the chamber air")

    # humidity relay: +12 V -> DRY
    RX = sx + 280
    d.wire([(560, TOP), (560, sy + 90), (RX, sy + 90)], RED, 3); d.dot(560, TOP, RED)
    DRY_Y = 640
    d.wire([(RX, sy + 120), (620, sy + 120), (620, DRY_Y), (330, DRY_Y)], ORANGE, 3)
    d.text(340, DRY_Y - 8, "DRY: on while the box is too humid", "p")
    # blower on DRY
    d.dot(330, DRY_Y, ORANGE)
    d.wire([(330, DRY_Y), (330, 690)], ORANGE, 3)
    d.box(270, 690, 120, 50, "blower", "4010 12 V")
    d.wire([(330, 740), (330, GND)], BLACK, 3); d.dot(330, GND, BLACK)
    # temp relay: DRY -> HEAT
    d.dot(580, DRY_Y, ORANGE)
    d.wire([(580, DRY_Y), (580, sy + 180), (RX, sy + 180)], ORANGE, 3)
    d.wire([(RX, sy + 210), (545, sy + 210), (545, 470), (760, 470)], YELLOW, 3)
    d.text(560, 492, "HEAT: humid and below the cap", "p")
    # safety chain
    d.box(760, 445, 120, 50, "KSD301", "85 °C, opens", "safe")
    d.wire([(880, 470), (910, 470)], YELLOW, 3)
    d.box(910, 445, 130, 50, "thermal fuse", "92 °C, one-shot", "safe")
    SAFE_X = 1080
    d.wire([(1040, 470), (SAFE_X, 470), (SAFE_X, 560)], YELLOW, 3); d.dot(SAFE_X, 520, YELLOW)
    # heater A: always on when HEAT
    d.box(1020, 560, 120, 60, "heater A", "50 W, 3 Ω")
    d.wire([(SAFE_X, 620), (SAFE_X, GND)], BLACK, 3); d.dot(SAFE_X, GND, BLACK)
    # W1209 stage
    wx, wy = 780, 200
    d.box(wx, wy, 220, 170, "W1209 (stage 2)", "set 5 °C under the cap", "mod")
    d.term(wx + 20, wy + 70, "+12 V"); d.term(wx + 20, wy + 95, "GND")
    d.term(wx + 200, wy + 70, "relay COM", "end"); d.term(wx + 200, wy + 100, "relay NO", "end")
    d.term(wx + 200, wy + 140, "NTC probe", "end")
    d.wire([(wx + 20, TOP), (wx + 20, wy + 70)], RED, 2); d.dot(wx + 20, TOP, RED)
    d.wire([(wx + 20, wy + 95), (wx - 30, wy + 95), (wx - 30, GND)], BLACK, 2); d.dot(wx - 30, GND, BLACK)
    d.wire([(SAFE_X, 520), (1110, 520), (1110, wy + 70), (wx + 200, wy + 70)], YELLOW, 3)
    d.wire([(wx + 200, wy + 100), (1060, wy + 100), (1060, 400), (895, 400), (895, 650)], "#8d6e63", 3)
    d.box(835, 650, 120, 60, "heater B", "50 W, 3 Ω")
    d.wire([(895, 710), (895, GND)], BLACK, 3); d.dot(895, GND, BLACK)
    d.wire([(wx + 200, wy + 140), (wx + 240, wy + 140)], GREY, 2)
    d.text(wx + 244, wy + 144, "→ next to the STC probe", "p")

    notes = [
        "Heaters A and B: aluminium-housed 50 W resistors (RX24, 3 Ω: 48 W each at 12 V), screwed to one finned heatsink in the blower's airflow.",
        "The KSD301 and thermal fuse sit in the chamber air near the lid; they protect both heaters (a probe that falls out or fails cannot run away).",
        "Wire the heater path in 16 AWG silicone (8 A); the controllers' power in 22 AWG. All relays switch 12 V DC well inside their 10 A rating.",
    ]
    for i, n in enumerate(notes):
        d.text(30, 846 + i * 18, n, "v")
    d.save(ROOT / "wiring.svg", "Dumb dryer wiring")


def heat_steps():
    W, H = 760, 380
    d = Svg(W, H)
    d.text(30, 34, "Heater power near the temperature cap (while the box is too humid)", "t")
    x0, x1, y0, y1 = 80, 700, 300, 80          # plot area
    tmin, tmax = -15, 3                        # °C relative to the cap
    X = lambda t: x0 + (t - tmin) / (tmax - tmin) * (x1 - x0)
    Y = lambda p: y0 - p / 100 * (y0 - y1)
    d.wire([(x0, y0), (x1, y0)], "#111", 1.4); d.wire([(x0, y0), (x0, y1 - 10)], "#111", 1.4)
    for p in (0, 50, 100):
        d.text(x0 - 10, Y(p) + 4, f"{p} W" if p else "0", "p", "end")
    for t, lab in ((-15, "cap − 15"), (-10, "cap − 10"), (-5, "cap − 5"), (0, "cap"), (3, "+3")):
        d.text(X(t), y0 + 20, lab, "p", "middle")
    d.wire([(X(-15), Y(96)), (X(-5), Y(96)), (X(-5), Y(48)), (X(0), Y(48)), (X(0), Y(0)), (X(3), Y(0))], RED, 3.5)
    d.wire([(X(-15), Y(96)), (X(0), Y(96)), (X(0), Y(0))], GREY, 1.5)
    d.text(X(-10), Y(96) - 10, "both halves: 96 W", "v", "middle")
    d.text(X(-2.5), Y(48) - 10, "half: 48 W", "v", "middle")
    d.text(X(0) + 8, Y(70), "off at the cap", "v")
    d.text(X(-7.5), Y(30), "grey: a single on/off heater", "p", "middle")
    d.text(30, H - 22, "Each step has 1-2 °C of hysteresis. Halving the power for the last 5 °C roughly halves the overshoot when the heater switches off.", "p")
    d.save(ROOT / "images" / "heat-steps.svg", "Heater power steps")


if __name__ == "__main__":
    wiring()
    heat_steps()
