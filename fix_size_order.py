#!/usr/bin/env python3
"""
Put the Size option values back in size order.

Shopify renders option values in stored order, and every product came out of the
import alphabetical - 2XL, L, M, S, XL, XS - so the picker reads "L M S XL".
This reorders them to XS, S, M, L, XL, 2XL. The Color option keeps whatever
order it already has.

Only the display order changes. No variant, price, SKU or image is touched.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
ORDER = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]

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

Q = '''query($c:String){ products(first:100,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ id handle style: metafield(namespace:"custom",key:"style"){value}
  options{ id name optionValues{ id name } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

work, unknown = [], collections.Counter()
for r in rows:
    if not (r["style"] or {}).get("value"):
        continue
    size = next((o for o in r["options"] if o["name"] == "Size"), None)
    if not size:
        continue
    have = size["optionValues"]
    for v in have:
        if v["name"] not in ORDER:
            unknown[v["name"]] += 1
    # known sizes in canonical order, then anything unrecognised, order kept
    known = [v for z in ORDER for v in have if v["name"] == z]
    rest = [v for v in have if v["name"] not in ORDER]
    want = known + rest
    if [v["name"] for v in want] == [v["name"] for v in have]:
        continue
    # the mutation rejects a partial list - every option must be sent, so Color
    # is passed through in whatever order it already has
    opts = []
    for o in r["options"]:
        vals = want if o["name"] == "Size" else o["optionValues"]
        opts.append({"id": o["id"], "values": [{"id": v["id"]} for v in vals]})
    work.append({"id": r["id"], "handle": r["handle"],
                 "from": [v["name"] for v in have],
                 "to": [v["name"] for v in want],
                 "options": opts})

print(f'products needing reorder : {len(work)}')
if unknown:
    print(f'unrecognised size values : {dict(unknown)}')
for w in work[:5]:
    print(f'   {w["handle"]:<44} {w["from"]} -> {w["to"]}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

M = """mutation($productId:ID!,$options:[OptionReorderInput!]!){
 productOptionsReorder(productId:$productId, options:$options){
  userErrors{ field message } } }"""
ok = err = 0
for i, w in enumerate(work, 1):
    g = gql(M, {"productId": w["id"], "options": w["options"]})["data"]["productOptionsReorder"]
    if g["userErrors"]:
        err += 1; print('  failed', w["handle"], g["userErrors"][:1])
    else:
        ok += 1
    if i % 50 == 0:
        print(f'  ...{i}/{len(work)}', flush=True)
print(f'\nREORDERED {ok} products   errors={err}')
