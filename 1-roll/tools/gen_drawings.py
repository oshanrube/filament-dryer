#!/usr/bin/env python3
"""Generate the single-reel drawings in 1-roll/images/: architecture, isometric, sections.

Run:  python3 1-roll/tools/gen_drawings.py
"""
import math
from pathlib import Path

EDGE, INK, QUIET, ACCENT = "#8c959f", "#1f2328", "#59636e", "#0969da"
HOT, HOT_FILL, TINT, ACC_FILL = "#bf8700", "#fff8e5", "#eef1f4", "#e7f0fb"
FONT = "font-family='system-ui,-apple-system,Segoe UI,Roboto,sans-serif'"
OUT = Path(__file__).resolve().parent.parent / "images"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.o = w, h, []
        self.o.append(f"<rect width='{w}' height='{h}' fill='white'/>")
        self.o.append("<defs><marker id='arr' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' markerHeight='6' "
                      f"orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{EDGE}'/></marker>"
                      "<marker id='arrb' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' markerHeight='6' "
                      f"orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{ACCENT}'/></marker></defs>")
        self.text(24, 32, title, 15, weight="600")

    def text(self, x, y, s, size=13, anchor="start", fill=INK, weight="normal"):
        self.o.append(f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' text-anchor='{anchor}' fill='{fill}' font-weight='{weight}'>{esc(s)}</text>")

    def raw(self, s):
        self.o.append(s)

    def save(self, name):
        svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {self.w} {self.h}' width='{self.w * 2}' "
               f"height='{self.h * 2}' {FONT}>" + "".join(self.o) + "</svg>\n")
        (OUT / name).write_text(svg)
        print("wrote", OUT / name)


# ---------------------------------------------------------------- architecture
def architecture():
    d = Svg(760, 496, "Only the reel and air get hot; power, weighing and control sit below the floor")

    def box(x, y, w, name, line, main=False):
        fill, stroke, sw = (ACC_FILL, ACCENT, 2) if main else ("white", EDGE, 1.25)
        d.raw(f"<rect x='{x}' y='{y}' width='{w}' height='56' rx='8' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
        d.text(x + w / 2, y + 24, name, 13, "middle", INK, "600")
        d.text(x + w / 2, y + 40, line, 11.5, "middle", QUIET)

    d.raw(f"<rect x='196' y='56' width='368' height='184' rx='8' fill='{HOT_FILL}' stroke='{HOT}' stroke-width='1.25'/>")
    d.text(212, 78, "Heated chamber, up to 70 °C", 13, weight="600")
    d.raw(f"<rect x='196' y='248' width='368' height='32' rx='8' fill='{TINT}' stroke='{EDGE}' stroke-width='1.25'/>")
    d.text(380, 268, "Insulated floor", 11.5, "middle", QUIET)
    d.raw(f"<rect x='196' y='288' width='368' height='184' rx='8' fill='none' stroke='{EDGE}' stroke-width='1.25'/>")
    d.text(212, 458, "Cool electronics bay", 13, weight="600")
    paths = ["M292 304V224", "M468 224V304", "M292 376V360", "M468 360V376", "M164 332H212", "M548 416H596",
             "M548 184H572V124H596", "M666 152V168"]
    for p in paths:
        d.raw(f"<path d='{p}' fill='none' stroke='{EDGE}' stroke-width='1.25' marker-end='url(#arr)'/>")
    d.raw(f"<path d='M596 140H580V392H548' fill='none' stroke='{EDGE}' stroke-width='1.25' marker-end='url(#arr)'/>")
    box(212, 96, 160, "Humidity sensors", "SHT40 + outlet probe")
    box(388, 96, 160, "Safety + vent", "thermostat, fuse, fan")
    box(212, 168, 160, "Heater + blower", "PTC 12 V 150 W")
    box(388, 168, 160, "Reel", "on rollers, 608ZZ", main=True)
    box(212, 304, 160, "MOSFET switches", "heater and fans")
    box(388, 304, 160, "Load cell", "HX711, 5 kg")
    box(212, 376, 336, "ESP32-C3 SuperMini, ESPHome", "PID, safety cut-outs, weight, filament motion")
    box(24, 304, 140, "12 V supply", "shared server PSU")
    box(596, 96, 140, "Motion sensor", "BTT V2, at the exit")
    box(596, 168, 140, "Printer", "one PTFE tube in")
    box(596, 392, 140, "Control center", "on the Orange Pi")
    d.text(300, 268, "12 V", 11.5, fill=QUIET)
    d.text(476, 268, "load post", 11.5, fill=QUIET)
    d.text(180, 324, "12 V", 11.5, "middle", QUIET)
    d.text(572, 408, "Wi-Fi", 11.5, "middle", QUIET)
    d.text(586, 300, "runout + motion", 11.5, fill=QUIET)
    d.save("architecture.svg")


# ---------------------------------------------------------------- isometric
def isometric():
    d = Svg(760, 712, "Lift the lid, drop the reel in; all the electrics live in the base")
    d.text(24, 52, "Isometric, about 250 × 155 × 335 mm outside. Solid = housing, dashed = parts inside.", 11.5, fill=QUIET)
    s, ox, oy = 1.15, 330, 455

    def P(x, y, z):
        return ox + (x - y) * 0.866 * s, oy + ((x + y) * 0.5 - z) * s

    def pts(lst):
        return " ".join(f"{P(*p)[0]:.1f},{P(*p)[1]:.1f}" for p in lst)

    def ring(cx, y, cz, r):
        return pts([(cx + r * math.cos(i * math.pi / 24), y, cz + r * math.sin(i * math.pi / 24)) for i in range(49)])

    def seg(a, b):
        p, q = P(*a), P(*b)
        return f"M{p[0]:.1f} {p[1]:.1f}L{q[0]:.1f} {q[1]:.1f}"

    def fy(x0, x1, y, z0, z1):
        return pts([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)])

    def fx(x, y0, y1, z0, z1):
        return pts([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)])

    def fz(x0, x1, y0, y1, z):
        return pts([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)])

    def poly(p, stroke=EDGE, w=1.25, dash=None, fill="none"):
        da = f" stroke-dasharray='{dash}'" if dash else ""
        d.raw(f"<polygon points='{p}' fill='{fill}' stroke='{stroke}' stroke-width='{w}'{da}/>")

    def pline(p, stroke=EDGE, w=1.25, dash=None):
        da = f" stroke-dasharray='{dash}'" if dash else ""
        d.raw(f"<polyline points='{p}' fill='none' stroke='{stroke}' stroke-width='{w}'{da}/>")

    def path(p, stroke=EDGE, w=1.25, dash=None, extra=""):
        da = f" stroke-dasharray='{dash}'" if dash else ""
        d.raw(f"<path d='{p}' fill='none' stroke='{stroke}' stroke-width='{w}'{da}{extra}/>")

    # inside parts
    for y in (62.5, 132.5):
        pline(ring(125, y, 208, 100), ACCENT, 1, "4 3")
    for y in (62.5, 132.5):
        pline(ring(125, y, 208, 27), ACCENT, 1, "4 3")
    poly(fz(10, 240, 10, 145, 82), ACCENT, 1, "4 3")
    for p in (fy(150, 240, 50, 90, 200), fz(150, 240, 10, 50, 200), fx(240, 10, 50, 90, 200),
              fy(115, 195, 110, 35, 48), fz(115, 195, 85, 110, 48), fx(195, 85, 110, 35, 48)):
        poly(p, ACCENT, 1, "4 3")
    path(seg((70, 50, 107), (70, 145, 107)) + seg((180, 50, 107), (180, 145, 107)), ACCENT, 5,
         extra=" stroke-opacity='0.5' stroke-linecap='round'")
    path(seg((125, 97.5, 48), (125, 97.5, 90)), ACCENT, 4, extra=" stroke-opacity='0.5' stroke-linecap='round'")
    # housing
    path(seg((0, 0, 0), (250, 0, 0)) + seg((0, 0, 0), (0, 155, 0)) + seg((0, 0, 0), (0, 0, 335)), EDGE, 1.25, "4 4")
    poly(fz(0, 250, 0, 155, 335)); poly(fy(0, 250, 155, 0, 335)); poly(fx(250, 0, 155, 0, 335))
    path(seg((0, 155, 315), (250, 155, 315)) + seg((250, 155, 315), (250, 0, 315))
         + seg((0, 155, 68), (250, 155, 68)) + seg((250, 155, 68), (250, 0, 68)))
    # lid
    poly(fz(30, 170, 55, 140, 335), w=1)
    path("".join(seg((185, y, 335), (230, y, 335)) for y in (15, 23, 31, 39, 47)), w=1)
    poly(fy(40, 60, 155, 300, 330), w=1); poly(fy(190, 210, 155, 300, 330), w=1)
    poly(fy(40, 60, 0, 305, 325), w=1, dash="3 3"); poly(fy(190, 210, 0, 305, 325), w=1, dash="3 3")
    # panels
    poly(fy(30, 90, 155, 22, 50), w=1); pline(ring(115, 155, 36, 6), w=1)
    poly(fx(250, 100, 120, 26, 42), w=1)
    path("".join(seg((250, y, 15), (250, y, 55)) for y in (15, 25, 35, 45, 55, 65)), w=1)
    # BTT sensor at the exit on the right wall
    poly(fz(250, 275, 120, 145, 290), w=1.25, fill="white"); poly(fy(250, 275, 145, 255, 290), w=1.25, fill="white")
    poly(fx(275, 120, 145, 255, 290), w=1.25, fill="white")
    path(seg((275, 132.5, 272), (315, 132.5, 272)), EDGE, 3)

    def lead(p3, lx, ly, name, line, anchor):
        p = P(*p3)
        d.raw(f"<path d='M{p[0]:.1f} {p[1]:.1f}L{lx} {ly}' stroke='{QUIET}' stroke-width='1' fill='none'/>")
        d.raw(f"<circle cx='{p[0]:.1f}' cy='{p[1]:.1f}' r='2.5' fill='{INK}'/>")
        tx = lx - 6 if anchor == "end" else lx + 6
        d.text(tx, ly + 4, name, 13, anchor, INK, "600")
        d.text(tx, ly + 20, line, 11.5, anchor, QUIET)

    lead((30, 140, 335), 174, 116, "Lid window", "2 mm polycarbonate", "end")
    lead((50, 155, 315), 174, 196, "Toggle latches", "2, stainless", "end")
    lead((25, 132.5, 208), 174, 296, "eSUN 1 kg reel", "drops onto 2 rollers", "end")
    lead((10, 145, 82), 174, 396, "Insulated floor", "load post through it", "end")
    lead((115, 97.5, 41), 174, 476, "Load cell", "5 kg, in the cool bay", "end")
    lead((60, 155, 36), 174, 546, "OLED + button", "front panel", "end")
    lead((50, 0, 315), 594, 96, "Hinges at the back", "lid lifts open", "start")
    lead((207, 31, 335), 594, 176, "Exhaust fan + flap", "K1C 3010, vents", "start")
    lead((275, 132.5, 272), 594, 346, "Motion sensor", "BTT V2, PTFE out", "start")
    lead((240, 50, 145), 594, 426, "Heater + blower", "duct at the back", "start")
    lead((250, 40, 35), 594, 516, "Bay vents", "keep the bay cool", "start")
    lead((250, 110, 34), 594, 596, "12 V in (XT60)", "from the shared supply", "start")
    d.save("housing-isometric.svg")


# ---------------------------------------------------------------- sections
def sections():
    d = Svg(760, 540, "Sections: heater duct behind the reel, scale and electronics under the floor")
    k = 1.2
    X = lambda x: 72 + x * k
    S = lambda y: 470 + y * k
    Z = lambda z: 482 - z * k

    def bf(x0, x1, z0, z1, w=1, fill="none", stroke=EDGE, dash=None):
        da = f" stroke-dasharray='{dash}'" if dash else ""
        d.raw(f"<rect x='{X(x0):.1f}' y='{Z(z1):.1f}' width='{(x1 - x0) * k:.1f}' height='{(z1 - z0) * k:.1f}' fill='{fill}' stroke='{stroke}' stroke-width='{w}'{da}/>")

    def bs(y0, y1, z0, z1, w=1, fill="none", stroke=EDGE, dash=None):
        da = f" stroke-dasharray='{dash}'" if dash else ""
        d.raw(f"<rect x='{S(y0):.1f}' y='{Z(z1):.1f}' width='{(y1 - y0) * k:.1f}' height='{(z1 - z0) * k:.1f}' fill='{fill}' stroke='{stroke}' stroke-width='{w}'{da}/>")

    def circ(cx, cy, r, stroke=EDGE, w=1):
        d.raw(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{r:.1f}' fill='none' stroke='{stroke}' stroke-width='{w}'/>")

    def ln(p, stroke=EDGE, w=1.25, extra=""):
        d.raw(f"<path d='{p}' fill='none' stroke='{stroke}' stroke-width='{w}'{extra}/>")

    d.text(72, 68, "Front section", 13, weight="600")
    d.text(470, 68, "Side section, back on the left", 13, weight="600")
    # front
    bf(0, 250, 0, 335, 1.25)
    ln(f"M{X(0)} {Z(315)}H{X(250)}M{X(0)} {Z(68)}H{X(250)}")
    bf(10, 240, 82, 315); bf(4, 246, 68, 82, fill=TINT); bf(4, 246, 4, 64); bf(185, 225, 318, 332)
    ln(f"M{X(55)} {Z(110)}V{Z(92)}H{X(195)}V{Z(110)}", w=1)
    bf(117, 133, 40, 92, fill=TINT); bf(110, 195, 35, 48); bf(165, 195, 4, 35); bf(15, 95, 10, 28)
    bf(240, 252, 266, 278); bf(252, 276, 255, 290, 1.25, "white")
    circ(X(125), Z(208), 100 * k, ACCENT, 1.5); circ(X(125), Z(208), 27 * k, ACCENT)
    circ(X(70), Z(107), 15 * k, ACCENT); circ(X(180), Z(107), 15 * k, ACCENT)
    ln(f"M{X(164)} {Z(300)}H{X(246)}V{Z(272)}H{X(296)}", ACCENT, 1.5, " marker-end='url(#arrb)'")
    d.text(X(95), 96, "Lid, gasket, vent fan", 11.5, "middle", QUIET)
    d.text(X(125), Z(165), "reel Ø200", 11.5, "middle", INK)
    d.text(X(52), Z(107) + 4, "rollers", 11.5, "end", QUIET)
    d.text(X(20), Z(75) + 4, "insulated floor", 10.5, fill=QUIET)
    d.text(X(160), Z(53), "load cell", 11.5, "middle", QUIET)
    d.text(X(55), Z(19) + 4, "perfboard", 11.5, "middle", QUIET)
    d.text(X(264), Z(296), "BTT", 11.5, "middle", QUIET)
    ln(f"M{X(0)} 500H{X(250)}M{X(0)} 494V506M{X(250)} 494V506M56 {Z(0)}V{Z(335)}M50 {Z(0)}H62M50 {Z(335)}H62", QUIET, 1)
    d.text(X(125), 520, "250 mm", 11.5, "middle")
    d.raw(f"<text x='44' y='{Z(167.5):.1f}' transform='rotate(-90 44 {Z(167.5):.1f})' font-size='11.5' text-anchor='middle' fill='{INK}'>335 mm</text>")
    # side
    bs(0, 155, 0, 335, 1.25)
    ln(f"M{S(0)} {Z(315)}H{S(155)}M{S(0)} {Z(68)}H{S(155)}")
    bs(10, 145, 82, 315); bs(4, 151, 68, 82, fill=TINT); bs(4, 151, 4, 64)
    bs(10, 50, 90, 200); bs(16, 44, 150, 170); circ(S(30), Z(115), 14); bs(10, 50, 215, 290)
    bs(48, 147, 88, 92); bs(89.5, 105.5, 40, 88, fill=TINT); bs(91, 104, 35, 48)
    circ(S(-4), Z(322), 5); bs(155, 161, 300, 330)
    bs(62.5, 132.5, 108, 308, 1.5, stroke=ACCENT); bs(50, 145, 92, 122, 1, stroke=ACCENT, dash="3 3")
    d.text(S(77.5), 96, "lid + vent fan", 11.5, "middle", QUIET)
    d.text(S(30), Z(252) + 4, "silica", 11.5, "middle", QUIET)
    d.text(S(30), Z(160) + 4, "PTC", 11.5, "middle", QUIET)
    d.text(S(30), 322, "blower", 11.5, "middle", QUIET)
    d.text(S(97.5), Z(208) + 4, "eSUN reel", 11.5, "middle", INK)
    d.text(S(86), Z(41) + 4, "load cell", 11.5, "end", QUIET)
    d.text(S(-12), Z(322) + 4, "hinge", 11.5, "end", QUIET)
    d.text(S(163), Z(315) + 4, "latch", 11.5, fill=QUIET)
    d.text(S(163), Z(200), "chamber", 11.5, fill=QUIET)
    d.text(S(163), Z(75) + 4, "floor", 11.5, fill=QUIET)
    d.text(S(163), Z(34), "bay", 11.5, fill=QUIET)
    ln(f"M{S(0)} 500H{S(155)}M{S(0)} 494V506M{S(155)} 494V506", QUIET, 1)
    d.text(S(77.5), 520, "155 mm", 11.5, "middle")
    d.save("housing-sections.svg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    architecture()
    isometric()
    sections()
