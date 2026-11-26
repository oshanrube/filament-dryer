#!/usr/bin/env python3
"""Build the GitHub Pages site in docs/ from the version folders.

Each version folder (2-roll-feeder/, 1-roll/) holds page.html (the page body),
bom.csv, wiring.svg and images/. This script wraps each page in
site/layout.html, fills in the parts tables from bom.csv, copies the assets,
and writes the overview page from site/overview.html.

Run:  python3 tools/build_site.py
"""
import csv
import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LAYOUT = (ROOT / "site" / "layout.html").read_text(encoding="utf-8")

# (folder, tab label, page title, description)
VERSIONS = [
    ("2-roll-feeder", "2-roll feeder", "Two-Reel Filament Dryer",
     "Two-reel dryer and feeder with automatic reel switch-over, per-reel weighing and motion sensing."),
    ("1-roll", "1 roll", "Single-Reel Filament Dryer",
     "Single-reel dryer with weighing, filament motion sensing and Printer Control Center integration."),
    ("dumb", "Dumb (STC-3028)", "Dumb Filament Dryer",
     "The cheapest box: a humidity-controlled heater with an STC-3028 and a W1209, no microcontroller."),
]


def bom(folder: str):
    rows = list(csv.DictReader((ROOT / folder / "bom.csv").open(newline="", encoding="utf-8")))
    shared = sum(float(r["approx_usd"]) for r in rows if r["part"].startswith("Shared:"))
    per_box = sum(float(r["approx_usd"]) for r in rows) - shared
    return rows, per_box, shared


def bom_tables(rows) -> str:
    sections: dict[str, list[dict]] = {}
    for r in rows:
        sections.setdefault(r["section"], []).append(r)
    parts = []
    for name, items in sections.items():
        total = sum(float(r["approx_usd"]) for r in items)
        parts.append(f"<h3>{html.escape(name)} (≈ US${total:.0f})</h3>")
        parts.append('<div class="table-wrap"><table>')
        parts.append("<thead><tr><th>Part</th><th>Qty</th><th>AliExpress search</th><th>≈ US$</th><th>Why this one</th></tr></thead><tbody>")
        for r in items:
            parts.append(
                "<tr>"
                f"<td>{html.escape(r['part'])}</td>"
                f"<td>{html.escape(r['qty'])}</td>"
                f"<td>{html.escape(r['aliexpress_search'])}</td>"
                f"<td class=\"num\">{float(r['approx_usd']):g}</td>"
                f"<td>{html.escape(r['why'])}</td>"
                "</tr>"
            )
        parts.append("</tbody></table></div>")
    return "\n".join(parts)


def tabs(current: str, root: str) -> str:
    items = [("index", "Overview", f"{root}index.html")]
    items += [(folder, label, f"{root}{folder}/index.html") for folder, label, *_ in VERSIONS]
    out = []
    for key, label, href in items:
        cur = ' aria-current="page"' if key == current else ""
        out.append(f'<a href="{href}"{cur}>{html.escape(label)}</a>')
    return "".join(out)


def page(title, description, current, root, content, footer) -> str:
    return (LAYOUT.replace("{{TITLE}}", html.escape(title))
                  .replace("{{DESCRIPTION}}", html.escape(description))
                  .replace("{{ROOT}}", root)
                  .replace("{{TABS}}", tabs(current, root))
                  .replace("{{CONTENT}}", content)
                  .replace("{{FOOTER}}", footer))


def main() -> None:
    if DOCS.exists():
        for child in DOCS.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").touch()

    costs = {}
    for folder, label, title, desc in VERSIONS:
        src = ROOT / folder
        out = DOCS / folder
        out.mkdir(parents=True)
        rows, per_box, shared = bom(folder)
        costs[folder] = (per_box, shared)
        body = (src / "page.html").read_text(encoding="utf-8")
        body = (body.replace("{{BOM_TABLES}}", bom_tables(rows))
                    .replace("{{BOM_PER_BOX}}", f"{per_box:.0f}")
                    .replace("{{BOM_SHARED}}", f"{shared:.0f}"))
        wiring_table = src / "wiring-table.html"
        body = body.replace("{{WIRING_TABLE}}", wiring_table.read_text(encoding="utf-8") if wiring_table.exists() else "")
        footer = f"Built from <code>{folder}/page.html</code> and <code>{folder}/bom.csv</code> by <code>tools/build_site.py</code>."
        (out / "index.html").write_text(page(title, desc, folder, "../", body, footer), encoding="utf-8")
        for name in ("bom.csv", "wiring.svg"):
            shutil.copy2(src / name, out / name)
        shutil.copytree(src / "images", out / "images")
        if (src / "basic" / "wiring.svg").exists():
            (out / "basic").mkdir()
            shutil.copy2(src / "basic" / "wiring.svg", out / "basic" / "wiring.svg")
        if (src / "perfboard").exists():
            (out / "perfboard").mkdir()
            for f in (src / "perfboard").glob("*.svg"):
                shutil.copy2(f, out / "perfboard" / f.name)
        print(f"wrote docs/{folder}/ (per box ≈ US${per_box:.0f}, shared ≈ US${shared:.0f})")

    pcb_out = DOCS / "pcb"
    pcb_out.mkdir()
    for f in [ROOT / "pcb" / "schematic.svg", ROOT / "pcb" / "schematic.pdf", ROOT / "pcb" / "easyeda" / "dryer-controller-kicad.zip"] + list((ROOT / "pcb" / "export").glob("*.pdf")) + list((ROOT / "pcb" / "export").glob("*.svg")) + list((ROOT / "pcb" / "jlcpcb").glob("*.csv")):
        shutil.copy2(f, pcb_out / f.name)
    one = ROOT / "pcb" / "1-roll"
    if one.exists():
        (pcb_out / "1-roll").mkdir()
        for f in [one / "easyeda" / "dryer-controller-1roll-kicad.zip", one / "export" / "dryer-controller-1roll.pdf"] + list((one / "jlcpcb").glob("*.csv")):
            shutil.copy2(f, pcb_out / "1-roll" / f.name)
    print("wrote docs/pcb/")

    overview = (ROOT / "site" / "overview.html").read_text(encoding="utf-8")
    for folder, (per_box, shared) in costs.items():
        key = folder.upper().replace("-", "_")
        overview = (overview.replace("{{" + key + "_PER_BOX}}", f"{per_box:.0f}")
                            .replace("{{" + key + "_SHARED}}", f"{shared:.0f}"))
    footer = "Built from <code>site/overview.html</code> by <code>tools/build_site.py</code>."
    (DOCS / "index.html").write_text(
        page("Filament Dryer", "Two-reel and single-reel 3D-printed filament dryers.", "index", "", overview, footer),
        encoding="utf-8")
    print("wrote docs/index.html")


if __name__ == "__main__":
    main()
