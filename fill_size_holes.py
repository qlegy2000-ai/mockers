#!/usr/bin/env python3
"""
Close any (colour x size) hole left in the winter grid.

fill_winter_colours.py only creates variants for colours a product was missing
entirely. A colour that already existed but lacked a size keeps its gap, so a
product can end up selling 2XL in one colour and not the rest. This fills those,
copying price, stock policy and SKU shape from the product's own variants.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
WINTER = {"Hoodie", "Sweatshirt"}
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
ABBR = {"Hoodie": "HOD", "Sweatshirt": "SWT"}
COLOUR_ABBR = {
    "Black": "BLK", "Offwhite": "OFW", "Purple": "PUR", "Aegean Blue": "AEG",
    "Iron Grey": "IGY", "Dark Green": "DGN", "Dark Blue": "DBL",
    "Beetroot Purple": "BPR", "White": "WHT", "Burgundy": "BRG",
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

Q = '''query($c:String){ products(first:50,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ id handle status
  design: metafield(namespace:"custom",key:"design_id"){value}
  style:  metafield(namespace:"custom",key:"style"){value}
  options{ id name optionValues{ id name } }
  variants(first:250){ nodes{ price compareAtPrice selectedOptions{name value} } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

work = []
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in WINTER or r["status"] != "ACTIVE":
        continue
    vs = r["variants"]["nodes"]
    if not vs:
        continue
    grid = collections.defaultdict(set)
    for v in vs:
        c = next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color")
        z = next(o["value"] for o in v["selectedOptions"] if o["name"] == "Size")
        grid[c].add(z)
    allsz = set().union(*grid.values())
    holes = [(c, z) for c in grid for z in allsz if z not in grid[c]]
    if not holes:
        continue
    design = (r["design"] or {}).get("value") or r["handle"]
    price, cmp_ = vs[0]["price"], vs[0]["compareAtPrice"]
    variants = []
    for c, z in holes:
        code = COLOUR_ABBR.get(c, c[:3].upper())
        variants.append({
            "optionValues": [{"optionName": "Color", "name": c},
                             {"optionName": "Size", "name": z}],
            "price": price, "compareAtPrice": cmp_,
            "inventoryPolicy": "CONTINUE",
            "inventoryItem": {"sku": f"MK-{ABBR[st]}-{design.upper()}-{code}-{z}",
                              "tracked": False},
            "metafields": [{"namespace": "custom", "key": "blank_sku",
                            "type": "single_line_text_field",
                            "value": f"{ABBR[st]}-{code}-{z}"}],
        })
    work.append({"id": r["id"], "handle": r["handle"], "holes": holes,
                 "variants": variants, "options": r["options"]})

print(f'products with holes : {len(work)}')
for w in work:
    print(f'   {w["handle"]:<36}{sorted(w["holes"])}')
print(f'variants to create  : {sum(len(w["variants"]) for w in work)}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

C = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkCreate(productId:$productId, variants:$variants){
  productVariants{ id } userErrors{ field message } } }"""
R = """mutation($productId:ID!,$options:[OptionReorderInput!]!){
 productOptionsReorder(productId:$productId, options:$options){ userErrors{ field message } } }"""
ok = err = 0
for w in work:
    g = gql(C, {"productId": w["id"], "variants": w["variants"]})["data"]["productVariantsBulkCreate"]
    if g["userErrors"]:
        err += 1; print('  failed', w["handle"], g["userErrors"][:2]); continue
    ok += len(w["variants"])
    opts = []
    for o in w["options"]:
        if o["name"] != "Size":
            opts.append({"id": o["id"], "values": [{"id": v["id"]} for v in o["optionValues"]]})
            continue
        have = o["optionValues"]
        want = [v for z in SIZE_ORDER for v in have if v["name"] == z] + \
               [v for v in have if v["name"] not in SIZE_ORDER]
        opts.append({"id": o["id"], "values": [{"id": v["id"]} for v in want]})
    gql(R, {"productId": w["id"], "options": opts})
print(f'\nCREATED {ok} variants   errors={err}')
