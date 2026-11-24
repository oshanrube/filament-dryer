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
KICAD_FPS = Path("/usr/share/kicad/footprints")
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
    "ESP32-C3-WROOM-02": box_symbol(
        "ESP32-C3-WROOM-02", "U", "ESP32-C3-WROOM-02-N4",
        [("1", "3V3", "power_in"), ("2", "EN", "input"), ("18", "IO0", "bidirectional"), ("17", "IO1", "bidirectional"),
         ("16", "IO2", "bidirectional"), ("15", "IO3", "bidirectional"), ("3", "IO4", "bidirectional"), ("4", "IO5", "bidirectional"),
         ("5", "IO6", "bidirectional"), ("9", "GND", "power_in")],
        [("6", "IO7", "bidirectional"), ("7", "IO8", "bidirectional"), ("8", "IO9", "bidirectional"), ("10", "IO10", "bidirectional"),
         ("11", "RXD/IO20", "bidirectional"), ("12", "TXD/IO21", "bidirectional"), ("13", "IO18/USB_D-", "bidirectional"),
         ("14", "IO19/USB_D+", "bidirectional"), ("19", "GND", "passive")],
        "RF_Module:ESP32-C3-WROOM-02", 25.4, "Espressif ESP32-C3-WROOM-02 Wi-Fi module, 4 MB flash, PCB antenna; pin table from its datasheet, Table 3-1"),
    "TMC2209-LA": box_symbol(
        "TMC2209-LA", "U", "TMC2209-LA-T",
        [("2", "~{EN}", "input"), ("16", "STEP", "input"), ("19", "DIR", "input"), ("9", "MS1/AD0", "input"), ("10", "MS2/AD1", "input"),
         ("14", "~{PD}/UART", "bidirectional"), ("7", "SPREAD", "input"), ("13", "CLK", "input"), ("20", "STDBY", "input"),
         ("11", "DIAG", "output"), ("12", "INDEX", "output"), ("25", "NC", "passive"), ("15", "VCC_IO", "power_in"),
         ("3", "GND", "power_in"), ("18", "GND", "passive"), ("29", "EP/GND", "passive")],
        [("22", "VS", "power_in"), ("28", "VS", "passive"), ("6", "VCP", "output"), ("4", "CPO", "input"), ("5", "CPI", "input"),
         ("8", "5VOUT", "power_out"), ("17", "VREF", "passive"), ("24", "OA1", "output"), ("21", "OA2", "output"),
         ("26", "OB1", "output"), ("1", "OB2", "output"), ("23", "BRA", "input"), ("27", "BRB", "input")],
        "Package_DFN_QFN:QFN-28-1EP_5x5mm_P0.5mm_EP3.75x3.75mm_ThermalVias", 20.32,
        "ADI Trinamic TMC2209 stepper driver, QFN-28 5x5; pin numbers as KiCad's TMC2209-LA symbol"),
    "UCC27517": box_symbol(
        "UCC27517", "U", "UCC27517DBV",
        [("1", "VDD", "power_in"), ("3", "IN+", "input"), ("4", "IN-", "input")],
        [("5", "OUT", "output"), ("2", "GND", "power_in")],
        "Package_TO_SOT_SMD:SOT-23-5", 12.7, "4 A low-side gate driver, TI UCC27517 (DBV)"),
}


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


def part(ref, lib_id, value, fp, lcsc, at, nets, variant="all", mpn="", note="", jlc=True, bom=True):
    """bom=False: copper only (wire pads), nothing to buy or place."""
    PARTS.append(dict(ref=ref, lib_id=lib_id, value=value, fp=fp, lcsc=lcsc, at=at, nets=nets,
                      variant=variant, mpn=mpn, note=note, jlc=jlc, bom=bom))


def R(ref, val, lcsc, at, a, b, variant="all"):
    part(ref, "Device:R", val, R0603, lcsc, at, {"1": a, "2": b}, variant, mpn={"C25804": "0603WAF1002T5E", "C23162": "0603WAF4701T5E",
         "C22775": "0603WAF1000T5E", "C21190": "0603WAF1001T5E", "C22859": "0603WAF100JT5E", "C23186": "0603WAF5101T5E",
         "C4184": "0603WAF2002T5E", "C25981": "0603WAF8201T5E", "C23153": "0603WAF3902T5E"}[lcsc])


def C(ref, val, lcsc, at, a, b, variant="all"):
    fp = C0805 if lcsc in ("C15850", "C45783") else C0603
    mpn = {"C14663": "CC0603KRX7R9BB104", "C15850": "CL21A106KAYNNNE", "C45783": "CL21A226MAQNNNE", "C15849": "CL10A105KB8NNNC",
           "C21122": "CL10B223KB8NNNC", "C23630": "CL10A225KO8NNNC"}[lcsc]
    part(ref, "Device:C", val, fp, lcsc, at, {"1": a, "2": b}, variant, mpn=mpn)


def CP(ref, at, a, b, variant="all"):
    part(ref, "Device:C_Polarized", "100uF 25V", "Capacitor_SMD:CP_Elec_6.3x7.7", "C3008501", at, {"1": a, "2": b}, variant,
         mpn="EMVE250ARA101MF80G")


def CONN(ref, nets, at, variant="all", value=None):
    n = len(nets)
    part(ref, f"Connector_Generic:Conn_01x0{n}", value or f"XH-{n}", XH[n], XH_LCSC[n], at,
         {str(i + 1): net for i, net in enumerate(nets)}, variant, mpn=f"B{n}B-XH-A(LF)(SN)")


# --- 1. power in and 5 V buck
part("J1", "Connector_Generic:Conn_01x02", "XT60PW-M", "Connector_AMASS:AMASS_XT60PW-M_1x02_P7.20mm_Horizontal", "C98732", (33.02, 66.04),
     {"1": "GND", "2": "+12V_IN"}, mpn="XT60PW-M",
     note="12 V in at the board edge, through the base wall; the lead from the supply has an XT60-F plug. Pad 1 = -, pad 2 = + (footprint silkscreen)")
part("F1", "Device:Fuse", "ATO fuse holder", "Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165", "C207061", (40.64, 45.72),
     {"1": "+12V_IN", "2": "+12V"}, mpn="178.6165.0002",
     note="ATO blade fuse holder; fit a 15 A ATO fuse (Littelfuse 0287015.PXCN, LCSC C142684), ordered loose")
CP("C1", (55.88, 60.96), "+12V", "GND")
C("C2", "100nF", "C14663", (68.58, 60.96), "+12V", "GND")
part("U2", "Regulator_Switching:AP63205WU", "AP63205WU-7", "Package_TO_SOT_SMD:TSOT-23-6", "C2071056", (106.68, 60.96),
     {"1": "+5V", "2": "+12V", "3": "+12V", "4": "GND", "5": "SW5V", "6": "BST5V"}, mpn="AP63205WU-7")
C("C3", "10uF 25V", "C15850", (81.28, 60.96), "+12V", "GND")
C("C4", "100nF", "C14663", (129.54, 45.72), "BST5V", "SW5V")
part("L1", "Device:L", "4.7uH", "Inductor_SMD:L_Changjiang_FNR4030S", "C5289366", (132.08, 60.96), {"1": "SW5V", "2": "+5V"},
     mpn="XRNR4030-4.7uH/M", note="4x4 mm; check pads against the XRNR4030 drawing")
C("C5", "22uF 25V", "C45783", (144.78, 60.96), "+5V", "GND")
C("C6", "22uF 25V", "C45783", (160.02, 60.96), "+5V", "GND")

# --- 2. controller
part("U1", "dryer:ESP32-C3-WROOM-02", "ESP32-C3-WROOM-02-N4", "RF_Module:ESP32-C3-WROOM-02", "C2934560", (213.36, 66.04),
     {"1": "+3V3", "2": "EN", "18": "HX_SCK", "17": "HXA_DT", "16": "ONEWIRE", "15": "HXB_DT", "3": "HEAT_IN", "4": "BLOW_IN",
      "5": "EXH_IN", "9": "GND", "6": "SCL", "7": "SDA", "8": "BOOT", "10": "STEP_A", "11": "STEP_B", "12": "MOTION_MCU",
      "13": "USB_DN", "14": "USB_DP", "19": "GND"},
     mpn="ESP32-C3-WROOM-02-N4", note="Antenna end at the board edge, no copper under the antenna")
C("C14", "10uF 25V", "C15850", (182.88, 45.72), "+3V3", "GND")
C("C15", "100nF", "C14663", (193.04, 45.72), "+3V3", "GND")
R("R16", "10k", "C25804", (241.3, 45.72), "+3V3", "EN")
C("C16", "1uF", "C15849", (251.46, 45.72), "EN", "GND")
part("SW2", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "C318884", (236.22, 116.84), {"1": "EN", "2": "GND"},
     mpn="TS-1187A-B-A-B")
R("R17", "10k", "C25804", (233.68, 104.14), "+3V3", "BOOT")
part("SW3", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "C318884", (264.16, 116.84), {"1": "BOOT", "2": "GND"},
     mpn="TS-1187A-B-A-B", note="Hold BOOT, press RESET: download mode")

# --- 2b. USB (data only) and 3.3 V
part("J2", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", (294.64, 271.78),
     {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "A4": None, "A9": None, "B4": None, "B9": None,
      "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN", "A8": None, "B8": None, "S1": "GND"},
     mpn="TYPE-C-31-M-12", note="Programming and logs (USB serial/JTAG). Data only: VBUS is not connected, so plug in 12 V while flashing")
R("R18", "5.1k", "C23186", (330.2, 279.4), "CC1", "GND")
R("R19", "5.1k", "C23186", (340.36, 279.4), "CC2", "GND")
part("U12", "Regulator_Linear:AMS1117-3.3", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", "C6186", (386.08, 266.7),
     {"1": "GND", "2": "+3V3", "3": "+5V"}, mpn="AMS1117-3.3", note="3.3 V for the module, MCP23017, sensors and logic (up to ~0.4 A peak)")
C("C12", "10uF 25V", "C15850", (363.22, 279.4), "+5V", "GND")
C("C13", "22uF 25V", "C45783", (406.4, 279.4), "+3V3", "GND")
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
part("TB2", "Connector:Screw_Terminal_01x02", "HEATER", TERM, "C474952", (149.86, 162.56), {"1": "HEATER_N", "2": "+12V"},
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
CONN("J8", ["+3V3", "GND", "SCL", "SDA"], (335.28, 210.82), value="OLED")
CONN("J9", ["BTN", "GND"], (335.28, 228.6), value="BUTTON")
CONN("J11", ["EXC_A", "GND", "LCA_N", "LCA_P"], (386.08, 149.86), value="LOAD_CELL_A")
CONN("J12", ["EXC_B", "GND", "LCB_N", "LCB_P"], (386.08, 170.18), "2roll", value="LOAD_CELL_B")
CONN("J13", ["+3V3", "GND", "LANE_A"], (386.08, 190.5), "2roll", value="LANE_A")
CONN("J14", ["+3V3", "GND", "LANE_B"], (386.08, 208.28), "2roll", value="LANE_B")
CONN("J15", ["+3V3", "GND", "MERGE", "MOTION"], (386.08, 228.6), value="BTT_SFS")

# --- 6b. bay temperature + humidity, on the board (I2C 0x45; the chamber SHT40 is 0x44)
part("U13", "Sensor_Humidity:SHT4x", "SHT40-BD1B-R2", "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad", "C7461849",
     (370.84, 106.68), {"1": "SDA", "2": "SCL", "3": "+3V3", "4": "GND"}, mpn="SHT40-BD1B-R2",
     note="Bay sensor, address 0x45: place at a board edge away from U2, U12, U10, U11, with a slot around it")
C("C38", "100nF", "C14663", (391.16, 106.68), "+3V3", "GND")

# --- 9. sensor boards: small boards broken off the main panel, wired back to J5 and J6
part("U14", "Sensor_Humidity:SHT4x", "SHT40-AD1B-R2", "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad", "C2909890",
     (45.72, 388.62), {"1": "SB1_SDA", "2": "SB1_SCL", "3": "SB1_3V3", "4": "SB1_GND"}, mpn="SHT40-AD1B-R2",
     note="Sensor board SB1 (chamber air), address 0x44")
C("C37", "100nF", "C14663", (68.58, 388.62), "SB1_3V3", "SB1_GND")
part("J18", "Connector_Generic:Conn_01x04", "SB1 WIRES", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "", (93.98, 388.62),
     {"1": "SB1_3V3", "2": "SB1_GND", "3": "SB1_SCL", "4": "SB1_SDA"}, note="Wire pads, same order as J5", bom=False)
part("U15", "Sensor_Temperature:DS18B20Z", "DS18B20Z", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C695837", (139.7, 388.62),
     {"1": None, "2": None, "3": "SB2_3V3", "4": "SB2_DQ", "5": "SB2_GND", "6": None, "7": None, "8": None}, mpn="DS18B20Z(UMW)",
     note="Sensor board SB2 (heater outlet air)")
C("C39", "100nF", "C14663", (167.64, 388.62), "SB2_3V3", "SB2_GND")
part("J19", "Connector_Generic:Conn_01x03", "SB2 WIRES", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "", (193.04, 388.62),
     {"1": "SB2_3V3", "2": "SB2_GND", "3": "SB2_DQ"}, note="Wire pads, same order as J6", bom=False)

# --- 7. scales: HX711 on the board, load cells straight into J11/J12
for u, q, rs, cs, k, dt, x, y, var in (("U7", "Q5", ("R20", "R21"), ("C17", "C18", "C19", "C20", "C21"), "A", "HXA_DT", 452.12, 246.38, "all"),
                                       ("U8", "Q6", ("R22", "R23"), ("C22", "C23", "C24", "C25", "C26"), "B", "HXB_DT", 538.48, 246.38, "2roll")):
    exc, vfb, base = f"EXC_{k}", f"VFB_{k}", f"HXBASE_{k}"
    part(u, "Analog_ADC:HX711", "HX711", "Package_SO:SOP-16_3.9x9.9mm_P1.27mm", "C43656", (x, y),
         {"1": "+5V", "2": base, "3": exc, "4": vfb, "5": "GND", "6": f"VBG_{k}", "7": f"LC{k}_N", "8": f"LC{k}_P",
          "9": None, "10": None, "11": "HX_SCK", "12": dt, "13": None, "14": "GND", "15": "GND", "16": "+3V3"},
         var, mpn="HX711", note="Load-cell ADC; 10 samples/s, internal oscillator")
    part(q, "Device:Q_PNP_BEC", "S8550", "Package_TO_SOT_SMD:SOT-23", "C105432", (x - 27.94, y - 30.48), {"1": base, "2": "+5V", "3": exc},
         var, mpn="S8550 (RANGE:120-200)", note="Excitation regulator pass transistor (AVDD = 4.3 V)")
    R(rs[0], "20k", "C4184", (x + 20.32, y - 30.48), exc, vfb, var)
    R(rs[1], "8.2k", "C25981", (x + 33.02, y - 30.48), vfb, "GND", var)
    C(cs[0], "10uF 25V", "C15850", (x - 30.48, y + 30.48), exc, "GND", var)
    C(cs[1], "100nF", "C14663", (x - 15.24, y + 30.48), exc, "GND", var)
    C(cs[2], "100nF", "C14663", (x - 2.54, y + 30.48), f"VBG_{k}", "GND", var)
    C(cs[3], "100nF", "C14663", (x + 10.16, y + 30.48), "+5V", "GND", var)
    C(cs[4], "100nF", "C14663", (x + 22.86, y + 30.48), "+3V3", "GND", var)

# --- 8. feeder drivers (2-roll only): TMC2209 on the board, standalone, 1/8 step
for k, (u, step, j, cb, m, y, rr, cc) in enumerate((
        ("U10", "STEP_A", "J16", "C10", "MA", 66.04, ("R24", "R25", "R26", "R27"), ("C27", "C28", "C29", "C30", "C31")),
        ("U11", "STEP_B", "J17", "C11", "MB", 147.32, ("R28", "R29", "R30", "R31"), ("C32", "C33", "C34", "C35", "C36")))):
    v5, vref, cpi, cpo, vcp, bra, brb = (f"{m}_5V", f"{m}_VREF", f"{m}_CPI", f"{m}_CPO", f"{m}_VCP", f"{m}_BRA", f"{m}_BRB")
    part(u, "dryer:TMC2209-LA", "TMC2209-LA-T", "Package_DFN_QFN:QFN-28-1EP_5x5mm_P0.5mm_EP3.75x3.75mm_ThermalVias", "C2150710", (474.98, y),
         {"2": "FEED_EN", "16": step, "19": "FEED_DIR", "9": "GND", "10": "GND", "14": "GND", "7": "GND", "13": "GND", "20": "GND",
          "11": None, "12": None, "25": None, "15": "+3V3", "3": "GND", "18": "GND", "29": "GND",
          "22": "+12V", "28": "+12V", "6": vcp, "4": cpo, "5": cpi, "8": v5, "17": vref,
          "24": f"{m}_1A", "21": f"{m}_1B", "26": f"{m}_2A", "1": f"{m}_2B", "23": bra, "27": brb},
         "2roll", mpn="TMC2209-LA-T", note="Exposed pad to GND with thermal vias into a ground pour")
    CP(cb, (431.8, y - 17.78), "+12V", "GND", "2roll")
    C(cc[0], "100nF", "C14663", (431.8, y + 2.54), "+12V", "GND", "2roll")
    C(cc[1], "22nF 50V", "C21122", (500.38, y - 27.94), cpo, cpi, "2roll")
    C(cc[2], "100nF", "C14663", (513.08, y - 27.94), vcp, "+12V", "2roll")
    C(cc[3], "2.2uF", "C23630", (525.78, y - 27.94), v5, "GND", "2roll")
    C(cc[4], "100nF", "C14663", (431.8, y + 22.86), "+3V3", "GND", "2roll")
    R(rr[0], "39k", "C23153", (500.38, y + 25.4), v5, vref, "2roll")
    R(rr[1], "10k", "C25804", (513.08, y + 25.4), vref, "GND", "2roll")
    for ref, net in ((rr[2], bra), (rr[3], brb)):
        part(ref, "Device:R", "0.11R 1%", "Resistor_SMD:R_1206_3216Metric", "C82532", (525.78 + (12.7 if ref == rr[3] else 0), y + 25.4),
             {"1": net, "2": "GND"}, "2roll", mpn="1206W4F110LT5E", note="Sense resistor: sets the current range")
    CONN(j, [f"{m}_1A", f"{m}_1B", f"{m}_2A", f"{m}_2B"], (556.26, y), "2roll", value=f"MOTOR_{'AB'[k]}")

# --- power nets: one power symbol + PWR_FLAG per rail, tied to the same-named labels
POWER = [("+12V", "power:+12V", (30.48, 330.2)), ("+5V", "power:+5V", (55.88, 330.2)),
         ("+3V3", "power:+3V3", (81.28, 330.2)), ("GND", "power:GND", (106.68, 340.36))]
FLAGS = ["+12V", "+5V", "GND"]

BLOCKS = [("1  12 V in (XT60, fuse), 5 V buck", 22, 30), ("2  Controller (ESP32-C3-WROOM-02)", 170, 30), ("3  I/O expander", 262, 30),
          ("4  Heater switch, 12 V gate drive", 22, 130), ("5  Fans and buzzer (low-side)", 170, 130),
          ("6  Sensor, panel and load-cell connectors", 322, 130), ("7  Scales: HX711 (U8 parts: 2-roll only)", 425, 205),
          ("8  Feeder drivers (2-roll build only)", 425, 30), ("2b  USB (data only) and 3.3 V", 280, 250),
          ("9  Sensor boards SB1, SB2 (break off; wired to J5, J6)", 22, 370), ("6b  Bay sensor", 345, 92),
          ("Power rails", 22, 315)]


# ---------------------------------------------------------------- writers
ROOT_UUID = uid()


def write_schematic():
    root_uuid = ROOT_UUID
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
        elif lib_id in ("Device:Q_NMOS_GDS", "Transistor_FET:AO3400A", "Device:Q_PNP_BEC"):
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
        sym_uuid = uid()
        body.append([S("symbol"), [S("lib_id"), lib_id], [S("at"), x, y, 0], [S("unit"), 1],
                     [S("in_bom"), S("yes" if in_bom else "no")], [S("on_board"), S("yes")], [S("dnp"), S("yes" if dnp else "no")],
                     [S("uuid"), sym_uuid], *props, *[[S("pin"), n, [S("uuid"), uid()]] for n in pins],
                     [S("instances"), [S("project"), PROJECT, [S("path"), "/" + root_uuid, [S("reference"), ref], [S("unit"), 1]]]]])
        return sym_uuid

    for p in PARTS:
        x, y = p["at"]
        pins = pin_table(lib_syms[p["lib_id"]])
        fields = {"Footprint": p["fp"], "LCSC": p["lcsc"], "MPN": p["mpn"], "Build": "both" if p["variant"] == "all" else "2-roll only"}
        if p["bom"]:
            fields.update({"Supplier": "LCSC", "Supplier Part": p["lcsc"], "Manufacturer Part": p["mpn"]})
        ys = [py for (_, py, _, _) in pins.values()]
        body_rects = [r for sub in find(lib_syms[p["lib_id"]], "symbol") for r in find(sub, "rectangle")]
        for r in body_rects:
            ys += [float(first(r, "start")[2]), float(first(r, "end")[2])]
        vertical = any(ang in (90, 270) for (_, _, ang, t) in pins.values() if t != "no_connect")
        p["uuid"] = instance(p["lib_id"], p["ref"], p["value"], x, y, fields, sorted(pins), in_bom=p["bom"], extent=(max(ys), min(ys), vertical))
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
    notes = ["One board for both dryers, every part assembled by JLCPCB. The 1-roll BOM leaves off the 2-roll-only parts (field Build).",
             "U1 antenna at the board edge: no copper, parts or traces under it. USB is data only: plug in 12 V while flashing.",
             "SB1 (U14, C37, J18) and SB2 (U15, C39, J19) are small boards on break-off tabs: their nets (SB1_*, SB2_*) reach the board only through the harness.",
             "U10/U11: 39k/10k on VREF = 1.0 V -> about 0.72 A RMS with 0.11 R sense resistors. Exposed pad to GND with vias.",
             "Heater path J1 -> F1 -> TB2 -> Q1 carries 12.5 A: wide pours, 2 oz copper, copper area under Q1."]
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
    old = ROOT / "dryer.pretty" / "ESP32-C3_SuperMini_Socket.kicad_mod"
    if old.exists():
        old.unlink()
    (ROOT / "sym-lib-table").write_text('(sym_lib_table\n  (lib (name "dryer")(type "KiCad")(uri "${KIPRJMOD}/dryer.kicad_sym")(options "")(descr "Filament dryer parts"))\n)\n')
    if (ROOT / "dryer.pretty").exists() and not any((ROOT / "dryer.pretty").iterdir()):
        (ROOT / "dryer.pretty").rmdir()
    # every footprint the board uses, copied into the project so it opens anywhere (KiCad, EasyEDA Pro import)
    import shutil
    libs = ROOT / "libs"
    if libs.exists():
        shutil.rmtree(libs)
    used = [p["fp"] for p in PARTS] + ["MountingHole:MountingHole_3.2mm_M3"]
    nicks = sorted({f.split(":")[0] for f in used})
    for f in used:
        nick, name = f.split(":")
        d = libs / f"{nick}.pretty"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(KICAD_FPS / f"{nick}.pretty" / f"{name}.kicad_mod", d / f"{name}.kicad_mod")
    (ROOT / "fp-lib-table").write_text("(fp_lib_table\n" + "".join(
        f'  (lib (name "{n}")(type "KiCad")(uri "${{KIPRJMOD}}/libs/{n}.pretty")(options "")(descr "Copied from KiCad 7 for this project"))\n'
        for n in nicks) + ")\n")


def write_boms():
    (ROOT / "jlcpcb").mkdir(exist_ok=True)
    for build, keep in (("2-roll", {"all", "2roll"}), ("1-roll", {"all"})):
        groups = {}
        if any(p["variant"] in keep and p["bom"] and not p["jlc"] for p in PARTS):
            raise SystemExit("every part is meant to be assembled by JLCPCB")
        old = ROOT / "jlcpcb" / f"hand-fit-{build}.csv"
        if old.exists():
            old.unlink()
        for p in PARTS:
            if p["variant"] not in keep or not p["jlc"] or not p["bom"]:
                continue
            key = (p["lcsc"], p["fp"])
            groups.setdefault(key, []).append(p)
        rows = []
        for (lcsc, fp), ps in groups.items():
            refs = [p["ref"] for p in ps]
            qty = len(refs)
            values = {p["value"] for p in ps}
            value = values.pop() if len(values) == 1 and not ps[0]["lib_id"].startswith("Connector_Generic") else ps[0]["mpn"]
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


def write_pcb():
    """Unrouted starting board: every footprint, with its nets, linked to the schematic symbols. Layout is still to do."""
    try:
        import pcbnew
    except ImportError:
        print("pcbnew Python module not found: skipped the .kicad_pcb")
        return
    from sexp import parse as _parse
    netlist = _parse((ROOT / "export" / f"{PROJECT}.net").read_text())[0]
    pin_net = {}
    for n in find(first(netlist, "nets"), "net"):
        name = first(n, "name")[1]
        if name.startswith("unconnected-"):
            continue
        for node in find(n, "node"):
            pin_net[(first(node, "ref")[1], first(node, "pin")[1])] = name
    board = pcbnew.BOARD()
    nets = {}
    for name in sorted(set(pin_net.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
    x, y, row_h, row_w = 0.0, 0.0, 0.0, 180.0
    for p in PARTS:
        nick, name = p["fp"].split(":")
        fp = pcbnew.FootprintLoad(str(ROOT / "libs" / f"{nick}.pretty"), name)
        fp.SetFPID(pcbnew.LIB_ID(nick, name))
        fp.SetReference(p["ref"])
        fp.SetValue(p["value"])
        fp.SetPath(pcbnew.KIID_PATH(f"/{ROOT_UUID}/{p['uuid']}"))
        if p["bom"]:
            for k, v in (("LCSC", p["lcsc"]), ("Supplier Part", p["lcsc"]), ("MPN", p["mpn"])):
                fp.SetProperty(k, v)
        for pad in fp.Pads():
            net = pin_net.get((p["ref"], pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        bb = fp.GetBoundingBox(False, False)
        w, h = pcbnew.ToMM(bb.GetWidth()) + 2, pcbnew.ToMM(bb.GetHeight()) + 2
        if x + w > row_w:
            x, y, row_h = 0.0, y + row_h, 0.0
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100 + x + w / 2), pcbnew.FromMM(50 + y + h / 2)))
        bb2 = fp.GetBoundingBox(False, False)
        fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(100 + x) - bb2.GetX(), pcbnew.FromMM(50 + y) - bb2.GetY()))
        x += w
        row_h = max(row_h, h)
        board.Add(fp)
    try:
        import place_pcb
    except ImportError:
        place_pcb = None
    if place_pcb:
        place_pcb.layout(board)
    pcbnew.SaveBoard(str(ROOT / f"{PROJECT}.kicad_pcb"), board)
    print("wrote", ROOT / f"{PROJECT}.kicad_pcb", f"({len(PARTS)} footprints, {len(nets)} nets, unrouted)")


def write_easyeda_zip():
    """The project as KiCad's 'Archive Project' would pack it: what EasyEDA Pro's KiCad import expects."""
    import zipfile
    out = ROOT / "easyeda" / f"{PROJECT}-kicad.zip"
    out.parent.mkdir(exist_ok=True)
    files = [f"{PROJECT}.kicad_pro", f"{PROJECT}.kicad_sch", f"{PROJECT}.kicad_pcb", "sym-lib-table", "fp-lib-table", "dryer.kicad_sym"]
    files += [str(f.relative_to(ROOT)) for f in sorted((ROOT / "libs").rglob("*.kicad_mod"))]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if (ROOT / f).exists():
                z.write(ROOT / f, f"{PROJECT}/{f}")
    print("wrote", out)


if __name__ == "__main__":
    write_project_files()
    write_schematic()
    write_boms()
    print("wrote", ROOT / f"{PROJECT}.kicad_sch")
    export()
    write_pcb()
    write_easyeda_zip()
