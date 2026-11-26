#!/usr/bin/env python3
"""
Give every design the full five-garment set.

A design is one artwork sold as five products - Regular Fit T-Shirt, Oversized
Light-Soft, Oversized Heavy Premium, Sweatshirt, Hoodie. The old catalogue only
listed whichever garments had been photographed, so 33 of the 78 designs are
short one or more. This creates the missing products from a sibling of the same
design, so the copy, the artwork and the metafield wiring match what is already
live.

Colours and sizes come from the agreed range for the garment, NOT from whatever
the sibling happens to carry - the sibling may itself be a legacy product with an
arbitrary colour set. Winter additionally honours the Offwhite white-artwork rule
(see optimize_catalog.WHITE_ARTWORK).

The only image attached is the design artwork tile, taken from the sibling's first
media. Garment mockups do not exist for a product that has never been photographed;
reports/ tracks what needs shooting.

Collections are rule-based on product type and tags, so a new product joins them on
its own. Lead tags are not set here - run apply_lead_tags.py and tag_season_leads.py
afterwards, then set_sibling_styles.py so the PDP garment switcher sees the new
products.

SHOP and TOKEN from the environment.
  --season winter|summer|all   which garments to fill   (default winter)
  --run                        execute; otherwise reports only
"""
import json, os, re, sys, time, urllib.request, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optimize_catalog import (WINTER_RANGE, SUMMER_RANGE, GARMENT_SIZES, WHITE_ARTWORK,
                              PRICE_BOOK, garment_colours)

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
SEASON = "winter"
if "--season" in sys.argv:
    SEASON = sys.argv[sys.argv.index("--season") + 1]

STYLES = ["Regular Fit T-Shirt", "Oversized Light-Soft", "Oversized Heavy Premium",
          "Sweatshirt", "Hoodie"]
SEASON_OF = {"Regular Fit T-Shirt": "summer", "Oversized Light-Soft": "summer",
             "Oversized Heavy Premium": "summer", "Sweatshirt": "winter", "Hoodie": "winter"}

# Ranges and sizes live in optimize_catalog so every script agrees on them.
SIZES = GARMENT_SIZES
STYLE_ABBR = {"Hoodie": "HOD", "Sweatshirt": "SWT", "Regular Fit T-Shirt": "RFT",
              "Oversized Light-Soft": "OLS", "Oversized Heavy Premium": "OHP"}
COLOUR_ABBR = {
    "Black": "BLK", "Offwhite": "OFW", "Purple": "PUR", "Aegean Blue": "AEG",
    "Iron Grey": "IGY", "Dark Green": "DGN", "Dark Blue": "DBL",
    "Beetroot Purple": "BPR", "White": "WHT", "Burgundy": "BRG",
    "Cashmere Pink": "CPK", "Beige Cafe": "BCF", "Pink": "PNK",
    "Pistache Green": "PSG", "Earth Green": "ERG", "Royal Dark Green": "RDG",
    "Beige": "BEI",
}
ONLINE_STORE = "gid://shopify/Publication/94733828138"   # what every live product uses

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

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

Q = '''query($c:String){ products(first:30,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ id handle title status vendor descriptionHtml
  design: metafield(namespace:"custom",key:"design_id"){value}
  dtitle: metafield(namespace:"custom",key:"design_title"){value}
  style:  metafield(namespace:"custom",key:"style"){value}
  media(first:1){nodes{ ... on MediaImage { image{url} } }} } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

live = [r for r in rows if r["status"] == "ACTIVE" and (r["style"] or {}).get("value") in STYLES]
by = collections.defaultdict(dict)
for r in live:
    by[(r["design"] or {}).get("value") or r["handle"]][r["style"]["value"]] = r
have_handles = {r["handle"] for r in rows}

wanted = [s for s in STYLES if SEASON in ("all", SEASON_OF[s])]
plan = []
for did, g in sorted(by.items()):
    sib = next(iter(g.values()))
    dtitle = (sib["dtitle"] or {}).get("value") or did.replace("-", " ").upper()
    for st in wanted:
        if st in g:
            continue
        handle = f"{did}-{slug(st)}"
        if handle in have_handles:
            print("  handle already exists, skipping:", handle); continue
        colours = garment_colours(did, st)
        sizes = SIZES[st]
        if not colours or not sizes:
            raise SystemExit(f"no agreed colour/size range for {st}")
        # the design artwork tile is the first media on every product
        art = sib["media"]["nodes"][0]["image"]["url"] if sib["media"]["nodes"] else None
        plan.append({
            "design": did, "style": st, "handle": handle,
            "title": f"{dtitle} {st}", "dtitle": dtitle,
            "vendor": sib["vendor"], "body": sib["descriptionHtml"],
            "season": SEASON_OF[st], "colours": colours, "sizes": sizes, "art": art,
            "from": sib["handle"],
        })

per = collections.Counter(p["style"] for p in plan)
print(f'season filter        : {SEASON}')
print(f'designs in catalogue : {len(by)}')
print(f'products to create   : {len(plan)}')
for s in STYLES:
    if per[s]:
        print(f'   {s:<26}{per[s]:>3}   {len(SIZES[s])} sizes')
print(f'variants to create   : {sum(len(p["colours"])*len(p["sizes"]) for p in plan)}')
noart = [p["handle"] for p in plan if not p["art"]]
if noart:
    print(f'!! no artwork tile on the sibling for {len(noart)}: {noart[:5]}')
off = [p["handle"] for p in plan if p["design"] in WHITE_ARTWORK]
print(f'pale colour withheld : {len(off)} {off}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    for p in plan[:8]:
        print(f'   {p["handle"]:<44} {len(p["colours"])}c x {len(p["sizes"])}s   from {p["from"]}')
    sys.exit()

M_CREATE = """mutation($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(product: $product, media: $media) {
    product{ id handle } userErrors{ field message } } }"""
M_VARIANTS = """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants) {
    productVariants{ id } userErrors{ field message } } }"""
M_VUPDATE = """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants{ id } userErrors{ field message } } }"""
M_PUBLISH = """mutation($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) { userErrors{ field message } } }"""
M_ACTIVATE = """mutation($input: ProductInput!) {
  productUpdate(input: $input) { product{ id status } userErrors{ field message } } }"""
Q_SEED = """query($id: ID!){ product(id:$id){
  variants(first:250){ nodes{ id selectedOptions{name value} } } } }"""

ok = fail = 0
created, failures = [], []
for i, p in enumerate(plan, 1):
    price, cmp_ = PRICE_BOOK[p["style"]]
    tags = sorted({f"design:{p['design']}", slug(p["style"]), p["dtitle"].lower(),
                   f"season:{p['season']}", f"style:{slug(p['style'])}"})
    media = ([{"originalSource": p["art"], "mediaContentType": "IMAGE", "alt": p["title"]}]
             if p["art"] else [])
    r = gql(M_CREATE, {"product": {
        "handle": p["handle"], "title": p["title"], "descriptionHtml": p["body"],
        # born as a DRAFT. If the variant calls fail the product is left unbuyable
        # rather than live at 0.00 - productCreate always makes a placeholder variant
        # with no price, and an ACTIVE product would be on sale for free in the gap.
        "vendor": p["vendor"], "productType": p["style"], "tags": tags, "status": "DRAFT",
        "metafields": [
            {"namespace": "custom", "key": "design_id",    "type": "single_line_text_field", "value": p["design"]},
            {"namespace": "custom", "key": "design_title", "type": "single_line_text_field", "value": p["dtitle"]},
            {"namespace": "custom", "key": "style",        "type": "single_line_text_field", "value": p["style"]},
            {"namespace": "custom", "key": "season",       "type": "single_line_text_field", "value": p["season"]},
        ],
        "productOptions": [
            {"name": "Color", "values": [{"name": c} for c in p["colours"]]},
            {"name": "Size",  "values": [{"name": s} for s in p["sizes"]]}],
    }, "media": media})["data"]["productCreate"]
    if r["userErrors"]:
        fail += 1; failures.append((p["handle"], r["userErrors"])); continue
    pid = r["product"]["id"]

    # productCreate does not leave the product empty: it builds one variant from the
    # FIRST value of each option, at price 0.00 with no SKU. Creating that combination
    # again fails the whole batch with "The variant 'X / Y' already exists", so it is
    # updated in place and only the rest are created.
    first = (p["colours"][0], p["sizes"][0])
    vin, seed = [], None
    for c in p["colours"]:
        code = COLOUR_ABBR.get(c, c[:3].upper())
        for z in p["sizes"]:
            v = {
                "optionValues": [{"optionName": "Color", "name": c},
                                 {"optionName": "Size", "name": z}],
                "price": price, "compareAtPrice": cmp_,
                "inventoryPolicy": "CONTINUE",
                "inventoryItem": {"sku": f"MK-{STYLE_ABBR[p['style']]}-{p['design'].upper()}-{code}-{z}",
                                  "tracked": False, "requiresShipping": True},
                "metafields": [{"namespace": "custom", "key": "blank_sku",
                                "type": "single_line_text_field",
                                "value": f"{STYLE_ABBR[p['style']]}-{code}-{z}"}],
            }
            if (c, z) == first:
                seed = v
            else:
                vin.append(v)
    bad = False
    for j in range(0, len(vin), 100):
        vr = gql(M_VARIANTS, {"productId": pid, "variants": vin[j:j+100]})["data"]["productVariantsBulkCreate"]
        if vr["userErrors"]:
            fail += 1; failures.append((p["handle"], vr["userErrors"])); bad = True; break
    if bad:
        continue
    seeded = gql(Q_SEED, {"id": pid})["data"]["product"]["variants"]["nodes"]
    sid = next((v["id"] for v in seeded
                if {o["name"]: o["value"] for o in v["selectedOptions"]}
                   == {"Color": first[0], "Size": first[1]}), None)
    if sid:
        seed = dict(seed); seed.pop("optionValues"); seed["id"] = sid
        ur = gql(M_VUPDATE, {"productId": pid, "variants": [seed]})["data"]["productVariantsBulkUpdate"]
        if ur["userErrors"]:
            fail += 1; failures.append((p["handle"], ur["userErrors"])); continue
    # fully built - now make it live and put it on the sales channel. Publishing is
    # separate from status: an ACTIVE product that was never published 404s on the
    # storefront while the Admin API reports nothing wrong.
    ar = gql(M_ACTIVATE, {"input": {"id": pid, "status": "ACTIVE"}})["data"]["productUpdate"]
    if ar["userErrors"]:
        fail += 1; failures.append((p["handle"], ar["userErrors"])); continue
    pr = gql(M_PUBLISH, {"id": pid, "input": [{"publicationId": ONLINE_STORE}]})["data"]["publishablePublish"]
    if pr["userErrors"]:
        fail += 1; failures.append((p["handle"], pr["userErrors"])); continue
    ok += 1; created.append({"handle": p["handle"], "id": pid, "style": p["style"],
                             "design": p["design"], "colours": p["colours"], "sizes": p["sizes"]})
    if i % 5 == 0:
        print(f'  {i}/{len(plan)}  created={ok} failed={fail}', flush=True)

print(f'\nCREATED {ok} products   failed={fail}')
for h, e in failures:
    print('  ', h, str(e)[:160])
out = f"catalog-build/created_products_{SEASON}.json"
os.makedirs("catalog-build", exist_ok=True)
json.dump(created, open(out, "w"), indent=1)
print("wrote", out)
