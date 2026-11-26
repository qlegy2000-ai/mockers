#!/usr/bin/env python3
"""
Hoodies and sweatshirts are made in S, M, L, XL and 2XL only.

XS came across from the old catalogue. This removes every XS variant from winter
garments. Summer garments keep theirs - they were not part of this instruction.

A product is never emptied: if XS were somehow its only size the product is
reported and skipped.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
WINTER = {"Hoodie", "Sweatshirt"}
DROP = "XS"

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
 nodes{ id handle style: metafield(namespace:"custom",key:"style"){value}
  variants(first:250){ nodes{ id selectedOptions{name value} } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

work, skipped = [], []
per = collections.Counter()
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in WINTER:
        continue
    vs = r["variants"]["nodes"]
    kill = [v for v in vs
            if any(o["name"] == "Size" and o["value"] == DROP for o in v["selectedOptions"])]
    if not kill:
        continue
    if len(kill) == len(vs):
        skipped.append(r["handle"]); continue
    per[st] += len(kill)
    work.append({"id": r["id"], "handle": r["handle"],
                 "ids": [v["id"] for v in kill]})

print(f'winter products carrying {DROP} : {len(work)}')
for st in ("Hoodie", "Sweatshirt"):
    print(f'   {st:<12} {per[st]:>4} variants')
print(f'variants to delete : {sum(per.values())}')
print(f'skipped (would empty the product): {len(skipped)} {skipped[:5]}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

DEL = """mutation($productId:ID!,$ids:[ID!]!){
 productVariantsBulkDelete(productId:$productId, variantsIds:$ids){ userErrors{ field message } } }"""
ok = err = 0
for i, w in enumerate(work, 1):
    g = gql(DEL, {"productId": w["id"], "ids": w["ids"]})["data"]["productVariantsBulkDelete"]
    if g["userErrors"]:
        err += 1; print('  failed', w["handle"], g["userErrors"][:1])
    else:
        ok += len(w["ids"])
    if i % 25 == 0:
        print(f'  ...{i}/{len(work)} products, {ok} variants', flush=True)
print(f'\nDELETED {ok} {DROP} variants   errors={err}')
