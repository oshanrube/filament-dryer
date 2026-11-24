#!/usr/bin/env python3
"""Generate the dryer controller board: KiCad 7 schematic, project library and JLCPCB BOMs.

One board serves both dryer versions; the 1-roll build leaves the feeder parts off.
Every pin connects through a net label, so the netlist comes straight from the
table below. Run from the repo root:

    python3 pcb/tools/gen_kicad.py

Then check it with:  kicad-cli sch erc pcb/dryer-controller.kicad_sch
"""
import csv
import uuid
from pathlib import Path

from sexp import Sym, dump, find, first, parse

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "dryer-controller"
KICAD_SYMS = Path("/usr/share/kicad/symbols")
S = Sym


def uid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------- custom symbols and footprints
def box_symbol(name, ref, value, left, right, fp, width=15.24, desc=""):
    """Rectangle symbol; left/right = [(number, name, type)] top to bottom."""
    n = max(len(left), len(right))
    h = (n + 1) * 2.54
    top = h / 2
    body = [S("symbol"), f"{name}_0_1",
            [S("rectangle"), [S("start"), -width / 2, top], [S("end"), width / 2, -top],
             [S("stroke"), [S("width"), 0.254], [S("type"), S("default")]], [S("fill"), [S("type"), S("background")]]]]
    pins = [S("symbol"), f"{name}_1_1"]
    for side, plist in (("L", left), ("R", right)):
        for i, (num, pname, ptype) in enumerate(plist):
            y = top - 2.54 * (i + 1)
            x = -width / 2 - 2.54 if side == "L" else width / 2 + 2.54
            ang = 0 if side == "L" else 180
            pins.append([S("pin"), S(ptype), S("line"), [S("at"), round(x, 2), round(y, 2), ang], [S("length"), 2.54],
                         [S("name"), pname, [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]],
                         [S("number"), num, [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]]])
    return [S("symbol"), name, [S("in_bom"), S("yes")], [S("on_board"), S("yes")],
            prop("Reference", ref, 0, top + 1.27), prop("Value", value, 0, -top - 1.27),
            prop("Footprint", fp, 0, 0, hide=True), prop("Datasheet", "", 0, 0, hide=True),
            prop("Description", desc, 0, 0, hide=True), body, pins]


def prop(key, val, x, y, hide=False, angle=0, justify=None):
    eff = [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]
    if justify:
        eff.append([S("justify"), S(justify)])
    if hide:
        eff.append(S("hide"))
    return [S("property"), key, val, [S("at"), x, y, angle], eff]


CUSTOM = {
    "ESP32-C3_SuperMini": box_symbol(
        "ESP32-C3_SuperMini", "U", "ESP32-C3 SuperMini",
        [("1", "5V", "power_in"), ("2", "GND", "power_in"), ("3", "3V3", "power_out"), ("4", "GPIO4", "bidirectional"),
         ("5", "GPIO3", "bidirectional"), ("6", "GPIO2", "bidirectional"), ("7", "GPIO1", "bidirectional"), ("8", "GPIO0", "bidirectional")],
        [("9", "GPIO5", "bidirectional"), ("10", "GPIO6", "bidirectional"), ("11", "GPIO7", "bidirectional"), ("12", "GPIO8", "bidirectional"),
         ("13", "GPIO9", "bidirectional"), ("14", "GPIO10", "bidirectional"), ("15", "GPIO20", "bidirectional"), ("16", "GPIO21", "bidirectional")],
        "dryer:ESP32-C3_SuperMini_Socket", 17.78, "ESP32-C3 SuperMini on two 1x8 female headers"),
    "TMC2209_StepStick": box_symbol(
        "TMC2209_StepStick", "U", "TMC2209 StepStick",
        [("1", "EN", "input"), ("2", "MS1", "input"), ("3", "MS2", "input"), ("4", "PDN/UART", "passive"), ("5", "PDN/UART", "passive"),
         ("6", "CLK", "passive"), ("7", "STEP", "input"), ("8", "DIR", "input")],
        [("16", "VM", "power_in"), ("15", "GND", "power_in"), ("14", "2B", "output"), ("13", "2A", "output"), ("12", "1A", "output"),
         ("11", "1B", "output"), ("10", "VIO", "power_in"), ("9", "GND", "power_in")],
        "Module:Pololu_Breakout-16_15.2x20.3mm", 17.78, "TMC2209 StepStick module in two 1x8 female headers; check pins 4-6 on your module"),
    "UCC27517": box_symbol(
        "UCC27517", "U", "UCC27517DBV",
        [("1", "VDD", "power_in"), ("3", "IN+", "input"), ("4", "IN-", "input")],
        [("5", "OUT", "output"), ("2", "GND", "power_in")],
        "Package_TO_SOT_SMD:SOT-23-5", 12.7, "4 A low-side gate driver, TI UCC27517 (DBV)"),
}


def supermini_footprint():
    """Two 1x8 rows, 2.54 mm pitch, 15.24 mm apart (measure your board!)."""
    pads = []
    left = ["1", "2", "3", "4", "5", "6", "7", "8"]
    right = ["9", "10", "11", "12", "13", "14", "15", "16"]
    for i, n in enumerate(left):
        pads.append(f'  (pad "{n}" thru_hole {"rect" if n == "1" else "oval"} (at 0 {i * 2.54:.2f}) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask"))')
    for i, n in enumerate(right):
        pads.append(f'  (pad "{n}" thru_hole oval (at 15.24 {i * 2.54:.2f}) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask"))')
    x0, y0, x1, y1 = -1.38, -4.0, 16.62, 18.52
    return "\n".join([
        '(footprint "ESP32-C3_SuperMini_Socket" (version 20221018) (generator gen_kicad)',
        '  (layer "F.Cu")',
        '  (descr "ESP32-C3 SuperMini (22.5 x 18 mm) on two 1x8 2.54 mm female headers, rows 15.24 mm apart. MEASURE YOUR BOARD before ordering.")',
        '  (attr through_hole)',
        '  (fp_text reference "REF**" (at 7.62 -5.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        '  (fp_text value "ESP32-C3_SuperMini" (at 7.62 20) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
        '  (fp_text user "USB" (at 7.62 -2.6) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        f'  (fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
        f'  (fp_rect (start {x0 - 0.25} {y0 - 0.25}) (end {x1 + 0.25} {y1 + 0.25}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        *pads,
        ")",
        "",
    ])


# ---------------------------------------------------------------- library symbols
_LIBS = {}


def lib_symbol(lib_id):
    """Return a flattened copy of a library symbol, named lib_id."""
    lib, name = lib_id.split(":")
    if lib == "dryer":
        s = [x for x in CUSTOM[name]]
        s[1] = lib_id
        return s
    if lib not in _LIBS:
        _LIBS[lib] = parse((KICAD_SYMS / f"{lib}.kicad_sym").read_text())[0]
    root = _LIBS[lib]
    syms = {s[1]: s for s in find(root, "symbol")}
    s = syms[name]
    ext = first(s, "extends")
    if ext:
        parent = syms[ext[1]]
        out = [S("symbol"), lib_id]
        props = {p[1]: p for p in find(s, "property")}
        for e in parent[2:]:
            if isinstance(e, list) and e[0] == "property":
                out.append(props.pop(e[1], e))
            elif isinstance(e, list) and e[0] == "symbol":
                sub = list(e)
                sub[1] = sub[1].replace(ext[1], name, 1)
                out.append(sub)
            else:
                out.append(e)
        out.extend(props.values())
        out = [e for e in out if not (isinstance(e, list) and e[0] == "extends")]
        return out
    out = list(s)
    out[1] = lib_id
    return out


def pin_table(sym):
    pins = {}
    for sub in find(sym, "symbol"):
        for p in find(sub, "pin"):
            at = first(p, "at")
            pins[first(p, "number")[1]] = (float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0, p[1])
    return pins


# ---------------------------------------------------------------- the board
# variant: "all" = both builds, "2roll" = only the two-reel build
R0603, C0603, C0805 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric"
XH = {2: "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", 3: "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical",
      4: "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"}
XH_LCSC = {2: "C158012", 3: "C144394", 4: "C144395"}
TERM = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"

PARTS = []


def part(ref, lib_id, value, fp, lcsc, at, nets, variant="all", mpn="", note="", jlc=True):
    PARTS.append(dict(ref=ref, lib_id=lib_id, value=value, fp=fp, lcsc=lcsc, at=at, nets=nets,
                      variant=variant, mpn=mpn, note=note, jlc=jlc))


def R(ref, val, lcsc, at, a, b, variant="all"):
    part(ref, "Device:R", val, R0603, lcsc, at, {"1": a, "2": b}, variant, mpn={"C25804": "0603WAF1002T5E", "C23162": "0603WAF4701T5E",
         "C22775": "0603WAF1000T5E", "C21190": "0603WAF1001T5E", "C22859": "0603WAF100JT5E"}[lcsc])


def C(ref, val, lcsc, at, a, b, variant="all"):
    fp = C0805 if lcsc in ("C15850", "C45783") else C0603
    mpn = {"C14663": "CC0603KRX7R9BB104", "C15850": "CL21A106KAYNNNE", "C45783": "CL21A226MAQNNNE"}[lcsc]
    part(ref, "Device:C", val, fp, lcsc, at, {"1": a, "2": b}, variant, mpn=mpn)


def CP(ref, at, a, b, variant="all"):
    part(ref, "Device:C_Polarized", "100uF 25V", "Capacitor_SMD:CP_Elec_6.3x7.7", "C3008501", at, {"1": a, "2": b}, variant,
         mpn="EMVE250ARA101MF80G")


def CONN(ref, nets, at, variant="all", value=None):
    n = len(nets)
    part(ref, f"Connector_Generic:Conn_01x0{n}", value or f"XH-{n}", XH[n], XH_LCSC[n], at,
         {str(i + 1): net for i, net in enumerate(nets)}, variant, mpn=f"B{n}B-XH-A(LF)(SN)")


# --- 1. power in and 5 V buck
part("TB1", "Connector:Screw_Terminal_01x02", "12V IN", TERM, "C474952", (30.48, 58.42), {"1": "+12V", "2": "GND"},
     mpn="KF128-5.08-2P-AA", note="24 A terminal; 12 V feed from the XT60 and inline 15 A fuse")
CP("C1", (45.72, 60.96), "+12V", "GND")
C("C2", "100nF", "C14663", (58.42, 60.96), "+12V", "GND")
part("U2", "Regulator_Switching:AP63205WU", "AP63205WU-7", "Package_TO_SOT_SMD:TSOT-23-6", "C2071056", (106.68, 60.96),
     {"1": "+5V", "2": "+12V", "3": "+12V", "4": "GND", "5": "SW5V", "6": "BST5V"}, mpn="AP63205WU-7")
C("C3", "10uF 25V", "C15850", (71.12, 60.96), "+12V", "GND")
C("C4", "100nF", "C14663", (129.54, 45.72), "BST5V", "SW5V")
part("L1", "Device:L", "4.7uH", "Inductor_SMD:L_Changjiang_FNR4030S", "C5289366", (132.08, 60.96), {"1": "SW5V", "2": "+5V"},
     mpn="XRNR4030-4.7uH/M", note="4x4 mm; check pads against the XRNR4030 drawing")
C("C5", "22uF 25V", "C45783", (144.78, 60.96), "+5V", "GND")
C("C6", "22uF 25V", "C45783", (160.02, 60.96), "+5V", "GND")

# --- 2. controller
part("U1", "dryer:ESP32-C3_SuperMini", "ESP32-C3 SuperMini", "dryer:ESP32-C3_SuperMini_Socket", "C27438", (213.36, 66.04),
     {"1": "+5V", "2": "GND", "3": "+3V3", "4": "HEAT_IN", "5": "HXB_DT", "6": "ONEWIRE", "7": "HXA_DT", "8": "HX_SCK",
      "9": "BLOW_IN", "10": "EXH_IN", "11": "SCL", "12": "SDA", "13": None, "14": "STEP_A", "15": "STEP_B", "16": "MOTION_MCU"},
     mpn="2x 2.54-1*8P female header", note="Two C27438 1x8 sockets; the SuperMini itself plugs in (yours)", jlc=False)
R("R1", "4.7k", "C23162", (182.88, 104.14), "+3V3", "ONEWIRE")
R("R2", "4.7k", "C23162", (193.04, 104.14), "+3V3", "SCL")
R("R3", "4.7k", "C23162", (203.2, 104.14), "+3V3", "SDA")
R("R4", "1k", "C21190", (213.36, 104.14), "MOTION", "MOTION_MCU")

# --- 3. I/O expander
part("U3", "Interface_Expansion:MCP23017_SO", "MCP23017-E/SO", "Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm", "C47023", (309.88, 76.2),
     {"9": "+3V3", "10": "GND", "12": "SCL", "13": "SDA", "15": "GND", "16": "GND", "17": "GND", "18": "MCP_RST",
      "19": None, "20": None, "11": None, "14": None,
      "21": "LANE_A", "22": "LANE_B", "23": "MERGE", "24": "BTN", "25": "BUZ_IN", "26": "FEED_EN", "27": "FEED_DIR", "28": None,
      "1": None, "2": None, "3": None, "4": None, "5": None, "6": None, "7": None, "8": None}, mpn="MCP23017-E/SO")
C("C7", "100nF", "C14663", (279.4, 45.72), "+3V3", "GND")
R("R5", "10k", "C25804", (269.24, 45.72), "+3V3", "MCP_RST")
R("R6", "10k", "C25804", (355.6, 45.72), "+3V3", "FEED_EN")

# --- 4. heater switch (12 V gate drive)
part("U4", "dryer:UCC27517", "UCC27517DBVR", "Package_TO_SOT_SMD:SOT-23-5", "C99395", (60.96, 167.64),
     {"1": "+12V", "2": "GND", "3": "HEAT_IN", "4": "GND", "5": "GATE_DRV"}, mpn="UCC27517DBVR")
C("C8", "10uF 25V", "C15850", (30.48, 152.4), "+12V", "GND")
C("C9", "100nF", "C14663", (45.72, 152.4), "+12V", "GND")
R("R7", "10R", "C22859", (91.44, 152.4), "GATE_DRV", "HEAT_G")
R("R8", "10k", "C25804", (101.6, 185.42), "HEAT_G", "GND")
R("R9", "10k", "C25804", (30.48, 185.42), "HEAT_IN", "GND")
part("Q1", "Device:Q_NMOS_GDS", "AOD4184A", "Package_TO_SOT_SMD:TO-252-2", "C99124", (124.46, 170.18),
     {"1": "HEAT_G", "2": "HEATER_N", "3": "GND"}, mpn="AOD4184A", note="12.5 A heater: big copper pour on the drain tab, 2 oz copper")
part("TB2", "Connector:Screw_Terminal_01x02", "HEATER", TERM, "C474952", (149.86, 162.56), {"1": "+12V", "2": "HEATER_N"},
     mpn="KF128-5.08-2P-AA", note="Heater + via KSD301 and thermal fuse (in the harness)")

# --- 5. fans and buzzer
def low_side(n, gate_in, gnet, drain, x, y, rg, rpd, q):
    R(rg, "100R", "C22775", (x, y), gate_in, gnet)
    R(rpd, "10k", "C25804", (x + 10.16, y + 22.86), gnet, "GND")
    part(q, "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917", (x + 25.4, y + 2.54),
         {"1": gnet, "2": "GND", "3": drain}, mpn="AO3400A")


low_side(1, "BLOW_IN", "BLOW_G", "BLOW_N", 190.5, 160.02, "R10", "R11", "Q2")
part("D1", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", "C8598", (233.68, 147.32), {"1": "+12V", "2": "BLOW_N"}, mpn="B5819W SL")
CONN("J3", ["+12V", "BLOW_N"], (256.54, 162.56), value="BLOWER")
low_side(2, "EXH_IN", "EXH_G", "EXH_N", 190.5, 210.82, "R12", "R13", "Q3")
part("D2", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", "C8598", (233.68, 198.12), {"1": "+12V", "2": "EXH_N"}, mpn="B5819W SL")
CONN("J4", ["+12V", "EXH_N"], (256.54, 213.36), value="EXHAUST")
low_side(3, "BUZ_IN", "BUZ_G", "BUZ_N", 190.5, 261.62, "R14", "R15", "Q4")
part("BZ1", "Device:Buzzer", "KXG1205C", "Buzzer_Beeper:Buzzer_12x9.5RM7.6", "C1122355", (241.3, 254.0), {"1": "+5V", "2": "BUZ_N"},
     mpn="KXG1205C", note="5 V active buzzer, through-hole")

# --- 6. sensor, panel and scale connectors
CONN("J5", ["+3V3", "GND", "SCL", "SDA"], (335.28, 152.4), value="SHT40")
CONN("J6", ["+3V3", "GND", "ONEWIRE"], (335.28, 172.72), value="DS18B20")
CONN("J7", ["+3V3", "GND", "SCL", "SDA"], (335.28, 190.5), value="AHT20")
CONN("J8", ["+3V3", "GND", "SCL", "SDA"], (335.28, 210.82), value="OLED")
CONN("J9", ["BTN", "GND"], (335.28, 228.6), value="BUTTON")
CONN("J11", ["+3V3", "GND", "HX_SCK", "HXA_DT"], (386.08, 152.4), value="SCALE_A")
CONN("J12", ["+3V3", "GND", "HX_SCK", "HXB_DT"], (386.08, 172.72), "2roll", value="SCALE_B")
CONN("J13", ["+3V3", "GND", "LANE_A"], (386.08, 193.04), "2roll", value="LANE_A")
CONN("J14", ["+3V3", "GND", "LANE_B"], (386.08, 208.28), "2roll", value="LANE_B")
CONN("J15", ["+3V3", "GND", "MERGE", "MOTION"], (386.08, 226.06), value="BTT_SFS")

# --- 7. feeder drivers (2-roll only)
for k, (u, step, j, c, m, y) in enumerate((("U10", "STEP_A", "J16", "C10", "MA", 66.04), ("U11", "STEP_B", "J17", "C11", "MB", 132.08))):
    part(u, "dryer:TMC2209_StepStick", "TMC2209 StepStick", "Module:Pololu_Breakout-16_15.2x20.3mm", "C27438", (474.98, y),
         {"1": "FEED_EN", "2": "GND", "3": "GND", "4": None, "5": None, "6": None, "7": step, "8": "FEED_DIR",
          "16": "+12V", "15": "GND", "14": f"{m}_2B", "13": f"{m}_2A", "12": f"{m}_1A", "11": f"{m}_1B", "10": "+3V3", "9": "GND"},
         "2roll", mpn="2x 2.54-1*8P female header", note="Two C27438 sockets; the TMC2209 module plugs in", jlc=False)
    CP(c, (444.5, y), "+12V", "GND", "2roll")
    CONN(j, [f"{m}_1A", f"{m}_1B", f"{m}_2A", f"{m}_2B"], (520.7, y), "2roll", value=f"MOTOR_{'AB'[k]}")

# --- power nets: one power symbol + PWR_FLAG per rail, tied to the same-named labels
POWER = [("+12V", "power:+12V", (30.48, 330.2)), ("+5V", "power:+5V", (55.88, 330.2)),
         ("+3V3", "power:+3V3", (81.28, 330.2)), ("GND", "power:GND", (106.68, 340.36))]
FLAGS = ["+12V", "+5V", "GND"]

BLOCKS = [("1  12 V in, 5 V buck", 22, 30), ("2  Controller (ESP32-C3 SuperMini)", 170, 30), ("3  I/O expander", 262, 30),
          ("4  Heater switch, 12 V gate drive", 22, 130), ("5  Fans and buzzer (low-side)", 170, 130),
          ("6  Sensor, panel and scale connectors", 322, 130), ("7  Feeder drivers (2-roll build only)", 430, 30),
          ("Power rails", 22, 315)]


# ---------------------------------------------------------------- writers
def write_schematic():
    root_uuid = uid()
    used = sorted({p["lib_id"] for p in PARTS} | {lib for _, lib, _ in POWER} | {"power:PWR_FLAG"})
    lib_syms = {lid: lib_symbol(lid) for lid in used}
    body = []

    def label(net, x, y, ang):
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[ang]
        body.append([S("label"), net, [S("at"), round(x, 2), round(y, 2), ang], [S("fields_autoplaced")],
                     [S("effects"), [S("font"), [S("size"), 1.27, 1.27]], [S("justify"), S(just), S("bottom")]], [S("uuid"), uid()]])

    def instance(lib_id, ref, value, x, y, fields, pins, in_bom=True, dnp=False, extent=None):
        if lib_id in ("Device:R", "Device:C", "Device:C_Polarized", "Device:L"):
            props = [prop("Reference", ref, x + 2.54, y - 1.27, justify="left"), prop("Value", value, x + 2.54, y + 1.27, justify="left")]
        elif lib_id in ("Device:Q_NMOS_GDS", "Transistor_FET:AO3400A"):
            props = [prop("Reference", ref, x + 5.08, y - 1.27, justify="left"), prop("Value", value, x + 5.08, y + 1.27, justify="left")]
        elif lib_id == "Device:D_Schottky":
            props = [prop("Reference", ref, x, y - 3.81), prop("Value", value, x, y + 3.81)]
        elif extent:
            top, bottom, vertical_pins = extent
            dx, j = (5.08, "left") if vertical_pins else (0, None)
            props = [prop("Reference", ref, x + dx, round(y - top - (1.27 if dx else 3.81), 2), justify=j),
                     prop("Value", value, x + dx, round(y - bottom + (1.27 if dx else 3.81), 2), justify=j)]
        else:
            props = [prop("Reference", ref, x, y - 7.62), prop("Value", value, x, y + 7.62)]
        for k, v in fields.items():
            props.append(prop(k, v, x, y, hide=True))
        body.append([S("symbol"), [S("lib_id"), lib_id], [S("at"), x, y, 0], [S("unit"), 1],
                     [S("in_bom"), S("yes" if in_bom else "no")], [S("on_board"), S("yes")], [S("dnp"), S("yes" if dnp else "no")],
                     [S("uuid"), uid()], *props, *[[S("pin"), n, [S("uuid"), uid()]] for n in pins],
                     [S("instances"), [S("project"), PROJECT, [S("path"), "/" + root_uuid, [S("reference"), ref], [S("unit"), 1]]]]])

    for p in PARTS:
        x, y = p["at"]
        pins = pin_table(lib_syms[p["lib_id"]])
        fields = {"Footprint": p["fp"], "LCSC": p["lcsc"], "MPN": p["mpn"], "Build": "both" if p["variant"] == "all" else "2-roll only"}
        ys = [py for (_, py, _, _) in pins.values()]
        body_rects = [r for sub in find(lib_syms[p["lib_id"]], "symbol") for r in find(sub, "rectangle")]
        for r in body_rects:
            ys += [float(first(r, "start")[2]), float(first(r, "end")[2])]
        vertical = any(ang in (90, 270) for (_, _, ang, t) in pins.values() if t != "no_connect")
        instance(p["lib_id"], p["ref"], p["value"], x, y, fields, sorted(pins), extent=(max(ys), min(ys), vertical))
        for num, (px, py, ang, ptype) in pins.items():
            if num not in p["nets"]:
                raise SystemExit(f"{p['ref']} pin {num} has no net")
            net = p["nets"][num]
            sx, sy = x + px, y - py
            if ptype == "no_connect":
                continue
            if net is None:
                body.append([S("no_connect"), [S("at"), round(sx, 2), round(sy, 2)], [S("uuid"), uid()]])
            else:
                label(net, sx, sy, (ang + 180) % 360)
    for i, (net, lib_id, (x, y)) in enumerate(POWER):
        instance(lib_id, f"#PWR0{i + 1}", net, x, y, {}, ["1"], in_bom=False)
        label(net, x, y, 0)
    for i, net in enumerate(FLAGS):
        x, y = 152.4 + i * 25.4, 330.2
        instance("power:PWR_FLAG", f"#FLG0{i + 1}", "PWR_FLAG", x, y, {}, ["1"], in_bom=False)
        label(net, x, y, 0)
    for title, x, y in BLOCKS:
        body.append([S("text"), title, [S("at"), x, y, 0], [S("effects"), [S("font"), [S("size"), 2.54, 2.54], S("bold")], [S("justify"), S("left"), S("bottom")]], [S("uuid"), uid()]])
    notes = ["One board for both dryers. 1-roll build: leave off U10, U11, C10, C11, J12, J13, J14, J16, J17.",
             "U1 SuperMini: measure the header row spacing of your board; the footprint assumes 15.24 mm.",
             "U10/U11 StepStick pins 4-6 differ between TMC2209 modules: they are left unconnected here.",
             "Heater path TB1 -> TB2 -> Q1 carries 12.5 A: wide pours, 2 oz copper, copper area under Q1."]
    for i, t in enumerate(notes):
        body.append([S("text"), t, [S("at"), 260, 330.2 + i * 6, 0], [S("effects"), [S("font"), [S("size"), 1.8, 1.8]], [S("justify"), S("left"), S("bottom")]], [S("uuid"), uid()]])

    sch = [S("kicad_sch"), [S("version"), 20230121], [S("generator"), S("gen_kicad")], [S("uuid"), root_uuid], [S("paper"), "A2"],
           [S("title_block"), [S("title"), "Filament dryer controller board"], [S("date"), "2026-11-24"], [S("rev"), "1"],
            [S("company"), "github.com/oshanrube/filament-dryer"],
            [S("comment"), 1, "Generated by pcb/tools/gen_kicad.py - edit the generator, not this file"]],
           [S("lib_symbols"), *lib_syms.values()], *body,
           [S("sheet_instances"), [S("path"), "/", [S("page"), "1"]]]]
    (ROOT / f"{PROJECT}.kicad_sch").write_text(dump(sch) + "\n")


def write_project_files():
    (ROOT / f"{PROJECT}.kicad_pro").write_text('{\n  "meta": {"filename": "%s.kicad_pro", "version": 1},\n  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},\n  "sheets": [],\n  "text_variables": {}\n}\n' % PROJECT)
    lib = [S("kicad_symbol_lib"), [S("version"), 20220914], [S("generator"), S("gen_kicad")], *CUSTOM.values()]
    (ROOT / "dryer.kicad_sym").write_text(dump(lib) + "\n")
    (ROOT / "dryer.pretty").mkdir(exist_ok=True)
    (ROOT / "dryer.pretty" / "ESP32-C3_SuperMini_Socket.kicad_mod").write_text(supermini_footprint())
    (ROOT / "sym-lib-table").write_text('(sym_lib_table\n  (lib (name "dryer")(type "KiCad")(uri "${KIPRJMOD}/dryer.kicad_sym")(options "")(descr "Filament dryer parts"))\n)\n')
    (ROOT / "fp-lib-table").write_text('(fp_lib_table\n  (lib (name "dryer")(type "KiCad")(uri "${KIPRJMOD}/dryer.pretty")(options "")(descr "Filament dryer footprints"))\n)\n')


def write_boms():
    (ROOT / "jlcpcb").mkdir(exist_ok=True)
    for build, keep in (("2-roll", {"all", "2roll"}), ("1-roll", {"all"})):
        groups = {}
        hand = [p for p in PARTS if p["variant"] in keep and not p["jlc"]]
        with (ROOT / "jlcpcb" / f"hand-fit-{build}.csv").open("w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["Designator", "Part", "LCSC Part #", "Qty", "Note"])
            for p in hand:
                w.writerow([p["ref"], "2.54 mm 1x8 female header", p["lcsc"], 2, p["note"]])
        for p in PARTS:
            if p["variant"] not in keep or not p["jlc"]:
                continue
            key = (p["lcsc"], p["fp"])
            groups.setdefault(key, []).append(p)
        rows = []
        for (lcsc, fp), ps in groups.items():
            refs = [p["ref"] for p in ps]
            qty = len(refs)
            values = {p["value"] for p in ps}
            value = values.pop() if len(values) == 1 else ps[0]["mpn"]
            rows.append({"Comment": value,
                         "Designator": ",".join(sorted(refs, key=lambda r: (r.rstrip("0123456789"), int("0" + r[len(r.rstrip("0123456789")):])))),
                         "Footprint": fp.split(":")[1], "LCSC Part #": lcsc, "Qty": qty, "MPN": ps[0]["mpn"].replace("2x ", ""),
                         "Note": ps[0]["note"]})
        rows.sort(key=lambda r: (r["Designator"].rstrip("0123456789,"), r["Designator"]))
        with (ROOT / "jlcpcb" / f"bom-{build}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint", "LCSC Part #", "Qty", "MPN", "Note"], lineterminator="\n")
            w.writeheader(); w.writerows(rows)
        print(f"wrote jlcpcb/bom-{build}.csv ({len(rows)} lines, {sum(r['Qty'] for r in rows)} parts)")


def export():
    """PDF and SVG of the schematic via kicad-cli (KiCad 7+), if it is installed."""
    import shutil, subprocess
    if not shutil.which("kicad-cli"):
        print("kicad-cli not found: skipped PDF/SVG export")
        return
    out = ROOT / "export"
    out.mkdir(exist_ok=True)
    sch = str(ROOT / f"{PROJECT}.kicad_sch")
    subprocess.run(["kicad-cli", "sch", "export", "pdf", "-o", str(out / f"{PROJECT}.pdf"), sch], check=True, capture_output=True)
    subprocess.run(["kicad-cli", "sch", "export", "svg", "-o", str(out), sch], check=True, capture_output=True)
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(out / f"{PROJECT}.net"), sch], check=True, capture_output=True)
    print("wrote", out)


if __name__ == "__main__":
    write_project_files()
    write_schematic()
    write_boms()
    print("wrote", ROOT / f"{PROJECT}.kicad_sch")
    export()
