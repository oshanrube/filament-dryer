#!/usr/bin/env python3
"""Wiring drawings for the basic dryer controller (Wemos D1 Mini or ESP-01S, one T + RH probe, fan, heater).

Writes dumb/basic/wiring.svg (D1 Mini) and dumb/basic/wiring-esp01.svg (ESP-01S).  Run from the repo root:
    python3 dumb/basic/tools/gen_basic.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
from gen_dumb import Svg, RED, BLACK, ORANGE, YELLOW, BLUE, GREY  # noqa: E402

GREEN, PURPLE, BROWN = "#2e7d32", "#6a1b9a", "#8d6e63"


class Draw(Svg):
    def gnd(self, x, y):
        """Ground symbol hanging from (x, y)."""
        self.wire([(x, y), (x, y + 10)], BLACK, 2)
        for i, w in enumerate((16, 10, 4)):
            yy = y + 10 + i * 5
            self.wire([(x - w / 2, yy), (x + w / 2, yy)], BLACK, 2)

    def res_h(self, x1, x2, y, label, color, above=True):
        """Resistor between x1 and x2 on y, with its leads."""
        mid = (x1 + x2) / 2
        self.wire([(x1, y), (mid - 18, y)], color, 2)
        self.wire([(mid + 18, y), (x2, y)], color, 2)
        self.o.append(f'<rect x="{mid - 18}" y="{y - 6}" width="36" height="12" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        self.text(mid, y - 12 if above else y + 22, label, "p", "middle")

    def res_v(self, x, y1, y2, label, color, right=True):
        mid = (y1 + y2) / 2
        self.wire([(x, y1), (x, mid - 18)], color, 2)
        self.wire([(x, mid + 18), (x, y2)], color, 2)
        self.o.append(f'<rect x="{x - 6}" y="{mid - 18}" width="12" height="36" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        self.text(x + 12 if right else x - 12, mid + 4, label, "p", "start" if right else "end")

    def diode_v(self, x, y1, y2, label):
        """Diode on a vertical line, cathode at the top (y1)."""
        mid = (y1 + y2) / 2
        self.wire([(x, y1), (x, y2)], BLACK, 2)
        self.o.append(f'<path d="M{x - 9} {mid + 7} L{x + 9} {mid + 7} L{x} {mid - 7} Z" fill="#111"/>')
        self.wire([(x - 9, mid - 7), (x + 9, mid - 7)], BLACK, 2.4)
        self.text(x + 14, mid + 4, label, "p")

    def pin_top(self, x, y, label):
        self.o.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        self.text(x, y + 20, label, "p", "middle")

    def flag(self, x, y, label, color):
        """Net label pointing up from (x, y)."""
        self.wire([(x, y), (x, y - 14)], color, 2)
        self.wire([(x - 8, y - 14), (x + 8, y - 14)], color, 2)
        self.text(x, y - 20, label, "p", "middle")

    def pin_bottom(self, x, y, label):
        self.o.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        self.text(x, y - 10, label, "p", "middle")


def wiring(esp01=False):
    d = Draw(1360, 900)
    d.text(30, 36, "Basic dryer controller (ESP-01S): wiring" if esp01 else "Basic dryer controller (Wemos D1 Mini): wiring", "t")
    d.text(30, 58, "Fan and heater run while the box is above 15 % RH. The heater tapers from full power at 60 °C to off at 65 °C. "
                   "Crossing wires are not joined unless a dot is shown.", "v")
    TOP = 110

    # 12 V in, fuse, +12 V rail
    d.box(30, 80, 120, 60, "XT60 12 V in", "shared supply lead")
    d.wire([(150, TOP), (190, TOP)], RED)
    d.o.append(f'<rect x="190" y="{TOP - 9}" width="46" height="18" rx="3" fill="#fff" stroke="#111" stroke-width="1.4"/>')
    d.text(213, TOP - 16, "F1 15 A", "p", "middle")
    d.wire([(236, TOP), (1330, TOP)], RED)
    d.text(1330, TOP - 10, "+12 V", "v", "end")
    d.wire([(150, 130), (170, 130), (170, 150)], BLACK, 3); d.gnd(170, 150)

    # MP1584 buck: 12 V -> 5 V
    d.box(255, 170, 130, 110, "MP1584 buck", "set to 3.3 V first" if esp01 else "set to 5.0 V first")
    d.wire([(255, TOP), (255, 230)], RED, 2); d.dot(255, TOP, RED)
    d.wire([(255, 255), (235, 255), (235, 300)], BLACK, 2); d.gnd(235, 300)
    d.term(255, 230, "IN+"); d.term(255, 255, "IN−")
    d.term(385, 230, "OUT+", "end"); d.term(385, 255, "OUT−", "end")

    # D1 Mini
    if esp01:
        d.box(420, 170, 220, 260, "ESP-01S", "ESP8266, Wi-Fi switched off", "mod")
        d.term(440, 230, "3V3"); d.term(440, 255, "GND")
        d.term(620, 230, "GPIO3 (RX) fan", "end")
    else:
        d.box(420, 170, 220, 260, "Wemos D1 Mini", "ESP8266, reports over Wi-Fi", "mod")
        d.term(440, 230, "5V"); d.term(440, 255, "G")
        d.term(620, 230, "D6 (GPIO12) fan", "end")
    d.wire([(385, 230), (440, 230)], ORANGE, 2)
    d.text(412, 222, "3.3 V" if esp01 else "5 V", "p", "middle")
    d.wire([(385, 255), (440, 255)], BLACK, 2)
    d.dot(412, 255, BLACK); d.wire([(412, 255), (412, 300)], BLACK, 2); d.gnd(412, 300)
    if esp01:
        d.pin_bottom(460, 430, "3V3"); d.pin_bottom(520, 430, "GPIO2"); d.pin_bottom(600, 430, "GPIO0")
        lines = ["TX (GPIO1): serial log, 115200 baud", "no status LED: the on-board", "LED shares GPIO2 with the probe",
                 "EN and RST: pulled up on the", "ESP-01S (a plain ESP-01 needs", "10 kΩ from EN to 3V3)"]
    else:
        d.pin_bottom(460, 430, "3V3"); d.pin_bottom(520, 430, "D7"); d.pin_bottom(600, 430, "D5")
        lines = ["on-board LED (D4):", "on = heating", "slow blink = fan only", "short flash = dry, idle",
                 "fast blink = probe fault / too hot"]
    for i, s_ in enumerate(lines):
        d.text(530, 290 + i * 16, s_, "p", "middle")

    # probe: AM2301 (DHT21) or DHT22
    d.box(400, 590, 160, 100, "", "")
    d.text(480, 640, "T + RH probe", "r", "middle")
    d.text(480, 658, "AM2301 / DHT22", "p", "middle")
    d.text(480, 674, "in the chamber air", "p", "middle")
    d.pin_top(460, 590, "VCC"); d.pin_top(520, 590, "DATA")
    d.wire([(460, 430), (460, 590)], ORANGE, 2)
    d.wire([(520, 430), (520, 590)], BLUE, 2)
    d.dot(460, 520, ORANGE); d.dot(520, 520, BLUE)
    d.res_h(460, 520, 520, "", BLUE)
    d.text(528, 540, "R5 4.7 kΩ", "p")
    d.wire([(480, 690), (480, 715)], BLACK, 2); d.gnd(480, 715)
    d.text(470, 706, "GND", "p", "end")

    if esp01:
        d.box(30, 380, 340, 190, "Power and flashing", "", "safe")
        info = ["Set the MP1584 to 3.3 V BEFORE fitting the",
                "ESP-01S: above 3.6 V it is destroyed.",
                "100 µF + 100 nF across 3V3 and GND at its socket.",
                "Flash it out of the board, in the USB ESP-01",
                "adapter with GPIO0 to GND (the adapter's jumper).",
                "Probe: AM2301 or DHT22 only (no I2C pins left).",
                "Not a DHT11: it can't read below 20 % RH or 50 °C."]
    else:
        d.box(30, 380, 340, 170, "Or an AHT20 probe (I2C)", "the firmware uses whichever probe answers", "mod")
        info = ["VCC → 3V3,  GND → G",
                "SDA → D2 (GPIO4),  SCL → D1 (GPIO5)",
                "R6, R7: 4.7 kΩ from SDA and SCL to 3V3",
                "(leave R5 and D7 unconnected)",
                "Not a DHT11: it can't read below 20 % RH or 50 °C."]
    for i, s_ in enumerate(info):
        d.text(50, (430 if esp01 else 450) + i * 20, s_, "v")

    # fan: Q2 low-side, flyback diode
    FX = 760
    d.box(720, 280, 80, 56, "blower", "4010 12 V")
    d.wire([(FX, TOP), (FX, 280)], RED, 3); d.dot(FX, TOP, RED)
    d.dot(FX, 250, RED); d.wire([(FX, 250), (840, 250)], RED, 2)
    d.diode_v(840, 250, 370, "D1 1N5819")
    d.wire([(840, 370), (FX, 370)], BLACK, 2); d.dot(FX, 370, BLACK)
    d.wire([(FX, 336), (FX, 420)], BLACK, 3)
    d.box(735, 420, 50, 60, "Q2", "")
    d.text(792, 434, "C", "p"); d.text(792, 478, "E", "p")
    if esp01:   # RX can sit high-ish at boot: R9 holds the base down
        d.dot(723, 450, GREEN)
        d.res_v(723, 450, 530, "R9 10 kΩ", GREEN, right=False); d.gnd(723, 530)
    else:
        d.text(728, 470, "B", "p", "end")
    d.text(800, 458, "2N2222A", "p")
    d.wire([(FX, 480), (FX, 495)], BLACK, 2); d.gnd(FX, 495)
    d.wire([(620, 230), (660, 230), (660, 450), (672, 450)], GREEN, 2)
    d.res_h(672, 712 if esp01 else 735, 450, "R4 500 Ω", GREEN)
    if esp01:
        d.wire([(712, 450), (735, 450)], GREEN, 2)

    if esp01:
        # heater switch, active low: 3V3 -> R1 -> PC817 LED -> GPIO0; R8 keeps GPIO0 high at boot
        d.wire([(600, 430), (600, 600), (950, 600)], PURPLE, 2)
        d.dot(600, 500, PURPLE); d.res_h(600, 645, 500, "", PURPLE); d.flag(645, 500, "3V3", ORANGE)
        d.text(608, 524, "R8 10 kΩ", "p")
        d.wire([(855, 560), (880, 560)], ORANGE, 2); d.flag(855, 560, "3V3", ORANGE)
        d.res_h(880, 950, 560, "R1 470 Ω", ORANGE)
        d.box(950, 520, 100, 110, "PC817", "")
        d.term(950, 560, "1"); d.term(950, 600, "2")
        d.text(905, 620, "low = heat", "p", "middle")
    else:
        # heater switch: D5 -> R1 -> PC817 -> IRF3205 gate from 12 V
        d.wire([(600, 430), (600, 560), (880, 560)], PURPLE, 2)
        d.res_h(880, 950, 560, "R1 500 Ω", PURPLE)
        d.box(950, 520, 100, 110, "PC817", "")
        d.term(950, 560, "1"); d.term(950, 600, "2")
        d.wire([(950, 600), (925, 600), (925, 625)], BLACK, 2); d.gnd(925, 625)
    d.term(1050, 560, "4", "end"); d.term(1050, 600, "3", "end")
    d.wire([(1050, 560), (1080, 560)], RED, 2)
    d.res_v(1080, 560, TOP, "R2 1 kΩ", RED, right=False); d.dot(1080, TOP, RED)
    d.wire([(1050, 600), (1130, 600), (1130, 520), (1170, 520)], YELLOW, 2)
    d.text(1163, 512, "G", "p", "end")
    d.text(1140, 652, "Q1 gate: about 11 V when on", "p")
    d.dot(1100, 600, YELLOW)
    d.res_v(1100, 600, 680, "R3 10 kΩ", YELLOW, right=False); d.gnd(1100, 680)

    # heater chain: +12 V -> KSD301 -> thermal fuse -> heaters A || B -> Q1 drain
    HX = 1200
    d.wire([(HX, TOP), (HX, 160)], RED, 3); d.dot(HX, TOP, RED)
    d.box(1145, 160, 110, 46, "KSD301", "85 °C, opens", "safe")
    d.wire([(HX, 206), (HX, 226)], RED, 3)
    d.box(1145, 226, 110, 46, "thermal fuse", "92 °C, one-shot", "safe")
    d.wire([(HX, 272), (HX, 300)], RED, 3); d.dot(HX, 300, RED)
    d.wire([(1155, 300), (1245, 300)], RED, 3)
    d.wire([(1155, 300), (1155, 320)], RED, 3); d.wire([(1245, 300), (1245, 320)], RED, 3)
    d.box(1120, 320, 70, 56, "heater A", "50 W, 3 Ω")
    d.box(1210, 320, 70, 56, "heater B", "50 W, 3 Ω")
    d.wire([(1155, 376), (1155, 400)], BROWN, 3); d.wire([(1245, 376), (1245, 400)], BROWN, 3)
    d.wire([(1155, 400), (1245, 400)], BROWN, 3); d.dot(HX, 400, BROWN)
    d.wire([(HX, 400), (HX, 480)], BROWN, 3)
    d.text(HX + 8, 445, "heater −", "p")
    d.box(1170, 480, 60, 80, "Q1", "")
    d.text(HX, 528, "IRF3205", "p", "middle")
    d.text(HX + 36, 494, "D", "p"); d.text(HX + 36, 556, "S", "p");     d.text(HX + 36, 580, "on a TO-220 heatsink", "p")
    d.wire([(HX, 560), (HX, 600)], BLACK, 3); d.gnd(HX, 600)

    ctl = "the ESP-01S locks up with GPIO0 low" if esp01 else "the D1 Mini locks up with D5 high"
    boot = ("At power-up GPIO0 floats high (R8): the PC817 stays dark and R3 holds Q1's gate low, so the heater stays off until the firmware has a good reading."
            if esp01 else
            "At power-up every pin floats: the PC817 stays dark and R3 holds Q1's gate low, so the heater stays off until the firmware has a good reading.")
    board = "ESP-01S" if esp01 else "D1 Mini"
    pair = "R4 is" if esp01 else "R1 and R4 are"
    notes = [
        "Heater: two aluminium-housed 50 W resistors (RX24, 3 Ω) in parallel, 96 W at 12 V (8 A), on one finned heatsink in the blower's airflow. "
        "Heater path in 16 AWG silicone wire.",
        "The KSD301 and thermal fuse sit in the chamber air near the lid: they stop the heater if the probe fails, falls out of the airflow, "
        f"or {ctl}.",
        boot,
        f"{pair} two 1 kΩ in parallel. Grounds marked ⏚ all go to the XT60's black wire; take the heater's ground from Q1's source "
        f"straight to the XT60, not through the {board}'s wiring.",
    ]
    for i, n in enumerate(notes):
        d.text(30, 790 + i * 20, n, "v")
    d.save(HERE.parent / ("wiring-esp01.svg" if esp01 else "wiring.svg"),
           "Basic dryer controller wiring, " + ("ESP-01S" if esp01 else "D1 Mini"))


if __name__ == "__main__":
    wiring()
    wiring(esp01=True)
