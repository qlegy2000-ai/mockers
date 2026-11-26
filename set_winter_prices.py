#!/usr/bin/env python3
"""
Winter garments move to a single price with no discount shown.

  Hoodie      1599.00
  Sweatshirt  1499.00

Those were previously the compare-at values, so compare-at is cleared: leaving it
equal to the price makes Shopify render a struck-through price identical to the
live one and a 0% badge.

Summer garments are not touched. SHOP and TOKEN from the environment.
--run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
PRICE = {"Hoodie": "1599.00", "Sweatshirt": "1499.00"}

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
  variants(first:250){ nodes{ id price compareAtPrice } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

work, before = [], collections.Counter()
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in PRICE:
        continue
    ups = []
    for v in r["variants"]["nodes"]:
        before[(st, v["price"], v["compareAtPrice"])] += 1
        if v["price"] != PRICE[st] or v["compareAtPrice"] is not None:
            ups.append({"id": v["id"], "price": PRICE[st], "compareAtPrice": None})
    if ups:
        work.append({"id": r["id"], "handle": r["handle"], "style": st, "ups": ups})

print('current:')
for (st, p, c), n in before.most_common():
    print(f'   {st:<12} price {p:<10} compare-at {str(c):<10} {n:>5} variants')
print('\ntarget:')
for st, p in PRICE.items():
    print(f'   {st:<12} price {p:<10} compare-at cleared')
print(f'\nproducts to update : {len(work)}')
print(f'variants to update : {sum(len(w["ups"]) for w in work)}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

M = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkUpdate(productId:$productId, variants:$variants){ userErrors{ field message } } }"""
ok = err = 0
for i, w in enumerate(work, 1):
    for j in range(0, len(w["ups"]), 100):
        g = gql(M, {"productId": w["id"], "variants": w["ups"][j:j + 100]})["data"]["productVariantsBulkUpdate"]
        if g["userErrors"]:
            err += 1; print('  failed', w["handle"], g["userErrors"][:1])
        else:
            ok += len(w["ups"][j:j + 100])
    if i % 25 == 0:
        print(f'  ...{i}/{len(work)} products, {ok} variants', flush=True)
print(f'\nUPDATED {ok} variants   errors={err}')
