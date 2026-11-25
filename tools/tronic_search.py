"""Search Tronic.lk for parts: name, price (Rs.), stock and link for each match.

Uses the same JSON search the shop page itself calls (POST shop/search). Used to build the parts list in
1-roll/perfboard/README.md; re-run it before buying to check prices and stock.

    python3 tools/tronic_search.py "HX711" "IRF3205" "AHT20"
"""
import json, os, re, subprocess, sys, tempfile
jar = os.path.join(tempfile.mkdtemp(), "jar")
def curl(url, data=None):
    cmd = ["curl", "-sL", "--max-time", "40", "-A", "Mozilla/5.0", "-b", jar, "-c", jar, "-H", "X-Requested-With: XMLHttpRequest", url]
    for k, v in (data or {}).items():
        cmd += ["--data-urlencode", f"{k}={v}"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout
home = curl("https://tronic.lk/shop/products")
tok = re.search(r"csrf_token_value: '([0-9a-f]+)'", home).group(1)
for q in sys.argv[1:]:
    raw = curl("https://tronic.lk/shop/search?page=1", {"token": tok, "filters[query]": q, "filters[page]": "1", "format": "json"})
    try:
        d = json.loads(raw)
    except Exception:
        print(f"== {q}: no JSON ({raw[:120]!r})"); continue
    ps = d.get("products") or []
    print(f"== {q}: {len(ps)}")
    for p in ps[:8]:
        qty = p.get("quantity")
        price = p.get("promo_price") if p.get("promotion") and p.get("promo_price") else p.get("price")
        print(f"   {p.get('name','')[:70]:70s} Rs.{float(price or 0):>8,.0f}  stock={float(qty) if qty not in (None,'') else '?'}  https://tronic.lk/product/{p.get('slug')}")
