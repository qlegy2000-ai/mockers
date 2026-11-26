#!/usr/bin/env python3
"""
Attach exported Canva mockups to the right product and colour.

Reads a folder of images exported from the Canva deck, works out which product and
colour each one belongs to from its SLIDE NUMBER, uploads it to Shopify and pins it
to that colour's variants - so picking the swatch changes the photo.

Canva names exports after the design plus the page number ("... - 41.png"), so the
slide number is taken as the LAST number in the filename. Anything whose number is
not in the map is reported and skipped rather than guessed at.

Slides left out of the map must not be uploaded. In v1 those were 52 and 53
(duplicates) and 60 (palestine Offwhite, which white artwork cannot carry). In v2 they
are 86, 93, 102, 118 and 122 - mockups shot on a WHITE sweatshirt, which is not a
colour the catalogue sells.

The design artwork stays first in the gallery; mockups are appended after it.

SHOP and TOKEN from the environment.
  --dir PATH   folder of exported images (required)
  --map PATH   slide->product csv matching that export's deck revision (required)
  --run        execute; otherwise reports only
"""
import json, os, re, sys, time, mimetypes, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
if "--dir" not in sys.argv:
    raise SystemExit("--dir <folder of exported images> is required")
DIR = sys.argv[sys.argv.index("--dir") + 1]

# The slide->product map MUST match the deck revision the exports came from.
# Canva page numbers are not stable: a page inserted near the front on 28 Oct 2026
# shifted every mockup by +1, so a batch exported before that date needs the v1 map
# and a batch exported after needs v2. Passing the wrong one puts the right photo on
# the wrong product, which is why the map is an explicit argument with no default
# that silently works for both.
if "--map" not in sys.argv:
    raise SystemExit("--map <csv> is required (reports/canva_export_list*.csv) - "
                     "it must match the deck revision the exports came from")
MAPFILE = sys.argv[sys.argv.index("--map") + 1]

MAP = {}
import csv as _csv
with open(MAPFILE, encoding="utf-8") as fh:
    for r in _csv.DictReader(fh):
        if r["Action"] == "EXPORT":
            MAP[int(r["Canva slide"])] = (r["Product handle"], r["Colour"])

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

# ---- which files do we have, and which slide is each?
files = {}
unknown = []
if os.path.isdir(DIR):
    for fn in sorted(os.listdir(DIR)):
        if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        nums = re.findall(r'(\d+)', fn)
        n = int(nums[-1]) if nums else None
        if n in MAP:
            files.setdefault(n, os.path.join(DIR, fn))
        else:
            unknown.append(fn)
else:
    print(f"!! folder not found: {DIR}")

# ---- resolve every target product and its variants
Q = '''query($c:String){ products(first:50,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ id handle title
  media(first:50){ nodes{ id } }
  variants(first:250){ nodes{ id selectedOptions{name value}
    media(first:1){nodes{ id }} } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]
by_handle = {r["handle"]: r for r in rows}

plan, missing_file, missing_product, missing_colour = [], [], [], []
for slide, (handle, colour) in sorted(MAP.items()):
    p = by_handle.get(handle)
    if not p:
        missing_product.append((slide, handle)); continue
    vids = [v["id"] for v in p["variants"]["nodes"]
            if any(o["name"] == "Color" and o["value"] == colour for o in v["selectedOptions"])]
    if not vids:
        missing_colour.append((slide, handle, colour)); continue
    f = files.get(slide)
    if not f:
        missing_file.append((slide, handle, colour)); continue
    plan.append({"slide": slide, "pid": p["id"], "handle": handle, "colour": colour,
                 "vids": vids, "file": f, "title": p["title"]})

print(f'slides expected      : {len(MAP)}')
print(f'files found          : {len(files)}')
print(f'ready to attach      : {len(plan)}  ({sum(len(x["vids"]) for x in plan)} variants)')
print(f'no export yet        : {len(missing_file)}')
if unknown:
    print(f'!! files whose slide number is not in the map ({len(unknown)}): {unknown[:6]}')
    print('   52, 53 and 60 are deliberately excluded - do not upload them.')
if missing_product:
    print(f'!! product not found : {missing_product}')
if missing_colour:
    print(f'!! colour not on the product : {missing_colour}')
for x in plan[:5]:
    print(f'   slide {x["slide"]:<3} -> {x["handle"]:<30}{x["colour"]:<18}{len(x["vids"])} variants  {os.path.basename(x["file"])}')
if DRY:
    print('\nDRY RUN - nothing uploaded. add --run to execute.')
    sys.exit()

M_STAGE = """mutation($input:[StagedUploadInput!]!){
 stagedUploadsCreate(input:$input){
  stagedTargets{ url resourceUrl parameters{ name value } } userErrors{ field message } } }"""
M_MEDIA = """mutation($productId:ID!,$media:[CreateMediaInput!]!){
 productCreateMedia(productId:$productId, media:$media){
  media{ ... on MediaImage { id status } } mediaUserErrors{ field message } } }"""
M_APPEND = """mutation($productId:ID!,$variantMedia:[ProductVariantAppendMediaInput!]!){
 productVariantAppendMedia(productId:$productId, variantMedia:$variantMedia){
  userErrors{ field message } } }"""

def upload(path):
    name = os.path.basename(path)
    mime = mimetypes.guess_type(name)[0] or "image/png"
    size = str(os.path.getsize(path))
    t = gql(M_STAGE, {"input": [{"filename": name, "mimeType": mime,
                                 "resource": "IMAGE", "httpMethod": "POST",
                                 "fileSize": size}]})["data"]["stagedUploadsCreate"]
    if t["userErrors"]:
        raise SystemExit("staged upload: " + json.dumps(t["userErrors"]))
    tgt = t["stagedTargets"][0]
    boundary = "----mk" + os.urandom(8).hex()
    body = b""
    for p in tgt["parameters"]:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{p["name"]}"\r\n\r\n'
                 f'{p["value"]}\r\n').encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
             f'Content-Type: {mime}\r\n\r\n').encode()
    body += open(path, "rb").read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(tgt["url"], data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    urllib.request.urlopen(req, timeout=120).read()
    return tgt["resourceUrl"]

ok = err = 0
for i, x in enumerate(plan, 1):
    try:
        src = upload(x["file"])
        m = gql(M_MEDIA, {"productId": x["pid"],
                          "media": [{"originalSource": src, "mediaContentType": "IMAGE",
                                     "alt": f'{x["title"]} - {x["colour"]}'}]})["data"]["productCreateMedia"]
        if m["mediaUserErrors"]:
            err += 1; print('  media failed', x["handle"], m["mediaUserErrors"][:1]); continue
        mid = m["media"][0]["id"]
        # media must finish processing before it can be pinned to a variant
        for _ in range(30):
            st = gql('query($id:ID!){ node(id:$id){ ... on MediaImage { status } } }',
                     {"id": mid})["data"]["node"]["status"]
            if st == "READY":
                break
            time.sleep(2)
        a = gql(M_APPEND, {"productId": x["pid"],
                           "variantMedia": [{"variantId": v, "mediaIds": [mid]} for v in x["vids"]]})["data"]["productVariantAppendMedia"]
        if a["userErrors"]:
            err += 1; print('  attach failed', x["handle"], a["userErrors"][:1]); continue
        ok += 1
        print(f'  {i}/{len(plan)}  {x["handle"]} / {x["colour"]}  ok', flush=True)
    except Exception as e:
        err += 1; print('  error', x["handle"], str(e)[:160])
print(f'\nATTACHED {ok} images   errors={err}')
