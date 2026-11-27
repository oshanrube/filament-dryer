"""Search AliExpress (as a guest, shipping to Sri Lanka) to find well-sold listings for a part.

Reads the product data embedded in the public search page; no login, nothing is bought.
**The price shown is each listing's cheapest variant or promotion** (often a new-buyer "Dollar
Express" deal), not necessarily the variant you need (e.g. N16R8 vs N8R2), and excludes shipping
and coupons. Product pages are behind a captcha for scripts, so open the link to check the variant's
real price. Use this to shortlist listings, not to compare final prices.

    python3 tools/ali_search.py "ESP32-S3 N16R8" "HX711 module"
    python3 tools/ali_search.py --must N16R8 --min-sold 50 "ESP32-S3 DevKitC N16R8"

For each query: up to --top listings with at least --min-sold sales whose title contains every
--must word (case-insensitive), most sold first: lowest price, sold, rating, title, link.
"""
import argparse
import json
import re
import subprocess

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
COOKIE = "aep_usuc_f=site=glo&c_tp=USD&region=LK&b_locale=en_US"


def fetch(query):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", query).strip("-")
    url = f"https://www.aliexpress.com/w/wholesale-{slug}.html?SearchText={query.replace(' ', '+')}"
    return subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, "-b", COOKIE, url], capture_output=True, text=True).stdout


def items(html):
    i = html.find('"itemList":{"content":')
    if i < 0:
        return []
    start = html.index("[", i)
    depth = 0
    for k in range(start, len(html)):      # find the matching ] of the content array
        c = html[k]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                break
    try:
        arr = json.loads(html[start:k + 1])
    except json.JSONDecodeError:
        return []
    out = []
    for it in arr:
        pid = it.get("productId")
        title = (it.get("title") or {}).get("displayTitle", "")
        price = ((it.get("prices") or {}).get("salePrice") or {}).get("minPrice")
        if not pid or price is None:
            continue
        sold_txt = (it.get("trade") or {}).get("tradeDesc", "") or ""
        m = re.search(r"([\d,.]+)\s*(k|K|万)?\+?\s*sold", sold_txt)
        sold = 0
        if m:
            sold = float(m.group(1).replace(",", "")) * (1000 if m.group(2) in ("k", "K") else 10000 if m.group(2) == "万" else 1)
        rating = (it.get("evaluation") or {}).get("starRating")
        store = (it.get("store") or {}).get("storeName", "")
        out.append({"id": pid, "title": title, "price": float(price), "sold": int(sold), "sold_txt": sold_txt,
                    "rating": rating, "store": store, "url": f"https://www.aliexpress.com/item/{pid}.html"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--must", action="append", default=[], help="word the title must contain (repeatable)")
    ap.add_argument("--min-sold", type=int, default=20)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--sort", choices=["sold", "price"], default="sold", help="most sold first (default) or cheapest first")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    for q in a.queries:
        found = [x for x in items(fetch(q)) if x["sold"] >= a.min_sold and all(w.lower() in x["title"].lower() for w in a.must)]
        found.sort(key=(lambda x: x["price"]) if a.sort == "price" else (lambda x: -x["sold"]))
        if a.json:
            print(json.dumps({"query": q, "results": found[: a.top]}))
            continue
        print(f"== {q}: {len(found)} matching")
        for x in found[: a.top]:
            print(f"   from US${x['price']:>6.2f}  {x['sold_txt'] or '-':>12}  {x['rating'] or '-':>4}  {x['title'][:70]}")
            print(f"            {x['url']}  ({x['store'][:30]})")


if __name__ == "__main__":
    main()
