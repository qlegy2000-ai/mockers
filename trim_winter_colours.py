#!/usr/bin/env python3
"""
Hoodies and sweatshirts are only made in five colours each. Anything else on a
winter product is a leftover from the old catalogue and cannot be fulfilled, so
those variants are removed.

  Hoodie      Black, Offwhite, Purple, Aegean Blue, Iron Grey
  Sweatshirt  Black, Offwhite, Dark Green, Dark Blue, Beetroot Purple

Summer garments are not touched. A product is never left with zero variants -
if that were ever the case it is reported and skipped rather than emptied.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv

KEEP = {
    "Hoodie":     {"Black", "Offwhite", "Purple", "Aegean Blue", "Iron Grey"},
    "Sweatshirt": {"Black", "Offwhite", "Dark Green", "Dark Blue", "Beetroot Purple"},
}

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

Q = '''query($c:String){ products(first:60,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ id handle
  style: metafield(namespace:"custom",key:"style"){value}
  variants(first:250){ nodes{ id selectedOptions{name value} } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

plan, emptied = [], []
bycol, byst = collections.Counter(), collections.Counter()
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in KEEP:
        continue
    vs = r["variants"]["nodes"]
    kill = [v for v in vs
            if not any(o["name"] == "Color" and o["value"] in KEEP[st]
                       for o in v["selectedOptions"])]
    if not kill:
        continue
    if len(kill) == len(vs):            # never empty a product
        emptied.append(r["handle"]); continue
    for v in kill:
        bycol[(st, next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color"))] += 1
    byst[st] += len(kill)
    plan.append({"id": r["id"], "handle": r["handle"],
                 "ids": [v["id"] for v in kill]})

for st in ("Hoodie", "Sweatshirt"):
    print(f'{st}:')
    for (s, c), n in sorted(bycol.items(), key=lambda x: -x[1]):
        if s == st:
            print(f'   {c:<18} {n:>4}')
    print(f'   {"TOTAL":<18} {byst[st]:>4}')
print(f'\nproducts affected : {len(plan)}')
print(f'variants to delete: {sum(byst.values())}')
print(f'skipped (would empty the product): {len(emptied)} {emptied[:5]}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

DEL = """mutation($productId:ID!,$ids:[ID!]!){
 productVariantsBulkDelete(productId:$productId, variantsIds:$ids){ userErrors{ field message } } }"""
ok = err = 0
for i, p in enumerate(plan, 1):
    for j in range(0, len(p["ids"]), 100):
        g = gql(DEL, {"productId": p["id"], "ids": p["ids"][j:j + 100]})["data"]["productVariantsBulkDelete"]
        if g["userErrors"]:
            err += 1; print('  failed', p["handle"], g["userErrors"][:1])
        else:
            ok += len(p["ids"][j:j + 100])
    if i % 25 == 0:
        print(f'  ...{i}/{len(plan)} products, {ok} variants deleted', flush=True)
print(f'\nDELETED {ok} variants   errors={err}')
