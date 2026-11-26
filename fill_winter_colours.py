#!/usr/bin/env python3
"""
Fill every hoodie and sweatshirt out to its full five-colour range.

  Hoodie      Black, Offwhite, Purple, Aegean Blue, Iron Grey
  Sweatshirt  Black, Offwhite, Dark Green, Dark Blue, Beetroot Purple

Missing colours are a leftover of the old catalogue, where a design was listed in
whatever subset happened to be photographed. The garment is made in all five, so
all five are offered.

THE OFFWHITE RULE
-----------------
Offwhite (#eee3cc) is a cream garment. A design printed in white ink disappears on
it, so a white-artwork design is sold in the other four colours only. This is a
per-DESIGN rule, not a per-garment one: it applies to that design's hoodie and its
sweatshirt alike.

WHITE_ARTWORK below was settled by looking at the real mockups, not by guessing from
the design tile. Two things the tile alone gets wrong:

  * White inside a dark printed shape is a KNOCKOUT - the garment colour shows
    through and it reads on any colour. wish-you-were-beer is white text inside a
    black badge and prints fine on cream.
  * Mockers re-colour the artwork per garment. breaking-sad, capitalism,
    i-love-your-personality and see-right-through-you look like white text on their
    dark tile but ship in green/teal on the cream garment.

So a design only lands in WHITE_ARTWORK when white ink sits directly on the garment
with no coloured version in evidence.

Sizes, price, stock policy and SKU shape are copied from the variants the product
already has. No image is attached - no mockup exists for a colour that was never
photographed; reports/winter_missing_images.csv tracks what still needs shooting.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv

RANGE = {
    "Hoodie":     ["Black", "Offwhite", "Purple", "Aegean Blue", "Iron Grey"],
    "Sweatshirt": ["Black", "Offwhite", "Dark Green", "Dark Blue", "Beetroot Purple"],
}

# designs whose artwork is white ink straight onto the garment - no Offwhite
WHITE_ARTWORK = {
    "andy", "dear-music", "if-only", "illegal", "kill-bic", "millennials",
    "national-psychotic", "paranoid", "pros-cons", "trans-parent",
}

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
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
 nodes{ id handle status
  design: metafield(namespace:"custom",key:"design_id"){value}
  style:  metafield(namespace:"custom",key:"style"){value}
  options{ id name optionValues{ id name } }
  variants(first:250){ nodes{ id price compareAtPrice selectedOptions{name value} } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

work = []
per_colour = collections.Counter()
withheld = []
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in RANGE or r["status"] != "ACTIVE":
        continue
    vs = r["variants"]["nodes"]
    if not vs:
        continue
    design = (r["design"] or {}).get("value") or r["handle"]
    have = {next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color") for v in vs}
    sizes = {next(o["value"] for o in v["selectedOptions"] if o["name"] == "Size") for v in vs}
    sizes = [z for z in SIZE_ORDER if z in sizes] + sorted(s for s in sizes if s not in SIZE_ORDER)
    price, cmp_ = vs[0]["price"], vs[0]["compareAtPrice"]

    todo = []
    for c in RANGE[st]:
        if c in have:
            continue
        if c == "Offwhite" and design in WHITE_ARTWORK:
            withheld.append((r["handle"], design))
            continue
        todo.append(c)
    if not todo:
        continue

    variants = []
    for c in todo:
        per_colour[c] += len(sizes)
        code = COLOUR_ABBR.get(c, c[:3].upper())
        for z in sizes:
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
    work.append({"id": r["id"], "handle": r["handle"], "style": st,
                 "colours": todo, "sizes": sizes, "variants": variants,
                 "options": r["options"]})

print(f'winter products to fill : {len(work)}')
print(f'colour slots to add     : {sum(len(w["colours"]) for w in work)}')
print(f'variants to create      : {sum(len(w["variants"]) for w in work)}')
print('\nby colour:')
for c, n in per_colour.most_common():
    print(f'   {c:<18}{n:>4}')
print(f'\nOffwhite withheld on {len(withheld)} products '
      f'({len({d for _, d in withheld})} white-artwork designs)')
for h, _ in sorted(withheld):
    print('   ', h)
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
        err += 1; print('  create failed', w["handle"], g["userErrors"][:2]); continue
    ok += len(w["variants"])
    if i % 20 == 0:
        print(f'  ...{i}/{len(work)} products, {ok} variants', flush=True)
print(f'\nCREATED {ok} variants   errors={err}')

# new option values are appended, so both axes need putting back in order
print('\nreordering options...')
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
    st = (r["style"] or {}).get("value")
    if st not in RANGE:
        continue
    opts, changed = [], False
    for o in r["options"]:
        have = o["optionValues"]
        canon = SIZE_ORDER if o["name"] == "Size" else RANGE[st]
        want = [v for z in canon for v in have if v["name"] == z] + \
               [v for v in have if v["name"] not in canon]
        if [v["name"] for v in want] != [v["name"] for v in have]:
            changed = True
        opts.append({"id": o["id"], "values": [{"id": v["id"]} for v in want]})
    if not changed:
        continue
    g = gql(R, {"productId": r["id"], "options": opts})["data"]["productOptionsReorder"]
    if g["userErrors"]:
        print('  reorder failed', r["handle"], g["userErrors"][:1])
    else:
        rk += 1
print(f'reordered {rk} products')
