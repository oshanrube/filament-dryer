#!/usr/bin/env python3
"""Build docs/index.html (GitHub Pages) from site/index.template.html and docs/bom.csv.

Run:  python3 tools/build_site.py
"""
import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "site" / "index.template.html"
BOM = ROOT / "docs" / "bom.csv"
OUT = ROOT / "docs" / "index.html"


def main() -> None:
    rows = list(csv.DictReader(BOM.open(newline="", encoding="utf-8")))
    sections: dict[str, list[dict]] = {}
    for r in rows:
        sections.setdefault(r["section"], []).append(r)

    shared = sum(float(r["approx_usd"]) for r in rows if r["part"].startswith("Shared:"))
    per_box = sum(float(r["approx_usd"]) for r in rows) - shared

    parts = []
    for name, items in sections.items():
        total = sum(float(r["approx_usd"]) for r in items)
        parts.append(f"<h3>{html.escape(name)} (≈ US${total:.0f})</h3>")
        parts.append('<div class="table-wrap"><table>')
        parts.append("<thead><tr><th>Part</th><th>Qty</th><th>AliExpress search</th><th>≈ US$</th><th>Why this one</th></tr></thead><tbody>")
        for r in items:
            usd = float(r["approx_usd"])
            parts.append(
                "<tr>"
                f"<td>{html.escape(r['part'])}</td>"
                f"<td>{html.escape(r['qty'])}</td>"
                f"<td>{html.escape(r['aliexpress_search'])}</td>"
                f"<td class=\"num\">{usd:g}</td>"
                f"<td>{html.escape(r['why'])}</td>"
                "</tr>"
            )
        parts.append("</tbody></table></div>")

    page = TEMPLATE.read_text(encoding="utf-8")
    page = (page.replace("{{BOM_TABLES}}", "\n".join(parts))
                .replace("{{BOM_PER_BOX}}", f"{per_box:.0f}")
                .replace("{{BOM_SHARED}}", f"{shared:.0f}"))
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} (per box ≈ US${per_box:.0f}, shared ≈ US${shared:.0f})")


if __name__ == "__main__":
    main()
