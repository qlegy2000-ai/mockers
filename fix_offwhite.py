#!/usr/bin/env python3
"""
Offwhite is a winter-only garment colour.

Regular Fit T-Shirt, Oversized Light-Soft and Oversized Heavy Premium are only
made in White - they never came in Offwhite. Hoodie and Sweatshirt keep Offwhite.

Two cases on the summer garments:
  * the product has Offwhite and no White  -> rename the option value in place.
    Variants, SKUs and images are preserved; only the label changes.
  * the product has both                   -> the Offwhite variants are not real,
    so they are deleted and the existing White ones kept.

SKUs and blank_sku carry the colour code, so -OFW- becomes -WHT- on anything renamed.

Run with SHOP and TOKEN in the environment. Add --run to execute; without it this
only reports.
"""
import json, os, sys, time, urllib.request

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
WINTER = {"Hoodie", "Sweatshirt"}
SUMMER = {"Regular Fit T-Shirt", "Oversized Light-Soft", "Oversized Heavy Premium"}

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
  options{ id name optionValues{ id name } }
  variants(first:250){ nodes{ id sku selectedOptions{name value}
    metafields(first:5){ nodes{ namespace key value } } } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

renames, merges = [], []
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in SUMMER:
        continue
    co = next((o for o in r["options"] if o["name"] == "Color"), None)
    if not co:
        continue
    vals = {v["name"]: v["id"] for v in co["optionValues"]}
    if "Offwhite" not in vals:
        continue
    offv = [v for v in r["variants"]["nodes"]
            if any(o["name"] == "Color" and o["value"] == "Offwhite" for o in v["selectedOptions"])]
    rec = {"id": r["id"], "handle": r["handle"], "optId": co["id"],
           "valId": vals["Offwhite"], "variants": offv}
    (merges if "White" in vals else renames).append(rec)

print(f'summer products to RENAME : {len(renames)}  ({sum(len(x["variants"]) for x in renames)} variants relabelled)')
print(f'summer products to MERGE  : {len(merges)}  ({sum(len(x["variants"]) for x in merges)} Offwhite variants deleted)')
winter = sum(1 for r in rows
             if (r["style"] or {}).get("value") in WINTER
             and any(o["name"] == "Color" and any(v["name"] == "Offwhite" for v in o["optionValues"])
                     for o in r["options"]))
print(f'winter products untouched : {winter}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

REN = """mutation($productId:ID!,$option:OptionUpdateInput!,$vals:[OptionValueUpdateInput!]){
 productOptionUpdate(productId:$productId, option:$option, optionValuesToUpdate:$vals,
   variantStrategy: LEAVE_AS_IS){ userErrors{ field message } } }"""
DEL = """mutation($productId:ID!,$ids:[ID!]!){
 productVariantsBulkDelete(productId:$productId, variantsIds:$ids){ userErrors{ field message } } }"""
UPD = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkUpdate(productId:$productId, variants:$variants){ userErrors{ field message } } }"""
MFS = 'mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ message } } }'

ren_ok = sku_ok = del_ok = err = 0
for x in renames:
    g = gql(REN, {"productId": x["id"], "option": {"id": x["optId"]},
                  "vals": [{"id": x["valId"], "name": "White"}]})["data"]["productOptionUpdate"]
    if g["userErrors"]:
        err += 1; print('  rename failed', x["handle"], g["userErrors"][:1]); continue
    ren_ok += 1
    # colour code lives in the SKU and in blank_sku
    ups = [{"id": v["id"], "inventoryItem": {"sku": v["sku"].replace("-OFW-", "-WHT-")}}
           for v in x["variants"] if v["sku"] and "-OFW-" in v["sku"]]
    if ups:
        g2 = gql(UPD, {"productId": x["id"], "variants": ups})["data"]["productVariantsBulkUpdate"]
        if not g2["userErrors"]:
            sku_ok += len(ups)
    mfs = []
    for v in x["variants"]:
        b = next((m for m in v["metafields"]["nodes"]
                  if m["namespace"] == "custom" and m["key"] == "blank_sku"), None)
        if b and "-OFW-" in b["value"]:
            mfs.append({"ownerId": v["id"], "namespace": "custom", "key": "blank_sku",
                        "type": "single_line_text_field",
                        "value": b["value"].replace("-OFW-", "-WHT-")})
    for i in range(0, len(mfs), 25):
        gql(MFS, {"m": mfs[i:i + 25]})

for x in merges:
    ids = [v["id"] for v in x["variants"]]
    g = gql(DEL, {"productId": x["id"], "ids": ids})["data"]["productVariantsBulkDelete"]
    if g["userErrors"]:
        err += 1; print('  merge failed', x["handle"], g["userErrors"][:1]); continue
    del_ok += len(ids)

print(f'\nrenamed products      : {ren_ok}')
print(f'SKUs updated          : {sku_ok}')
print(f'variants deleted      : {del_ok}')
print(f'errors                : {err}')
