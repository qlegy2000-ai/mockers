#!/usr/bin/env python3
"""
Add XS back to every hoodie and sweatshirt, for every colour the product carries.

Each new variant inherits the product's existing price, stock policy and the
image already used for that colour, and gets the usual SKU and blank_sku.
Afterwards the Size option is reordered so XS sits first.

Summer garments are not touched.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
WINTER = {"Hoodie", "Sweatshirt"}
ADD = "XS"
ORDER = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
ABBR = {"Hoodie": "HOD", "Sweatshirt": "SWT"}
COLOUR_ABBR = {
    "Black": "BLK", "Offwhite": "OFW", "Purple": "PUR", "Aegean Blue": "AEG",
    "Iron Grey": "IGY", "Dark Green": "DGN", "Dark Blue": "DBL",
    "Beetroot Purple": "BPR", "White": "WHT", "Burgundy": "BRG",
    "Cashmere Pink": "CPK", "Beige Cafe": "BCF", "Pink": "PNK",
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
 nodes{ id handle
  design: metafield(namespace:"custom",key:"design_id"){value}
  style:  metafield(namespace:"custom",key:"style"){value}
  options{ id name optionValues{ id name } }
  variants(first:250){ nodes{ id price compareAtPrice selectedOptions{name value}
    media(first:1){ nodes{ id } } } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

work = []
per = collections.Counter()
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in WINTER:
        continue
    vs = r["variants"]["nodes"]
    if not vs:
        continue
    have_xs = {next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color")
               for v in vs
               if any(o["name"] == "Size" and o["value"] == ADD for o in v["selectedOptions"])}
    colours, media_for, price, cmp_ = [], {}, vs[0]["price"], vs[0]["compareAtPrice"]
    for v in vs:
        c = next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color")
        if c not in colours:
            colours.append(c)
        if c not in media_for and v["media"]["nodes"]:
            media_for[c] = v["media"]["nodes"][0]["id"]
    todo = [c for c in colours if c not in have_xs]
    if not todo:
        continue
    per[st] += len(todo)
    design = (r["design"] or {}).get("value") or r["handle"]
    variants = []
    for c in todo:
        code = COLOUR_ABBR.get(c, c[:3].upper())
        v = {"optionValues": [{"optionName": "Color", "name": c},
                              {"optionName": "Size", "name": ADD}],
             "price": price, "compareAtPrice": cmp_,
             "inventoryPolicy": "CONTINUE",
             "inventoryItem": {"sku": f"MK-{ABBR[st]}-{design.upper()}-{code}-{ADD}",
                               "tracked": False},
             "metafields": [{"namespace": "custom", "key": "blank_sku",
                             "type": "single_line_text_field",
                             "value": f"{ABBR[st]}-{code}-{ADD}"}]}
        if c in media_for:
            v["mediaId"] = media_for[c]
        variants.append(v)
    size_opt = next((o for o in r["options"] if o["name"] == "Size"), None)
    work.append({"id": r["id"], "handle": r["handle"], "style": st,
                 "variants": variants, "options": r["options"], "sizeOpt": size_opt})

print(f'winter products needing {ADD} : {len(work)}')
for st in ("Hoodie", "Sweatshirt"):
    print(f'   {st:<12} {per[st]:>4} variants')
print(f'variants to create : {sum(per.values())}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

C = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkCreate(productId:$productId, variants:$variants){
  productVariants{ id } userErrors{ field message } } }"""
R = """mutation($productId:ID!,$options:[OptionReorderInput!]!){
 productOptionsReorder(productId:$productId, options:$options){ userErrors{ field message } } }"""

ok = err = 0
for i, w in enumerate(work, 1):
    g = gql(C, {"productId": w["id"], "variants": w["variants"]})["data"]["productVariantsBulkCreate"]
    if g["userErrors"]:
        err += 1; print('  create failed', w["handle"], g["userErrors"][:1]); continue
    ok += len(w["variants"])
    if i % 25 == 0:
        print(f'  ...{i}/{len(work)} products, {ok} variants', flush=True)
print(f'\nCREATED {ok} {ADD} variants   errors={err}')

# XS was just appended, so put the sizes back in order
print('reordering sizes...')
cur, rows2 = None, []
while True:
    d = gql('''query($c:String){ products(first:100,after:$c){ pageInfo{hasNextPage endCursor}
     nodes{ id handle style: metafield(namespace:"custom",key:"style"){value}
      options{ id name optionValues{ id name } } } } }''', {"c": cur})["data"]["products"]
    rows2 += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]
rk = 0
for r in rows2:
    if (r["style"] or {}).get("value") not in WINTER:
        continue
    so = next((o for o in r["options"] if o["name"] == "Size"), None)
    if not so:
        continue
    have = so["optionValues"]
    want = [v for z in ORDER for v in have if v["name"] == z] + \
           [v for v in have if v["name"] not in ORDER]
    if [v["name"] for v in want] == [v["name"] for v in have]:
        continue
    opts = [{"id": o["id"],
             "values": [{"id": v["id"]} for v in (want if o["name"] == "Size" else o["optionValues"])]}
            for o in r["options"]]
    g = gql(R, {"productId": r["id"], "options": opts})["data"]["productOptionsReorder"]
    if not g["userErrors"]:
        rk += 1
print(f'reordered {rk} products')
