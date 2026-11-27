#!/usr/bin/env python3
"""
Attach finished mockup images to the matching colour of a live product.

Files must be named  <design-handle>_<Style>_<Colour>.jpg|png
  e.g. funny-how_Sweatshirt_DarkBlue.jpg  ->  product funny-how-sweatshirt, Color "Dark Blue"
Each image is uploaded once, added to the product's media, and set as the image of
every size variant of that colour. Colours that already have an image are skipped
unless --replace is given.

  SHOP=... TOKEN=proxy-injected python3 attach_mockups.py <folder>          # dry run
  SHOP=... TOKEN=proxy-injected python3 attach_mockups.py <folder> --run
"""
import glob, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_upload_file import gql, multipart  # noqa: E402
import urllib.request, mimetypes

DRY = "--run" not in sys.argv
REPLACE = "--replace" in sys.argv
folder = next(a for a in sys.argv[1:] if not a.startswith("--"))
COLOUR = {"Black": "Black", "Offwhite": "Offwhite", "BeetrootPurple": "Beetroot Purple", "DarkGreen": "Dark Green",
          "DarkBlue": "Dark Blue", "Purple": "Purple", "IronGrey": "Iron Grey", "AegeanBlue": "Aegean Blue"}

Q = """query($h:String!){ productByHandle(handle:$h){ id title
  variants(first:100){ nodes{ id selectedOptions{name value} image{ id } } } } }"""

plan = []
for path in sorted(glob.glob(os.path.join(folder, "*.jpg")) + glob.glob(os.path.join(folder, "*.png"))):
    m = re.match(r"(.+)_(Sweatshirt|Hoodie)_([A-Za-z]+)\.(jpg|png)$", os.path.basename(path))
    if not m:
        print("skip (name):", path); continue
    design, style, col = m.group(1), m.group(2), COLOUR[m.group(3)]
    handle = f"{design}-{style.lower()}"
    p = gql(Q, {"h": handle})["productByHandle"]
    if not p:
        print("NO PRODUCT", handle); continue
    vs = [v for v in p["variants"]["nodes"] if {o["name"]: o["value"] for o in v["selectedOptions"]}.get("Color") == col]
    if not vs:
        print("NO VARIANTS", handle, col); continue
    has = any(v["image"] for v in vs)
    if has and not REPLACE:
        print(f"already has image, skip: {handle} / {col}"); continue
    plan.append((path, p["id"], p["title"], col, [v["id"] for v in vs]))

for path, pid, title, col, vids in plan:
    print(f"{title:45} {col:16} {len(vids)} variants  <- {os.path.basename(path)}")
if DRY:
    print(f"\nDRY RUN: {len(plan)} images would be attached. add --run to execute."); sys.exit()

for path, pid, title, col, vids in plan:
    name = os.path.basename(path); data = open(path, "rb").read(); ctype = mimetypes.guess_type(name)[0]
    t = gql("""mutation($i:[StagedUploadInput!]!){ stagedUploadsCreate(input:$i){ stagedTargets{ url resourceUrl parameters{name value} } } }""",
            {"i": [{"resource": "PRODUCT_IMAGE", "filename": name, "mimeType": ctype, "httpMethod": "POST", "fileSize": str(len(data))}]})["stagedUploadsCreate"]["stagedTargets"][0]
    body, ct = multipart([(x["name"], x["value"]) for x in t["parameters"]], name, data, ctype)
    urllib.request.urlopen(urllib.request.Request(t["url"], body, {"Content-Type": ct}))
    r = gql("""mutation($p:ID!,$m:[CreateMediaInput!]!){ productCreateMedia(productId:$p, media:$m){ media{ id } mediaUserErrors{ message } } }""",
            {"p": pid, "m": [{"originalSource": t["resourceUrl"], "mediaContentType": "IMAGE", "alt": f"{title} - {col}"}]})["productCreateMedia"]
    if r["mediaUserErrors"]:
        print("FAILED media", title, col, r["mediaUserErrors"]); continue
    mid = r["media"][0]["id"]
    for _ in range(40):
        st = gql('query($id:ID!){ node(id:$id){ ... on MediaImage { status } } }', {"id": mid})["node"]["status"]
        if st == "READY": break
        if st == "FAILED": break
        time.sleep(2)
    if st != "READY":
        print("media not ready", title, col, st); continue
    a = gql("""mutation($p:ID!,$vm:[ProductVariantAppendMediaInput!]!){ productVariantAppendMedia(productId:$p, variantMedia:$vm){ userErrors{ message } } }""",
            {"p": pid, "vm": [{"variantId": v, "mediaIds": [mid]} for v in vids]})["productVariantAppendMedia"]
    print(("OK    " if not a["userErrors"] else "ERROR ") + f"{title} / {col}", a["userErrors"] or "")
