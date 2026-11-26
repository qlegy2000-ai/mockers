#!/usr/bin/env python3
"""
Create the three DUFFLE BAG products and attach their mockups.

The Drive folder held three design folders, not one product - the same
design x item model the bucket hats and beach towels already follow. Each design
is one product with a Colour option, and each colour has its own photo.

Bag colours: Black, Dark Green, Yellow, Purple. MY SHIT TOGETHER was never shot in
Yellow, so it is offered in three.

Accessories differ from apparel and this follows the accessory pattern, not the
garment one: blank productType, templateSuffix "acc", vendor mockers-shop, and
published to all four sales channels rather than Online Store alone.

Images must be pre-resized. The originals were 6250x6250 = 39 MP, nearly double
Shopify's 20 MP ceiling, and two were over the 20 MB file limit; they would have
been rejected. duffle-web/ holds 3000px copies.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, mimetypes, urllib.request

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
PRICE = "968.00"

BODY = """<p><strong>DUFFLE BAG</strong></p>
<p>Made for everyday adventures, weekend getaways, and everything in between. A spacious, practical design with smart storage, comfortable carrying, and durable materials.</p>
<p><strong>Product Details</strong></p>
<ul>
<li><strong>Premium Fabric:</strong> Made from high-quality polyester for everyday durability.</li>
<li><strong>Comfortable Carry:</strong> Adjustable shoulder straps with padded shoulder support for added comfort.</li>
<li><strong>Durable Hardware:</strong> Finished with stainless-steel accessories.</li>
<li><strong>Smart Storage:</strong> Features an outer mesh pocket and an inner pocket for easy organization.</li>
<li><strong>Spacious Capacity:</strong> Approximately 26L &mdash; plenty of room for your daily essentials and more.</li>
<li><strong>Custom Print:</strong> Designed to accommodate a pocket print (circular, 24 &times; 24 cm) and a main bag print (75 &times; 57 cm).</li>
</ul>
<p><strong>Care Instructions</strong></p>
<ul>
<li>Detach the shoulder strap before washing.</li>
<li>Turn inside out and machine wash at 30&deg;C.</li>
<li>Hang to air dry.</li>
</ul>"""

PRODUCTS = [
    {"slug": "a-lot-to-carry",      "title": "A LOT TO CARRY - Duffle Bag",
     "colours": ["Black", "Dark Green", "Yellow", "Purple"]},
    {"slug": "my-shit-together",    "title": "MY SHIT TOGETHER - Duffle Bag",
     "colours": ["Black", "Dark Green", "Purple"]},
    {"slug": "return-to-therapist", "title": "RETURN TO THERAPIST - Duffle Bag",
     "colours": ["Black", "Dark Green", "Yellow", "Purple"]},
]
SLUGC = {"Black": "black", "Dark Green": "dark-green", "Yellow": "yellow", "Purple": "purple"}

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
            raise SystemExit("GQL " + json.dumps(o["errors"])[:400])
        ts = o.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
        if ts.get("currentlyAvailable", 2000) < 700:
            time.sleep(2)
        return o
    raise SystemExit("throttled out")

for p in PRODUCTS:
    p["handle"] = f'{p["slug"]}-duffle-bag'
    p["artwork"] = f'duffle-web/{p["slug"]}__00-artwork.jpg'
    p["shots"] = {c: f'duffle-web/{p["slug"]}__{SLUGC[c]}.jpg' for c in p["colours"]}
    p["missing"] = [f for f in [p["artwork"]] + list(p["shots"].values()) if not os.path.exists(f)]

print(f'products to create : {len(PRODUCTS)}')
for p in PRODUCTS:
    print(f'   {p["handle"]:<36}{len(p["colours"])} colours  {p["colours"]}')
    if p["missing"]:
        print(f'      !! missing files: {p["missing"]}')
if any(p["missing"] for p in PRODUCTS):
    raise SystemExit("missing image files - fix before running")
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

pubs = gql('{ publications(first:25){nodes{id name}} }')["data"]["publications"]["nodes"]
WANT = {"Online Store", "Point of Sale", "Facebook & Instagram", "TikTok"}
PUBIDS = [x["id"] for x in pubs if x["name"] in WANT]
ACC = gql('{ collections(first:1, query:"handle:accessories"){nodes{id}} }')["data"]["collections"]["nodes"][0]["id"]

M_CREATE = """mutation($product: ProductCreateInput!, $media:[CreateMediaInput!]){
 productCreate(product:$product, media:$media){
  product{ id handle title media(first:20){nodes{ ... on MediaImage { id } }} }
  userErrors{ field message } } }"""
M_VAR = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkUpdate(productId:$productId, variants:$variants){
  productVariants{ id } userErrors{ field message } } }"""
M_VCREATE = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkCreate(productId:$productId, variants:$variants){
  productVariants{ id } userErrors{ field message } } }"""
M_STAGE = """mutation($input:[StagedUploadInput!]!){
 stagedUploadsCreate(input:$input){ stagedTargets{ url resourceUrl parameters{ name value } }
  userErrors{ field message } } }"""
M_MEDIA = """mutation($productId:ID!,$media:[CreateMediaInput!]!){
 productCreateMedia(productId:$productId, media:$media){
  media{ ... on MediaImage { id status } } mediaUserErrors{ field message } } }"""
M_APPEND = """mutation($productId:ID!,$variantMedia:[ProductVariantAppendMediaInput!]!){
 productVariantAppendMedia(productId:$productId, variantMedia:$variantMedia){
  userErrors{ field message } } }"""
M_PUB = """mutation($id:ID!,$input:[PublicationInput!]!){
 publishablePublish(id:$id,input:$input){ userErrors{ field message } } }"""
M_ADD = """mutation($id:ID!,$productIds:[ID!]!){
 collectionAddProducts(id:$id, productIds:$productIds){ userErrors{ field message } } }"""

def upload(path):
    name = os.path.basename(path)
    mime = mimetypes.guess_type(name)[0] or "image/jpeg"
    t = gql(M_STAGE, {"input": [{"filename": name, "mimeType": mime, "resource": "IMAGE",
                                 "httpMethod": "POST", "fileSize": str(os.path.getsize(path))}]})["data"]["stagedUploadsCreate"]
    if t["userErrors"]:
        raise SystemExit("stage: " + json.dumps(t["userErrors"]))
    tgt = t["stagedTargets"][0]
    b = "----mk" + os.urandom(8).hex()
    body = b""
    for prm in tgt["parameters"]:
        body += (f'--{b}\r\nContent-Disposition: form-data; name="{prm["name"]}"\r\n\r\n{prm["value"]}\r\n').encode()
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
             f'Content-Type: {mime}\r\n\r\n').encode()
    body += open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    urllib.request.urlopen(urllib.request.Request(
        tgt["url"], data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=180).read()
    return tgt["resourceUrl"]

def add_media(pid, path, alt):
    src = upload(path)
    m = gql(M_MEDIA, {"productId": pid, "media": [{"originalSource": src,
             "mediaContentType": "IMAGE", "alt": alt}]})["data"]["productCreateMedia"]
    if m["mediaUserErrors"]:
        raise SystemExit("media: " + json.dumps(m["mediaUserErrors"]))
    mid = m["media"][0]["id"]
    for _ in range(40):
        st = gql('query($id:ID!){ node(id:$id){ ... on MediaImage { status } } }',
                 {"id": mid})["data"]["node"]["status"]
        if st == "READY":
            break
        time.sleep(2)
    return mid

made = []
for p in PRODUCTS:
    ex = gql('query($q:String!){ products(first:1, query:$q){nodes{id handle}} }',
             {"q": f'handle:{p["handle"]}'})["data"]["products"]["nodes"]
    if ex:
        print("exists, skipping:", p["handle"]); continue
    r = gql(M_CREATE, {"product": {
        "handle": p["handle"], "title": p["title"], "descriptionHtml": BODY,
        "vendor": "mockers-shop", "productType": "", "status": "DRAFT",
        "templateSuffix": "acc",
        "tags": ["duffle bag", "bag", "accessories"],
        "productOptions": [{"name": "Color", "values": [{"name": c} for c in p["colours"]]}],
    }})["data"]["productCreate"]
    if r["userErrors"]:
        print("create failed", p["handle"], r["userErrors"]); continue
    pid = r["product"]["id"]

    # productCreate seeds one variant from the first option value; update it, create the rest
    cur = gql('query($id:ID!){ product(id:$id){ variants(first:20){nodes{id selectedOptions{name value}}} } }',
              {"id": pid})["data"]["product"]["variants"]["nodes"]
    seeded = {next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color"): v["id"] for v in cur}
    base = {"price": PRICE, "taxable": True, "inventoryPolicy": "CONTINUE",
            "inventoryItem": {"tracked": False, "requiresShipping": True}}
    upd = [dict(base, id=vid) for vid in seeded.values()]
    g = gql(M_VAR, {"productId": pid, "variants": upd})["data"]["productVariantsBulkUpdate"]
    if g["userErrors"]:
        print("  variant update", p["handle"], g["userErrors"])
    rest = [c for c in p["colours"] if c not in seeded]
    if rest:
        g = gql(M_VCREATE, {"productId": pid, "variants":
                [dict(base, optionValues=[{"optionName": "Color", "name": c}]) for c in rest]})["data"]["productVariantsBulkCreate"]
        if g["userErrors"]:
            print("  variant create", p["handle"], g["userErrors"])

    # artwork first, then one mockup per colour pinned to that colour's variant
    add_media(pid, p["artwork"], p["title"])
    vmap = {next(o["value"] for o in v["selectedOptions"] if o["name"] == "Color"): v["id"]
            for v in gql('query($id:ID!){ product(id:$id){ variants(first:20){nodes{id selectedOptions{name value}}} } }',
                         {"id": pid})["data"]["product"]["variants"]["nodes"]}
    for c in p["colours"]:
        mid = add_media(pid, p["shots"][c], f'{p["title"]} - {c}')
        a = gql(M_APPEND, {"productId": pid,
                "variantMedia": [{"variantId": vmap[c], "mediaIds": [mid]}]})["data"]["productVariantAppendMedia"]
        if a["userErrors"]:
            print("  attach", p["handle"], c, a["userErrors"])
    gql(M_PUB, {"id": pid, "input": [{"publicationId": i} for i in PUBIDS]})
    gql(M_ADD, {"id": ACC, "productIds": [pid]})
    made.append(p["handle"])
    print(f'  built {p["handle"]}  ({len(p["colours"])} colours)', flush=True)

print(f'\nCREATED {len(made)} products: {made}')
