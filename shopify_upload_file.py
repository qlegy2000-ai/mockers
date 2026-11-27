#!/usr/bin/env python3
"""Upload local image files to Shopify Files (admin > Content > Files) and print their CDN URLs.
Not attached to any product. Usage: python3 shopify_upload_file.py file1.png [file2.png ...]"""
import json, os, sys, time, urllib.request, mimetypes, uuid
SHOP = os.environ.get("SHOP", "mockers-shop.myshopify.com"); TOKEN = os.environ.get("TOKEN", "proxy-injected")
API = f"https://{SHOP}/admin/api/2026-07/graphql.json"
def gql(q, v=None):
    r = urllib.request.Request(API, json.dumps({"query": q, "variables": v or {}}).encode(),
                               {"Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN})
    o = json.load(urllib.request.urlopen(r))
    if o.get("errors"): raise SystemExit(o["errors"])
    return o["data"]
def multipart(fields, fname, data, ctype):
    b = uuid.uuid4().hex; out = b""
    for k, v in fields:
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    out += f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{fname}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + data + f"\r\n--{b}--\r\n".encode()
    return out, f"multipart/form-data; boundary={b}"
def upload(path, alt=""):
    name = os.path.basename(path); ctype = mimetypes.guess_type(name)[0] or "image/png"; data = open(path, "rb").read()
    t = gql("""mutation($i:[StagedUploadInput!]!){ stagedUploadsCreate(input:$i){ stagedTargets{ url resourceUrl parameters{name value} } userErrors{message} } }""",
            {"i": [{"resource": "FILE", "filename": name, "mimeType": ctype, "httpMethod": "POST", "fileSize": str(len(data))}]})["stagedUploadsCreate"]["stagedTargets"][0]
    body, ct = multipart([(p["name"], p["value"]) for p in t["parameters"]], name, data, ctype)
    urllib.request.urlopen(urllib.request.Request(t["url"], body, {"Content-Type": ct}))
    f = gql("""mutation($f:[FileCreateInput!]!){ fileCreate(files:$f){ files{ id } userErrors{message} } }""",
            {"f": [{"originalSource": t["resourceUrl"], "contentType": "IMAGE", "alt": alt or name}]})["fileCreate"]
    if f["userErrors"]: raise SystemExit(f["userErrors"])
    fid = f["files"][0]["id"]
    for _ in range(30):
        n = gql('query($id:ID!){ node(id:$id){ ... on MediaImage { fileStatus image{ url } } } }', {"id": fid})["node"]
        if n and n.get("image"): return fid, n["image"]["url"]
        time.sleep(2)
    raise SystemExit("file not ready " + fid)
if __name__ == "__main__":
    for p in sys.argv[1:]:
        fid, url = upload(p); print(p, fid, url)
