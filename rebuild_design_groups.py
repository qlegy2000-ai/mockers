#!/usr/bin/env python3
"""
Rebuild catalog-build/design_groups.json from the LIVE store.

apply_lead_tags.py, tag_season_leads.py and set_sibling_styles.py all read this
file. It was originally generated from the export CSV, which means it goes stale
the moment a product is created or drafted in Shopify - and a stale file silently
mistags: a design whose cheapest garment has changed keeps its old lead, and a
product the file has never heard of gets no sibling_styles at all, so the PDP
garment switcher does not show it.

Reading live instead makes the three scripts correct by construction. Run this
first, every time, before any of them.

Shape: {design_id: [{handle, style, price}, ...]} ordered cheapest garment first.

SHOP and TOKEN from the environment.
"""
import json, os, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
STYLE_SORT = ["Regular Fit T-Shirt", "Oversized Light-Soft", "Oversized Heavy Premium",
              "Sweatshirt", "Hoodie"]

def gql(q, v=None):
    for _ in range(10):
        req = urllib.request.Request(
            f"https://{SHOP}/admin/api/2026-07/graphql.json",
            data=json.dumps({"query": q, "variables": v or {}}).encode(),
            headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
        o = json.load(urllib.request.urlopen(req))
        if o.get("errors") and "THROTTLED" in json.dumps(o["errors"]):
            time.sleep(5); continue
        if o.get("errors"):
            raise SystemExit("GQL " + json.dumps(o["errors"])[:300])
        ts = o.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
        if ts.get("currentlyAvailable", 2000) < 700:
            time.sleep(2)
        return o
    raise SystemExit("throttled out")

Q = '''query($c:String){ products(first:50,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ handle status
  design: metafield(namespace:"custom",key:"design_id"){value}
  style:  metafield(namespace:"custom",key:"style"){value}
  variants(first:1){ nodes{ price } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

groups = collections.defaultdict(list)
for r in rows:
    st = (r["style"] or {}).get("value")
    did = (r["design"] or {}).get("value")
    # drafted products are deliberately out of the catalogue - they must not win a
    # lead tag or appear in another product's garment switcher
    if not st or not did or st not in STYLE_SORT or r["status"] != "ACTIVE":
        continue
    if not r["variants"]["nodes"]:
        continue
    groups[did].append({"handle": r["handle"], "style": st,
                        "price": r["variants"]["nodes"][0]["price"]})

out = {}
for did, items in sorted(groups.items()):
    items.sort(key=lambda x: (float(x["price"]), STYLE_SORT.index(x["style"])))
    out[did] = items

path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "catalog-build", "design_groups.json")
prev = {}
if os.path.exists(path):
    prev = json.load(open(path))
json.dump(out, open(path, "w"), indent=1)

print(f"designs : {len(out)}  (was {len(prev)})")
print(f"products: {sum(len(v) for v in out.values())}")
size = collections.Counter(len(v) for v in out.values())
print("garments per design:", dict(sorted(size.items())))
added = sorted(set(out) - set(prev))
if added:
    print(f"designs new to the file ({len(added)}): {added}")
moved = [d for d in set(out) & set(prev)
         if out[d][0]["handle"] != prev[d][0]["handle"]]
if moved:
    print(f"designs whose lead changed ({len(moved)}): {moved[:10]}")
print("wrote", path)
