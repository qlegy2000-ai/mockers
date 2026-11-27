#!/usr/bin/env python3
"""Read-only: which Hoodie / Sweatshirt colours have no mockup image on live.

Writes reports/missing_winter_mockups.csv (design, style, colour, status) and
prints colours outside the 2026 winter palette.
  SHOP=mockers-shop.myshopify.com TOKEN=proxy-injected python3 audit_winter_mockups.py
"""
import csv, json, os, urllib.request
SHOP = os.environ.get("SHOP", "mockers-shop.myshopify.com")
TOKEN = os.environ.get("TOKEN", "proxy-injected")
API = f"https://{SHOP}/admin/api/2026-07/graphql.json"
PALETTE = {"Hoodie": ["Black", "Offwhite", "Purple", "Iron Grey", "Aegean Blue"],
           "Sweatshirt": ["Black", "Offwhite", "Beetroot Purple", "Dark Green", "Dark Blue"]}

def gql(q, v=None):
    r = urllib.request.Request(API, json.dumps({"query": q, "variables": v or {}}).encode(),
                               {"Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN})
    return json.load(urllib.request.urlopen(r))["data"]

Q = """query($c:String,$q:String){ products(first:50, after:$c, query:$q){ pageInfo{hasNextPage endCursor}
 nodes{ title handle status productType
   metafield(namespace:"custom", key:"design_title"){ value }
   variants(first:60){ nodes{ selectedOptions{name value} image{ id } inventoryPolicy } } } } }"""
rows, odd = [], []
for style in PALETTE:
    c = None
    while True:
        d = gql(Q, {"c": c, "q": f"product_type:'{style}' status:active"})["products"]
        for p in d["nodes"]:
            if p["productType"] != style:
                continue
            col = {}
            for v in p["variants"]["nodes"]:
                cl = next((o["value"] for o in v["selectedOptions"] if o["name"] == "Color"), "?")
                col.setdefault(cl, []).append(bool(v["image"]))
            design = (p["metafield"] or {}).get("value") or p["title"].rsplit(" ", 1)[0]
            for cl, imgs in col.items():
                if cl not in PALETTE[style]:
                    odd.append((p["handle"], cl))
                    continue
                rows.append({"design": design, "handle": p["handle"], "style": style, "colour": cl,
                             "status": "OK" if all(imgs) else ("MISSING" if not any(imgs) else "PARTIAL")})
            for cl in PALETTE[style]:
                if cl not in col:
                    rows.append({"design": design, "handle": p["handle"], "style": style, "colour": cl, "status": "NO VARIANT"})
        if not d["pageInfo"]["hasNextPage"]:
            break
        c = d["pageInfo"]["endCursor"]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "missing_winter_mockups.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
from collections import Counter
print("products checked:", len({r['handle'] for r in rows}))
print(Counter((r["style"], r["status"]) for r in rows))
print("colours outside palette:", Counter(c for _, c in odd), odd[:10])
