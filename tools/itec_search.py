"""Search ITEC Electronics (itecelectronic.lk) for parts: name, price (Rs.), stock and link.

ITEC runs WooCommerce, so this uses its public Store API (wp-json/wc/store/v1/products).
    python3 tools/itec_search.py "KSD301" "thermal fuse" "SSR"
"""
import html
import json
import subprocess
import sys
import urllib.parse


def search(q, n=8):
    url = "https://itecelectronic.lk/wp-json/wc/store/v1/products?" + urllib.parse.urlencode({"search": q, "per_page": n})
    raw = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", "Mozilla/5.0", url], capture_output=True, text=True).stdout
    try:
        return json.loads(raw)
    except ValueError:
        return None


for q in sys.argv[1:]:
    items = search(q)
    if items is None:
        print(f"== {q}: no answer")
        continue
    print(f"== {q}: {len(items)}")
    for p in items:
        pr = p.get("prices") or {}
        unit = 10 ** int(pr.get("currency_minor_unit", 2))
        price = int(pr.get("price") or 0) / unit
        stock = "in stock" if p.get("is_in_stock") else "out of stock"
        name = html.unescape(p.get("name", ""))[:68]
        print(f"   {name:68s} Rs.{price:>8,.0f}  {stock:12s} {p.get('permalink')}")
