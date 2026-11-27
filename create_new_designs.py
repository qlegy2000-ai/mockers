#!/usr/bin/env python3
"""
Create brand-new designs as Hoodie + Sweatshirt products, built exactly like the
existing catalogue (create_missing_products.py): same title pattern, tags,
custom.* metafields, prices, colour/size ranges, SKUs, untracked + CONTINUE.

Products are created as DRAFT and NOT published: the owner reviews them (and the
mockups get attached) before they go live.

  SHOP=... TOKEN=proxy-injected python3 create_new_designs.py          # dry run
  SHOP=... TOKEN=proxy-injected python3 create_new_designs.py --run    # create
"""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optimize_catalog import PRICE_BOOK, GARMENT_SIZES, WINTER_RANGE

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv

# design_id -> design title (as printed). Approved by the owner 27 Nov 2026.
DESIGNS = {
    "booooobs":       "BOOOOOBS!",
    "nice-try-china": "NICE TRY CHINA!",
}
STYLES = ["Hoodie", "Sweatshirt"]
STYLE_ABBR = {"Hoodie": "HOD", "Sweatshirt": "SWT"}
COLOUR_ABBR = {"Black": "BLK", "Offwhite": "OFW", "Purple": "PUR", "Aegean Blue": "AEG",
               "Iron Grey": "IGY", "Dark Green": "DGN", "Dark Blue": "DBL", "Beetroot Purple": "BPR"}
# Same copy the catalogue uses on its winter garments.
BODY = ('<p>"Warning: Wearing this may result in excessive laughter, envy, and compliments. '
        'Handle with sarcasm and be prepared for a surge in attention."</p>')


def gql(q, v=None):
    for _ in range(10):
        req = urllib.request.Request(f"https://{SHOP}/admin/api/2026-07/graphql.json",
                                     data=json.dumps({"query": q, "variables": v or {}}).encode(),
                                     headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
        o = json.load(urllib.request.urlopen(req))
        if o.get("errors") and "THROTTLED" in json.dumps(o["errors"]):
            time.sleep(5); continue
        if o.get("errors"):
            raise SystemExit("GQL " + json.dumps(o["errors"])[:300])
        return o
    raise SystemExit("throttled out")


plan = []
for did, dtitle in DESIGNS.items():
    for st in STYLES:
        handle = f"{did}-{st.lower()}"
        exists = gql('query($h:String!){ productByHandle(handle:$h){ id } }', {"h": handle})["data"]["productByHandle"]
        if exists:
            print("already exists, skipping:", handle); continue
        plan.append({"design": did, "dtitle": dtitle, "style": st, "handle": handle,
                     "title": f"{dtitle} {st}", "colours": WINTER_RANGE[st], "sizes": GARMENT_SIZES[st]})

for p in plan:
    price, cmp_ = PRICE_BOOK[p["style"]]
    print(f'{p["handle"]:<28} "{p["title"]}"  {len(p["colours"])} colours x {len(p["sizes"])} sizes  EGP {price}  DRAFT')
if DRY:
    print("\nDRY RUN - nothing written. add --run to execute."); sys.exit()

M_CREATE = """mutation($product: ProductCreateInput!) { productCreate(product: $product) {
  product{ id handle } userErrors{ field message } } }"""
M_VARIANTS = """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants) { productVariants{ id } userErrors{ field message } } }"""
M_VUPDATE = """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) { productVariants{ id } userErrors{ field message } } }"""
Q_SEED = """query($id: ID!){ product(id:$id){ variants(first:250){ nodes{ id selectedOptions{name value} } } } }"""

created = []
for p in plan:
    price, cmp_ = PRICE_BOOK[p["style"]]
    tags = sorted({f"design:{p['design']}", p["style"].lower(), p["dtitle"].lower(),
                   "season:winter", f"style:{p['style'].lower()}"})
    r = gql(M_CREATE, {"product": {
        "handle": p["handle"], "title": p["title"], "descriptionHtml": BODY, "vendor": "Mockers",
        "productType": p["style"], "tags": tags, "status": "DRAFT",
        "metafields": [
            {"namespace": "custom", "key": "design_id", "type": "single_line_text_field", "value": p["design"]},
            {"namespace": "custom", "key": "design_title", "type": "single_line_text_field", "value": p["dtitle"]},
            {"namespace": "custom", "key": "style", "type": "single_line_text_field", "value": p["style"]},
            {"namespace": "custom", "key": "season", "type": "single_line_text_field", "value": "winter"}],
        "productOptions": [{"name": "Color", "values": [{"name": c} for c in p["colours"]]},
                           {"name": "Size", "values": [{"name": s} for s in p["sizes"]]}],
    }})["data"]["productCreate"]
    if r["userErrors"]:
        print("FAILED", p["handle"], r["userErrors"]); continue
    pid = r["product"]["id"]
    first = (p["colours"][0], p["sizes"][0])
    vin, seed = [], None
    for c in p["colours"]:
        for z in p["sizes"]:
            code = COLOUR_ABBR[c]
            v = {"optionValues": [{"optionName": "Color", "name": c}, {"optionName": "Size", "name": z}],
                 "price": price, "compareAtPrice": cmp_, "inventoryPolicy": "CONTINUE",
                 "inventoryItem": {"sku": f"MK-{STYLE_ABBR[p['style']]}-{p['design'].upper()}-{code}-{z}",
                                   "tracked": False, "requiresShipping": True},
                 "metafields": [{"namespace": "custom", "key": "blank_sku", "type": "single_line_text_field",
                                 "value": f"{STYLE_ABBR[p['style']]}-{code}-{z}"}]}
            if (c, z) == first:
                seed = v
            else:
                vin.append(v)
    vr = gql(M_VARIANTS, {"productId": pid, "variants": vin})["data"]["productVariantsBulkCreate"]
    if vr["userErrors"]:
        print("FAILED variants", p["handle"], vr["userErrors"]); continue
    seeded = gql(Q_SEED, {"id": pid})["data"]["product"]["variants"]["nodes"]
    sid = next(v["id"] for v in seeded
               if {o["name"]: o["value"] for o in v["selectedOptions"]} == {"Color": first[0], "Size": first[1]})
    seed = dict(seed); seed.pop("optionValues"); seed["id"] = sid
    ur = gql(M_VUPDATE, {"productId": pid, "variants": [seed]})["data"]["productVariantsBulkUpdate"]
    if ur["userErrors"]:
        print("FAILED seed", p["handle"], ur["userErrors"]); continue
    created.append({"handle": p["handle"], "id": pid})
    print("created DRAFT", p["handle"], pid)
print(f"\n{len(created)} products created as DRAFT (not published).")
