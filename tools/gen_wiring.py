#!/usr/bin/env python3
"""Generate the wiring (harness) diagram and connector table for each version.

Writes <version>/wiring.svg and <version>/wiring-table.html.
Run:  python3 tools/gen_wiring.py
"""
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INK, QUIET, EDGE = "#1f2328", "#59636e", "#8c959f"
FONT = "font-family='system-ui,-apple-system,Segoe UI,Roboto,sans-serif'"

# Harness colours (a 6-colour 22 AWG silicone set + 14 AWG red/black)
COL = {
    "red": "#d1242f", "black": "#24292f", "white": "#c9d1d9", "yellow": "#d4a72c",
    "blue": "#0969da", "green": "#1a7f37", "motor": "#8250df",
}
LEGEND = [("red", "+12 V (14 AWG on heater and feed)"), ("black", "GND, or a fan's switched minus"),
          ("white", "+3.3 V"), ("yellow", "clock / SCL / motion"), ("blue", "data / SDA / DT / DQ"),
          ("green", "switch signals"), ("motor", "motor's own 4-wire cable")]

# Connector definitions: id -> (title, kind, gauge, [(pin signal, colour)], destination, where, notes)
CONN = {
    "J1": ("12 V in", "XT60 (XT60PW-M on the board, XT60-F on the lead)", "14 AWG",
            [("+12V", "red"), ("GND", "black")], "Shared supply's fuse block (15 A per box); F1 15 A on the board", "through the base wall",
            "J1 sits at the board edge and pokes through the base wall; nothing to wire inside the box"),
    "TB2": ("Heater", "screw terminal, 2-way", "14 AWG",
            [("+12V out → TH1 → TF1 → HT1", "red"), ("HEATER− (Q1 drain)", "black")], "PTC heater HT1, with TH1 KSD301 and TF1 92 °C in series on the red wire", "chamber",
            "TH1 and TF1 sit high on the back wall in the chamber air"),
    "J3": ("Blower", "JST-XH 2", "22 AWG", [("+12V", "red"), ("FAN− (Q2 drain)", "black")], "5015 blower M1", "chamber, heater duct",
           "The fan's black lead goes to the MOSFET, not GND"),
    "J4": ("Exhaust fan", "JST-XH 2", "22 AWG", [("+12V", "red"), ("FAN− (Q3 drain)", "black")], "4010 fan M2 in the lid", "lid",
           "Leave a slack loop at the hinge"),
    "J5": ("Chamber sensor", "JST-XH 4", "22 AWG", [("+3V3", "white"), ("GND", "black"), ("SCL", "yellow"), ("SDA", "blue")], "Sensor board SB1 (SHT40), wires soldered to its pads", "chamber", "Silicone wire: the chamber reaches 70 °C"),
    "J6": ("Heater outlet sensor", "JST-XH 3", "22 AWG", [("+3V3", "white"), ("GND", "black"), ("DQ", "blue")], "Sensor board SB2 (DS18B20Z) in the heater outlet, wires soldered to its pads", "chamber",
           "Silicone wire; the board sits in the outlet air, not on the heater"),
    "J8": ("OLED", "JST-XH 4", "22 AWG", [("+3V3", "white"), ("GND", "black"), ("SCL", "yellow"), ("SDA", "blue")], "SH1106 OLED U6", "front panel", ""),
    "J9": ("Button", "JST-XH 2", "22 AWG", [("BTN", "green"), ("GND", "black")], "Push button SW1", "front panel", ""),
    "J11": ("Load cell A", "JST-XH 4", "the cell's leads", [("E+", "red"), ("E−", "black"), ("A−", "white"), ("A+", "green")], "Load cell LC1 (its HX711, U7, is on the board)", "bay",
            "Crimp the cell's own four leads straight into the housing"),
    "J12": ("Load cell B", "JST-XH 4", "the cell's leads", [("E+", "red"), ("E−", "black"), ("A−", "white"), ("A+", "green")], "Load cell LC2 (its HX711, U8, is on the board)", "bay",
            "Same colours as scale A"),
    "J13": ("Lane A sensor", "JST-XH 3", "22 AWG", [("+3V3", "white"), ("GND", "black"), ("LANE_A", "green")], "K1C runout sensor S1", "feeder pod",
            "Check the sensor's pin order with a multimeter first"),
    "J14": ("Lane B sensor", "JST-XH 3", "22 AWG", [("+3V3", "white"), ("GND", "black"), ("LANE_B", "green")], "K1C runout sensor S2", "feeder pod", ""),
    "J15": ("Motion sensor", "JST-XH 4", "22 AWG", [("+3V3", "white"), ("GND", "black"), ("RUNOUT", "green"), ("MOTION", "yellow")],
            "BTT Smart Filament Sensor V2 U13", "pod / exit", "Confirm the BTT pin order with a multimeter while turning the wheel"),
    "J16": ("Feeder A motor", "JST-XH 4", "motor cable", [("A1", "motor"), ("A2", "motor"), ("B1", "motor"), ("B2", "motor")],
            "K1C extruder motor M3 (driver U10 on the board)", "feeder pod", "Swap one coil pair if the motor turns the wrong way"),
    "J17": ("Feeder B motor", "JST-XH 4", "motor cable", [("A1", "motor"), ("A2", "motor"), ("B1", "motor"), ("B2", "motor")],
            "K1C extruder motor M4 (driver U11 on the board)", "feeder pod", ""),
}

VERSIONS = {
    "2-roll-feeder": {
        "title": "Two-reel dryer: wiring",
        "board": ["U1 ESP32-C3-WROOM-02, J2 USB-C", "U2 12→5 V buck, U12 3.3 V", "U3 MCP23017 I/O expander",
                  "U4 + Q1 heater, Q2-Q4 fans", "U13 bay SHT40, BZ1 buzzer", "U7, U8 HX711 scales",
                  "U10, U11 TMC2209 feeder drivers"],
        "conns": ["J1", "TB2", "J3", "J4", "J5", "J6", "J8", "J9", "J11", "J12", "J13", "J14", "J15", "J16", "J17"],
        "right_zone": "Feeder pod (outside the heat)",
    },
    "1-roll": {
        "title": "Single-reel dryer: wiring",
        "board": ["U1 ESP32-C3-WROOM-02, J2 USB-C", "U2 12→5 V buck, U12 3.3 V", "U3 MCP23017 I/O expander",
                  "U4 + Q1 heater, Q2-Q4 fans", "U13 bay SHT40, BZ1 buzzer", "U7 HX711 scale",
                  "(feeder parts left off)"],
        "conns": ["J1", "TB2", "J3", "J4", "J5", "J6", "J8", "J9", "J11", "J15"],
        "right_zone": "Right wall, outside (filament exit)",
    },
}


def esc(s):
    return html.escape(s, quote=True)


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.o = w, h, [f"<rect width='{w}' height='{h}' fill='white'/>"]

    def text(self, x, y, s, size=12, anchor="start", fill=INK, weight="normal"):
        self.o.append(f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' text-anchor='{anchor}' fill='{fill}' font-weight='{weight}'>{esc(s)}</text>")

    def rect(self, x, y, w, h, fill="white", stroke=INK, sw=1.4, rx=6, dash=None):
        da = f" stroke-dasharray='{dash}'" if dash else ""
        self.o.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='{rx}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'{da}/>")

    def box(self, x, y, w, h, name, sub=None):
        self.rect(x, y, w, h)
        self.text(x + w / 2, y + h / 2 + (-2 if sub else 4), name, 12, "middle", INK, "600")
        if sub:
            self.text(x + w / 2, y + h / 2 + 13, sub, 10.5, "middle", QUIET)

    def cable(self, pts, colours, label=None, label_at=None):
        """Orthogonal path; one line per conductor, offset 4 px apart."""
        n = len(colours)
        for i, c in enumerate(colours):
            d = (i - (n - 1) / 2) * 4
            off = []
            for k, (x, y) in enumerate(pts):
                normals = []
                if k > 0:
                    ux, uy = _unit(pts[k - 1], pts[k]); normals.append((-uy, ux))
                if k < len(pts) - 1:
                    ux, uy = _unit(pts[k], pts[k + 1]); normals.append((-uy, ux))
                if len(normals) == 2 and normals[0] != normals[1]:
                    nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
                else:
                    nx, ny = normals[0]
                off.append((x + nx * d, y + ny * d))
            dstr = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in off)
            self.o.append(f"<path d='{dstr}' fill='none' stroke='{COL[c]}' stroke-width='2.2' stroke-linejoin='round'/>")
        if label:
            lx, ly = label_at
            w = 7 * len(label) + 10
            self.o.append(f"<rect x='{lx - 4}' y='{ly - 12}' width='{w}' height='17' rx='3' fill='white' stroke='{EDGE}' stroke-width='0.8'/>")
            self.text(lx + 1, ly, label, 11, fill=INK, weight="600")

    def save(self, path):
        svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {self.w} {self.h}' width='{self.w}' height='{self.h}' {FONT}>"
               + "".join(self.o) + "</svg>\n")
        path.write_text(svg, encoding="utf-8")
        print("wrote", path)


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = max(abs(dx), abs(dy)) or 1
    return (dx / L, dy / L)


def cols(cid):
    return [c for _, c in CONN[cid][3]]


def diagram(version, spec):
    has = set(spec["conns"])
    d = Svg(1700, 1240)
    d.text(24, 40, spec["title"], 22, weight="700")
    d.text(24, 64, "Physical harness: each cable from its board connector to the part. Wire colours as drawn; "
                   "connectors are JST-XH 2.54 mm unless noted.", 12.5, fill=QUIET)
    # zones
    d.rect(250, 90, 940, 330, "#fff8e5", "#bf8700", 1.2, 10)
    d.text(266, 112, "Heated chamber (and lid)", 13, weight="700")
    d.rect(250, 432, 940, 22, "#eef1f4", EDGE, 1, 6)
    d.text(262, 448, "Insulated floor: one grommet, sealed with RTV", 11, fill=QUIET)
    d.rect(250, 466, 940, 744, "#f6f8fa", EDGE, 1.2, 10)
    d.text(266, 488, "Electronics bay (base)", 13, weight="700")
    d.rect(20, 466, 210, 300, "white", EDGE, 1.2, 10, "6 4")
    d.text(34, 488, "Outside", 13, weight="700")
    d.rect(1210, 90, 470, 1120, "#f6f8fa", EDGE, 1.2, 10, "6 4")
    d.text(1226, 112, spec["right_zone"], 13, weight="700")

    # board
    bx, by, bw, bh = 560, 560, 320, 500
    # ---- cables first (boxes drawn over their ends)
    # power in
    d.cable([(130, 620), (560, 620)], cols("J1"), "J1  12 V in (XT60)", (300, 606))
    # chamber cables (from board top)
    d.cable([(590, 560), (590, 380), (380, 380), (380, 330)], cols("TB2"), "TB2", (596, 520))
    d.cable([(640, 560), (640, 340), (580, 340), (580, 300)], cols("J3"), "J3", (646, 540))
    d.cable([(740, 560), (740, 300)], cols("J5"), "J5", (750, 520))
    d.cable([(800, 560), (800, 352), (900, 352), (900, 300)], cols("J6"), "J6", (810, 540))
    d.cable([(860, 560), (860, 392), (1080, 392), (1080, 176)], cols("J4"), "J4", (1000, 386))
    # bay, left of board
    d.cable([(560, 700), (370, 700)], cols("J11"), "J11", (526, 690 - 4))
    if "J12" in has:
        d.cable([(560, 800), (370, 800)], cols("J12"), "J12", (526, 786))
    # front panel (below board)
    d.cable([(640, 1060), (640, 1110)], cols("J8"), "J8", (650, 1090))
    d.cable([(800, 1060), (800, 1110)], cols("J9"), "J9", (810, 1090))
    # right side
    right = []
    if "J13" in has:
        right += [("J13", 600), ("J14", 680)]
    right += [("J15", 760)]
    if "J16" in has:
        right += [("J16", 860), ("J17", 960)]
    for cid, y in right:
        d.cable([(880, y), (1300, y)], cols(cid), cid, (900, y - 10))
    if right:
        d.text(1030, 1040 if "J16" in has else 820, "cables run up a printed channel", 10.5, "middle", QUIET)
        d.text(1030, 1056 if "J16" in has else 836, "on the outside wall", 10.5, "middle", QUIET)

    # ---- boxes
    d.rect(bx, by, bw, bh, "white", INK, 1.8, 8)
    d.text(bx + bw / 2, by + 34, "Controller board", 15, "middle", INK, "700")
    d.text(bx + bw / 2, by + 52, "JLCPCB-assembled, in the bay", 11, "middle", QUIET)
    for i, line in enumerate(spec["board"]):
        d.text(bx + 44, by + 150 + i * 22, line, 12, fill=INK)
    # connector tags on the board edge
    tags = [("J1", bx + 6, 624, "start"), ("TB2", 590, by + 16, "middle"), ("J3", 640, by + 16, "middle"),
            ("J5", 740, by + 16, "middle"), ("J6", 800, by + 16, "middle"), ("J4", 860, by + 16, "middle"),
            ("J11", bx + 6, 704, "start"), ("J8", 640, by + bh - 6, "middle"),
            ("J9", 800, by + bh - 6, "middle")]
    if "J12" in has:
        tags.append(("J12", bx + 6, 804, "start"))
    tags += [(cid, bx + bw - 6, y + 4, "end") for cid, y in right]
    for t, x, y, a in tags:
        d.text(x, y, t, 10.5, a, QUIET, "600")

    d.box(40, 595, 90, 50, "12 V lead", "XT60-F plug")
    d.text(40, 680, "From the shared supply:", 11, fill=QUIET)
    d.text(40, 696, "14 AWG red/black, 15 A", 11, fill=QUIET)
    d.text(40, 712, "fuse at its fuse block.", 11, fill=QUIET)
    d.text(40, 728, "F1 15 A is on the board", 11, fill=QUIET)

    # heater circuit
    d.rect(280, 130, 200, 200, "white", "#bf8700", 1.4, 8)
    d.text(380, 150, "Heater circuit", 12, "middle", INK, "700")
    for i, (n, s) in enumerate([("TH1 KSD301", "85 °C NC, on the back wall"), ("TF1 92 °C fuse", "next to TH1"), ("HT1 PTC heater", "12 V 150 W, in the duct")]):
        d.box(300, 162 + i * 54, 160, 42, n, s)
        if i < 2:
            d.o.append(f"<path d='M380 {204 + i * 54}V{216 + i * 54}' stroke='{COL['red']}' stroke-width='2.2'/>")
    d.box(520, 250, 120, 50, "M1 blower", "5015 12 V")
    d.box(680, 250, 120, 50, "SB1 SHT40 board", "chamber air")
    d.box(840, 250, 120, 50, "SB2 DS18B20 board", "heater outlet")
    d.box(1020, 126, 120, 50, "M2 exhaust fan", "4010 12 V, lid")
    d.text(1080, 120, "slack loop at the hinge", 10.5, "middle", QUIET)

    d.box(270, 676, 100, 48, "LC1", "5 kg cell" + (", reel A" if "J12" in has else ""))
    if "J12" in has:
        d.box(270, 776, 100, 48, "LC2", "5 kg cell, reel B")
    d.box(580, 1110, 120, 48, "U6 OLED", "front panel")
    d.box(740, 1110, 120, 48, "SW1 button", "front panel")

    pod_parts = {"J13": ("S1 lane A", "K1C runout sensor"), "J14": ("S2 lane B", "K1C runout sensor"),
                 "J15": ("U13 BTT SFS V2", "runout + motion"), "J16": ("M3 feeder A", "K1C extruder motor"),
                 "J17": ("M4 feeder B", "K1C extruder motor")}
    for cid, y in right:
        n, s = pod_parts[cid]
        d.box(1300, y - 25, 170, 50, n, s)

    # legend
    lx, ly = 1226, 1050 if "J16" in has else 900
    d.text(lx, ly, "Wire colours", 12, weight="700")
    legend = [l for l in LEGEND if l[0] != "motor" or "J16" in has]
    for i, (c, meaning) in enumerate(legend):
        yy = ly + 20 + i * 18
        d.o.append(f"<path d='M{lx} {yy - 4}h28' stroke='{COL[c]}' stroke-width='3'/>")
        d.text(lx + 36, yy, f"{c}: {meaning}", 11, fill=INK)
    d.save(ROOT / version / "wiring.svg")


def table(version, spec):
    rows = []
    for cid in spec["conns"]:
        title, kind, gauge, pins, dest, where, notes = CONN[cid]
        pin_txt = "".join(f"<div class=\"pin\">{i + 1}: {esc(sig)} <span class=\"wire wire-{c}\">{c}</span></div>" for i, (sig, c) in enumerate(pins))
        rows.append(f"<tr><td><strong>{cid}</strong><br>{esc(title)}</td><td>{esc(kind)}<br>{esc(gauge)}</td>"
                    f"<td>{pin_txt}</td><td>{esc(dest)}</td><td>{esc(where)}</td><td>{esc(notes)}</td></tr>")
    out = ('<div class="table-wrap"><table><thead><tr><th>Connector</th><th>Type, wire</th><th>Pins</th>'
           '<th>Goes to</th><th>Where</th><th>Notes</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>\n")
    (ROOT / version / "wiring-table.html").write_text(out, encoding="utf-8")
    print("wrote", ROOT / version / "wiring-table.html")


if __name__ == "__main__":
    for v, spec in VERSIONS.items():
        diagram(v, spec)
        table(v, spec)
