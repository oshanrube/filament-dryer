#!/usr/bin/env python3
"""Board layout for the dryer controller: 70 x 150 mm, harness connectors on the two short ends.

Called by gen_kicad.write_pcb() on the freshly generated board. It places every footprint,
draws the outline, mounting holes and the two break-off sensor boards, and lays the
12.5 A heater path as wide copper. Routing of the remaining nets is a separate step.

Board coordinates below are mm from the board's top-left corner; "top end" is y = 0
(power in, heater, USB, fans, chamber sensors), "bottom end" is y = 150 (load cells,
feeder motors, lane and motion sensors, OLED, button).
"""
import pcbnew

W, H = 70.0, 150.0
OX, OY = 100.0, 50.0          # where the board sits on the KiCad page
MARGIN = 0.5                  # space kept between courtyards when packing
KICAD_FPS = "/usr/share/kicad/footprints"

# ------------------------------------------------------------------ fixed positions
# ref: (x, y, rotation) of the footprint origin, in board mm
FIXED = {
    # top end, row A at the edge
    "J1": (4.9, 17.3, 0),       # XT60PW-M, mating face at y = 0
    "F1": (22.0, 3.6, 0),       # ATO fuse holder
    "TB2": (49.5, 6.0, 180),    # heater terminal, wire entry facing the top edge
    "J2": (62.2, 4.65, 180),    # USB-C, opening at the top edge
    "Q1": (48.0, 17.2, 0),      # heater MOSFET right under TB2
    # top end, row B
    "J5": (3.0, 25.0, 0), "J6": (17.0, 25.0, 0), "J3": (50.0, 25.0, 0), "J4": (59.5, 25.0, 0),
    # bottom end, row C and row D (row D at the edge)
    "J13": (3.0, 137.4, 0), "J14": (14.0, 137.4, 0), "J15": (25.0, 137.4, 0), "J8": (39.0, 137.4, 0), "J9": (53.0, 137.4, 0),
    "J11": (3.0, 145.9, 0), "J12": (17.0, 145.9, 0), "J16": (40.5, 145.9, 0), "J17": (55.0, 145.9, 0),
    # bay sensor at the right edge, away from the buck, the regulator and the drivers
    "U13": (67.6, 44.0, 0), "C38": (67.6, 47.6, 90),
    # sensor board SB1 (chamber SHT40) and SB2 (outlet DS18B20), break-off at the right edge
    "U14": (61.6, 66.0, 0), "C37": (61.6, 70.0, 0), "J18": (67.3, 65.2, 0),
    "U15": (62.4, 89.4, 90), "C39": (62.4, 84.0, 0), "J19": (67.3, 84.6, 0),
}
# the ESP32 module: antenna end on the left board edge, placed by code (see below)
U1_Y = (37.4, 66.0)

HOLES = [(3.5, 32.5), (66.5, 32.5), (3.5, 130.0), (66.5, 130.0)]

# ------------------------------------------------------------------ packing regions
# (x0, y0, x1, y1), parts packed in order, biggest first
REGIONS = [
    ((17.6, 8.9, 27.6, 19.6), ["C1"]),
    ((27.6, 8.9, 41.0, 19.8), ["U2", "L1", "C3", "C2", "C4", "C5", "C6"], 1.0),   # buck: keep its loops short
    ((53.2, 10.6, 69.4, 22.2), ["U4", "C8", "C9", "R7", "R8", "R9", "R18", "R19"]),
    ((25.3, 21.8, 46.6, 29.6), ["Q2", "Q3", "D1", "D2", "R10", "R11", "R12", "R13"], 1.2),
    ((7.6, 29.4, 62.4, 36.8), ["U12", "C12", "C13", "R1", "R2", "R3", "R4"]),
    ((28.5, 38.0, 56.5, 62.5), ["U3", "C7", "R5", "R6"]),
    ((0.6, 67.5, 27.5, 79.5), ["SW2", "SW3", "C14", "C15", "R16", "C16", "R17"]),
    ((30.0, 64.0, 56.0, 95.5), ["BZ1", "Q4", "R14", "R15"]),
    ((0.6, 81.0, 16.6, 126.4), ["U7", "Q5", "C17", "C18", "C19", "C20", "C21", "R20", "R21"]),
    ((17.4, 81.0, 33.4, 133.6), ["U8", "Q6", "C22", "C23", "C24", "C25", "C26", "R22", "R23"]),
    ((34.4, 97.0, 52.0, 133.6), ["U10", "C10", "C27", "C28", "C29", "C30", "C31", "R24", "R25", "R26", "R27"]),
    ((52.6, 99.0, 69.4, 126.4), ["U11", "C11", "C32", "C33", "C34", "C35", "C36", "R28", "R29", "R30", "R31"]),
]
GAP = 1.6         # minimum space between courtyards inside a region; leftover room is spread evenly

# sensor boards: (x0, y0, x1, y1) of each break-off board, flush with the right edge
SENSOR_BOARDS = [(58.4, 62.2, 70.0, 76.0), (58.4, 80.8, 70.0, 95.2)]
SLOT = 1.6        # routed slot width around the sensor boards
BRIDGE = 2.4      # solid bridge left in the slot, with mouse-bite holes


def mm(v):
    return pcbnew.FromMM(v)


def vec(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def court(fp):
    c = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = c.BBox() if not c.IsEmpty() else fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY,
            pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY)


def overlap(a, b, gap=0.0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def put(fp, x, y, rot):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(vec(x, y))


def layout(board):
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    taken = []                     # courtyards already placed

    for ref, (x, y, r) in FIXED.items():
        put(fps[ref], x, y, r)
        taken.append((ref, court(fps[ref])))

    # U1: rotate so the antenna end faces x = 0, then move flush to the left edge
    u1 = fps["U1"]
    put(u1, 20.0, sum(U1_Y) / 2, 90)
    c = court(u1)
    ant = [z for z in u1.Zones()]
    ax = min(pcbnew.ToMM(z.GetBoundingBox().GetX()) - OX for z in ant) if ant else c[0]
    if ax > c[0] + 1:              # antenna keepout on the wrong side: turn the other way
        put(u1, 20.0, sum(U1_Y) / 2, 270)
        c = court(u1)
    u1.Move(pcbnew.VECTOR2I(mm(-c[0]), mm(U1_Y[0] - c[1])))
    taken.append(("U1", court(u1)))

    blocked = [(hx - 3.6, hy - 3.6, hx + 3.6, hy + 3.6) for hx, hy in HOLES]
    blocked += [(x0 - SLOT - 0.3, y0 - SLOT - 0.3, W, y1 + SLOT + 0.3) for x0, y0, x1, y1 in SENSOR_BOARDS]

    for region, refs, *gap in REGIONS:
        for ref, c in pack(fps, region, refs, blocked, taken, gap[0] if gap else GAP):
            taken.append((ref, c))

    missing = [r for r in fps if r not in {t[0] for t in taken}]
    if missing:
        raise SystemExit(f"place_pcb: not placed: {missing}")

    outline(board)
    holes(board)
    sensor_board_cuts(board)
    settings(board)
    power_tracks(board, fps)
    return taken


def pack(fps, region, refs, blocked, taken, GAP=GAP):
    """Shelf-pack the parts in rows (biggest first), then spread the rows over the region's height
    and the parts over each row's width, so the leftover room becomes routing channels."""
    x0, y0, x1, y1 = region
    items = []
    for ref in refs:
        fp = fps[ref]
        put(fp, 0, 0, 0)
        c = court(fp)
        if c[2] - c[0] > x1 - x0:                     # too wide lying down: stand it up
            put(fp, 0, 0, 90)
            c = court(fp)
        items.append((ref, fp, c[2] - c[0], c[3] - c[1]))
    rows, row, rx = [], [], 0.0
    for it in items:
        if row and rx + it[2] > x1 - x0:
            rows.append(row); row, rx = [], 0.0
        row.append(it); rx += it[2] + GAP
    if row:
        rows.append(row)
    heights = [max(it[3] for it in r) for r in rows]
    spare_y = (y1 - y0) - sum(heights) - GAP * (len(rows) - 1)
    if spare_y < 0:
        raise SystemExit(f"place_pcb: region {region} too small for {refs}")
    out, y = [], y0 + spare_y / (2 * len(rows))
    for r, h in zip(rows, heights):
        spare_x = (x1 - x0) - sum(it[2] for it in r) - GAP * (len(r) - 1)
        x = x0 + spare_x / (2 * len(r))
        for ref, fp, w, hh in r:
            c = court(fp)
            fp.Move(pcbnew.VECTOR2I(mm(x - c[0]), mm(y + (h - hh) / 2 - c[1])))
            nc = court(fp)
            for other, oc in taken + out:
                if overlap(nc, oc, 0.2):
                    raise SystemExit(f"place_pcb: {ref} hits {other}")
            for b in blocked:
                if overlap(nc, b):
                    raise SystemExit(f"place_pcb: {ref} hits a hole or slot")
            out.append((ref, nc))
            x += w + GAP + spare_x / len(r)
        y += h + GAP + spare_y / len(rows)
    return out


# ------------------------------------------------------------------ outline, holes, break-off boards
def seg(board, a, b, layer=pcbnew.Edge_Cuts, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(vec(*a)); s.SetEnd(vec(*b))
    s.SetLayer(layer); s.SetWidth(mm(width))
    board.Add(s)


def rect(board, x0, y0, x1, y1, layer=pcbnew.Edge_Cuts):
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        seg(board, a, b, layer)


def poly_cut(board, pts):
    for a, b in zip(pts, pts[1:] + pts[:1]):
        seg(board, a, b)


def outline(board):
    rect(board, 0, 0, W, H)


def holes(board):
    lib = f"{KICAD_FPS}/MountingHole.pretty"
    for i, (x, y) in enumerate(HOLES, 1):
        fp = pcbnew.FootprintLoad(lib, "MountingHole_3.2mm_M3")
        fp.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_3.2mm_M3"))
        fp.SetReference(f"H{i}")
        fp.SetValue("M3")
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.SetPosition(vec(x, y))
        board.Add(fp)


_MB = [0]


def mouse_bites(board, x, y, horizontal, n=3, pitch=0.8, d=0.5):
    """A row of small NPTH holes across a bridge, so the sensor board snaps off cleanly.
    One footprint per bridge, numbered MB1, MB2, ... (EasyEDA refuses duplicate designators)."""
    _MB[0] += 1
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(f"MB{_MB[0]}")
    fp.SetValue("mouse bites")
    fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    fp.SetPosition(vec(x, y))
    for i in range(n):
        off = (i - (n - 1) / 2) * pitch
        dx, dy = (off, 0) if horizontal else (0, off)
        pad = pcbnew.PAD(fp)
        pad.SetNumber("")
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(mm(d), mm(d)))
        pad.SetDrillSize(pcbnew.VECTOR2I(mm(d), mm(d)))
        pad.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
        pad.SetPos0(pcbnew.VECTOR2I(mm(dx), mm(dy)))
        pad.SetPosition(vec(x + dx, y + dy))
        fp.Add(pad)
    board.Add(fp)


def sensor_board_cuts(board):
    """Each sensor board is cut free on three sides by a slot, leaving three bridges:
    one in the middle of the inner (left) side and one at each end next to the board edge."""
    for x0, y0, x1, y1 in SENSOR_BOARDS:
        sx = x0 - SLOT                       # slot runs from sx to x0 on the left side
        ym = (y0 + y1) / 2
        xe = W - BRIDGE                      # slots stop short of the outer edge
        # upper L: along the top, then down the left side to the middle bridge
        poly_cut(board, [(sx, y0 - SLOT), (xe, y0 - SLOT), (xe, y0), (x0, y0), (x0, ym - BRIDGE / 2), (sx, ym - BRIDGE / 2)])
        # lower L: from the middle bridge down the left side, then along the bottom
        poly_cut(board, [(sx, ym + BRIDGE / 2), (x0, ym + BRIDGE / 2), (x0, y1), (xe, y1), (xe, y1 + SLOT), (sx, y1 + SLOT)])
        mouse_bites(board, sx + SLOT / 2, ym, False)                 # middle bridge (vertical slot line)
        mouse_bites(board, xe + BRIDGE / 2, y0 - SLOT / 2, True)     # top bridge
        mouse_bites(board, xe + BRIDGE / 2, y1 + SLOT / 2, True)     # bottom bridge


def settings(board):
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = mm(0.15)
    ds.m_MinClearance = mm(0.15)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.3)


# ------------------------------------------------------------------ the 12.5 A heater path, as wide locked copper
def pad_at(fp, num, near=None):
    pads = [p for p in fp.Pads() if p.GetNumber() == num]
    if near is not None:
        pads.sort(key=lambda p: (pcbnew.ToMM(p.GetPosition().x) - OX - near[0]) ** 2 + (pcbnew.ToMM(p.GetPosition().y) - OY - near[1]) ** 2)
    else:
        pads.sort(key=lambda p: -p.GetSize().x * p.GetSize().y)      # the biggest one (a tab)
    q = pads[0].GetPosition()
    return pcbnew.ToMM(q.x) - OX, pcbnew.ToMM(q.y) - OY


def track(board, pts, net, width, layers):
    ni = board.FindNet(net)
    for layer in layers:
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(*a)); t.SetEnd(vec(*b))
            t.SetWidth(mm(width)); t.SetLayer(layer); t.SetNet(ni); t.SetLocked(True)
            board.Add(t)


def power_tracks(board, fps):
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    j1p, j1g = pad_at(fps["J1"], "2"), pad_at(fps["J1"], "1")
    f1a = pad_at(fps["F1"], "1", near=(j1p[0] + 20, j1p[1] - 12))
    f1b = pad_at(fps["F1"], "2", near=(45, 6))
    tbp, tbh = pad_at(fps["TB2"], "2"), pad_at(fps["TB2"], "1")
    tab = pad_at(fps["Q1"], "2")
    src = pad_at(fps["Q1"], "3")
    # supply +: XT60 -> fuse, fuse -> heater terminal (through-hole at both ends: both layers)
    track(board, [j1p, (j1p[0], f1a[1]), f1a], "+12V_IN", 2.5, (F, B))
    track(board, [f1b, (tbp[0], f1b[1]), tbp], "+12V", 2.5, (F, B))
    # heater return: terminal -> MOSFET drain tab
    track(board, [tbh, (tbh[0], tab[1] - 2.0), (tab[0], tab[1] - 2.0), tab], "HEATER_N", 3.0, (F,))
    # MOSFET source -> XT60 minus, under the top-end parts (the ground pours add to it)
    y = 20.9
    track(board, [src, (src[0], y), (j1g[0], y), j1g], "GND", 1.5, (F,))


# ------------------------------------------------------------------ the 1-roll board: 70 x 100 mm
def use_1roll():
    """Same top end as the 2-roll board; the middle and the bottom end shrink to what the 1-roll needs."""
    global H, FIXED, HOLES, REGIONS, SENSOR_BOARDS
    H = 100.0
    top = {k: v for k, v in FIXED.items() if k in ("J1", "F1", "TB2", "J2", "Q1", "J5", "J6", "J3", "J4")}
    FIXED = {**top,
             # bottom end, one row at the edge
             "J11": (10.0, 95.9, 0), "J15": (25.0, 95.9, 0), "J8": (40.0, 95.9, 0), "J9": (55.0, 95.9, 0),
             # bay sensor at the right edge
             "U13": (67.6, 77.0, 0), "C38": (67.6, 80.6, 90),
             # sensor boards SB1, SB2 on the right edge, beside the ESP32
             "U14": (61.6, 42.4, 0), "C37": (61.6, 46.4, 0), "J18": (67.3, 41.6, 0),
             "U15": (62.4, 65.2, 90), "C39": (62.4, 59.8, 0), "J19": (67.3, 60.4, 0)}
    HOLES = [(3.5, 32.5), (66.5, 32.5), (3.5, 87.0), (66.5, 87.0)]
    SENSOR_BOARDS = [(58.4, 38.6, 70.0, 52.4), (58.4, 57.0, 70.0, 71.0)]
    REGIONS = [
        ((17.6, 8.9, 27.6, 19.6), ["C1"]),
        ((27.6, 8.9, 41.0, 19.8), ["U2", "L1", "C3", "C2", "C4", "C5", "C6"], 1.0),
        ((53.2, 10.6, 69.4, 22.2), ["U4", "C8", "C9", "R7", "R8", "R9", "R18", "R19"]),
        ((25.3, 21.8, 46.6, 29.6), ["Q2", "Q3", "D1", "D2", "R10", "R11", "R12", "R13"], 1.2),
        ((7.6, 29.4, 62.4, 36.8), ["U12", "C12", "C13", "R1", "R2", "R3", "R4"]),
        ((28.5, 38.0, 55.6, 62.5), ["BZ1", "Q4", "R14", "R15", "R32", "R33"]),
        ((0.6, 67.5, 27.5, 82.0), ["SW2", "SW3", "C14", "C15", "R16", "C16", "R17"]),
        ((28.5, 64.0, 56.0, 91.5), ["U7", "Q5", "C17", "C18", "C19", "C20", "C21", "R20", "R21"]),
    ]
