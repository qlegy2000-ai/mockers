#!/usr/bin/env python3
"""
Populate products whose variants failed to create.

productCreate with productOptions does not leave the product empty - it creates one
variant from the FIRST value of each option (here Black / XS) at price 0.00 with no
SKU. productVariantsBulkCreate then rejects the whole batch with "The variant
'Black / XS' already exists", so the product is left live with a single free variant.

This builds the full grid around that placeholder: every combination except the one
that exists is created, and the placeholder itself is updated in place with the real
price, SKU, stock policy and blank_sku.

Run it straight after create_missing_products.py. Safe to re-run - a product that
already has its full grid is skipped.

--handles is REQUIRED and takes a file of product handles, one per line. Without it
the script would also "repair" legacy products whose option grid has always been
sparse - a tee that lists seven colours but was only ever built in some of them.
Those gaps are deliberate until the range for that garment is agreed, so the repair
must only ever touch the products it just made.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optimize_catalog import PRICE_BOOK

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
if "--handles" not in sys.argv:
    raise SystemExit("--handles <file> is required; see the docstring")
ONLY = {l.strip() for l in open(sys.argv[sys.argv.index("--handles") + 1]) if l.strip()}
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
STYLE_ABBR = {"Hoodie": "HOD", "Sweatshirt": "SWT", "Regular Fit T-Shirt": "RFT",
              "Oversized Light-Soft": "OLS", "Oversized Heavy Premium": "OHP"}
COLOUR_ABBR = {
    "Black": "BLK", "Offwhite": "OFW", "Purple": "PUR", "Aegean Blue": "AEG",
    "Iron Grey": "IGY", "Dark Green": "DGN", "Dark Blue": "DBL",
    "Beetroot Purple": "BPR", "White": "WHT", "Burgundy": "BRG",
    "Cashmere Pink": "CPK", "Beige Cafe": "BCF", "Pink": "PNK",
    "Pistache Green": "PSG", "Earth Green": "ERG", "Royal Dark Green": "RDG", "Beige": "BEI",
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
  variants(first:250){ nodes{ id price selectedOptions{name value} } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

work = []
for r in rows:
    if r["handle"] not in ONLY:
        continue
    st = (r["style"] or {}).get("value")
    if st not in PRICE_BOOK:
        continue
    opts = {o["name"]: [v["name"] for v in o["optionValues"]] for o in r["options"]}
    if "Color" not in opts or "Size" not in opts:
        continue
    full = {(c, z) for c in opts["Color"] for z in opts["Size"]}
    have = {(next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color"),
             next(o["value"] for o in v["selectedOptions"] if o["name"] == "Size")): v
            for v in r["variants"]["nodes"]}
    missing = sorted(full - set(have), key=lambda t: (opts["Color"].index(t[0]),
                                                      opts["Size"].index(t[1])))
    # a placeholder is a variant still sitting at 0.00
    placeholders = {k: v for k, v in have.items() if v["price"] in ("0.00", "0")}
    if not missing and not placeholders:
        continue
    work.append({"id": r["id"], "handle": r["handle"], "style": st,
                 "design": (r["design"] or {}).get("value") or r["handle"],
                 "missing": missing, "placeholders": placeholders,
                 "options": r["options"], "opts": opts})

print(f'handles supplied        : {len(ONLY)}')
print(f'products needing repair : {len(work)}')
print(f'variants to create      : {sum(len(w["missing"]) for w in work)}')
print(f'placeholders to fix     : {sum(len(w["placeholders"]) for w in work)}')
for w in work[:5]:
    print(f'   {w["handle"]:<40} +{len(w["missing"]):>3} variants, '
          f'{len(w["placeholders"])} placeholder')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

C = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkCreate(productId:$productId, variants:$variants){
  productVariants{ id } userErrors{ field message } } }"""
U = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkUpdate(productId:$productId, variants:$variants){
  productVariants{ id } userErrors{ field message } } }"""
R = """mutation($productId:ID!,$options:[OptionReorderInput!]!){
 productOptionsReorder(productId:$productId, options:$options){ userErrors{ field message } } }"""

def spec(style, design, c, z):
    code = COLOUR_ABBR.get(c, c[:3].upper())
    ab = STYLE_ABBR[style]
    return (f"MK-{ab}-{design.upper()}-{code}-{z}", f"{ab}-{code}-{z}")

made = fixed = err = 0
for i, w in enumerate(work, 1):
    price, cmp_ = PRICE_BOOK[w["style"]]
    if w["missing"]:
        vin = []
        for c, z in w["missing"]:
            sku, blank = spec(w["style"], w["design"], c, z)
            vin.append({
                "optionValues": [{"optionName": "Color", "name": c},
                                 {"optionName": "Size", "name": z}],
                "price": price, "compareAtPrice": cmp_, "inventoryPolicy": "CONTINUE",
                "inventoryItem": {"sku": sku, "tracked": False, "requiresShipping": True},
                "metafields": [{"namespace": "custom", "key": "blank_sku",
                                "type": "single_line_text_field", "value": blank}],
            })
        for j in range(0, len(vin), 100):
            g = gql(C, {"productId": w["id"], "variants": vin[j:j+100]})["data"]["productVariantsBulkCreate"]
            if g["userErrors"]:
                err += 1; print('  create failed', w["handle"], g["userErrors"][:1]); break
            made += len(vin[j:j+100])
    if w["placeholders"]:
        upd = []
        for (c, z), v in w["placeholders"].items():
            sku, blank = spec(w["style"], w["design"], c, z)
            upd.append({"id": v["id"], "price": price, "compareAtPrice": cmp_,
                        "inventoryPolicy": "CONTINUE",
                        "inventoryItem": {"sku": sku, "tracked": False, "requiresShipping": True},
                        "metafields": [{"namespace": "custom", "key": "blank_sku",
                                        "type": "single_line_text_field", "value": blank}]})
        g = gql(U, {"productId": w["id"], "variants": upd})["data"]["productVariantsBulkUpdate"]
        if g["userErrors"]:
            err += 1; print('  update failed', w["handle"], g["userErrors"][:1])
        else:
            fixed += len(upd)
    # creates append new option values, so put both axes back in order
    opts = []
    for o in w["options"]:
        have = o["optionValues"]
        canon = SIZE_ORDER if o["name"] == "Size" else w["opts"]["Color"]
        want = [v for x in canon for v in have if v["name"] == x] + \
               [v for v in have if v["name"] not in canon]
        opts.append({"id": o["id"], "values": [{"id": v["id"]} for v in want]})
    gql(R, {"productId": w["id"], "options": opts})
    if i % 10 == 0:
        print(f'  ...{i}/{len(work)}  created={made} fixed={fixed}', flush=True)

print(f'\nCREATED {made} variants, FIXED {fixed} placeholders, errors={err}')
