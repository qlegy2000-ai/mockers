#!/usr/bin/env python3
"""
Push catalog-build/shopify_import_products.csv into a Shopify store via GraphQL.

  python3 push_to_shopify.py --dry-run          # parse + validate, no writes
  python3 push_to_shopify.py --limit 2          # smoke test, 2 products
  python3 push_to_shopify.py                    # full run (idempotent: skips existing handles)

Credentials come from the env file, never from the repo:
  SHOP=xxx.myshopify.com   TOKEN=shpua_...
"""
import csv, json, os, sys, time, argparse, collections, urllib.request, urllib.error

API = "2026-07"
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "catalog-build", "shopify_import_products.csv")

MF_PROD = {
    "Metafield: custom.design_id [single_line_text_field]": "design_id",
    "Metafield: custom.design_title [single_line_text_field]": "design_title",
    "Metafield: custom.style [single_line_text_field]": "style",
    "Metafield: custom.season [single_line_text_field]": "season",
}
MF_VAR = "Metafield: custom.blank_sku [single_line_text_field]"


class Shopify:
    def __init__(self, shop, token):
        self.url = f"https://{shop}/admin/api/{API}/graphql.json"
        self.token = token

    def __call__(self, query, variables=None):
        body = json.dumps({"query": query, "variables": variables or {}}).encode()
        req = urllib.request.Request(self.url, data=body, headers={
            "X-Shopify-Access-Token": self.token, "Content-Type": "application/json"})
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req) as r:
                    out = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503):
                    time.sleep(2 * (attempt + 1)); continue
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:500].decode(errors='replace')}")
            if out.get("errors"):
                msg = json.dumps(out["errors"])[:400]
                if "THROTTLED" in msg:
                    time.sleep(3); continue
                raise RuntimeError(f"GraphQL errors: {msg}")
            ts = out.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
            if ts.get("currentlyAvailable", 2000) < 300:
                time.sleep(2)
            return out
        raise RuntimeError("retries exhausted")


Q_EXISTING = """query($cursor: String) {
  products(first: 250, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle }
  } }"""

M_CREATE = """mutation($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(product: $product, media: $media) {
    product { id handle media(first: 100) { nodes { id ... on MediaImage { image { url } } } } }
    userErrors { field message }
  } }"""

M_VARIANTS = """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants,
                            strategy: REMOVE_STANDALONE_VARIANT) {
    productVariants { id sku }
    userErrors { field message }
  } }"""

M_PUBLISH = """mutation($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) { userErrors { field message } } }"""

Q_PUBS = """{ publications(first: 20) { nodes { id name } } }"""


def load_csv(path):
    """Group the flat Shopify CSV back into product dicts."""
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault(r["Handle"], []).append(r)

    products = []
    for handle, g in groups.items():
        head = g[0]
        variants = [r for r in g if r["Variant Price"]]
        images, seen = [], set()
        for r in g:
            src = r["Image Src"]
            if src and src not in seen:
                seen.add(src); images.append(src)
        for r in variants:
            vi = r["Variant Image"]
            if vi and vi not in seen:
                seen.add(vi); images.append(vi)
        colors = list(dict.fromkeys(r["Option1 Value"] for r in variants))
        sizes = list(dict.fromkeys(r["Option2 Value"] for r in variants))
        products.append(dict(
            handle=handle, title=head["Title"], body=head["Body (HTML)"],
            vendor=head["Vendor"], ptype=head["Type"],
            tags=[t.strip() for t in head["Tags"].split(",") if t.strip()],
            status=(head["Status"] or "active").upper(),
            seo_title=head["SEO Title"], seo_desc=head["SEO Description"],
            alt=head["Image Alt Text"], colors=colors, sizes=sizes,
            images=images, variants=variants,
            metafields=[{"namespace": "custom", "key": k, "type": "single_line_text_field",
                         "value": head[col]} for col, k in MF_PROD.items() if head.get(col)],
        ))
    return products


def push(gql, products, publish_ids, dry=False):
    ok = skipped = failed = 0
    failures = []
    existing = set()
    if not dry:
        cursor = None
        while True:
            d = gql(Q_EXISTING, {"cursor": cursor})["data"]["products"]
            existing |= {n["handle"] for n in d["nodes"]}
            if not d["pageInfo"]["hasNextPage"]:
                break
            cursor = d["pageInfo"]["endCursor"]
        print(f"  {len(existing)} products already in store")

    for i, p in enumerate(products, 1):
        if p["handle"] in existing:
            skipped += 1; continue
        if dry:
            ok += 1; continue
        try:
            media = [{"originalSource": u, "mediaContentType": "IMAGE", "alt": p["alt"]}
                     for u in p["images"][:150]]
            res = gql(M_CREATE, {"product": {
                "handle": p["handle"], "title": p["title"], "descriptionHtml": p["body"],
                "vendor": p["vendor"], "productType": p["ptype"], "tags": p["tags"],
                "status": p["status"],
                "seo": {"title": p["seo_title"][:70], "description": p["seo_desc"][:320]},
                "metafields": p["metafields"],
                "productOptions": [
                    {"name": "Color", "values": [{"name": c} for c in p["colors"]]},
                    {"name": "Size",  "values": [{"name": s} for s in p["sizes"]]}],
            }, "media": media})
            pc = res["data"]["productCreate"]
            if pc["userErrors"]:
                failed += 1; failures.append((p["handle"], pc["userErrors"])); continue
            pid = pc["product"]["id"]
            # At create time the CDN urls are often still null (media is PROCESSING),
            # so match on the returned url when present and fall back to position:
            # productCreate returns media in the order it was supplied.
            supplied = [u.split("?")[0].rsplit("/", 1)[-1] for u in p["images"][:150]]
            by_url = {}
            for idx, n in enumerate(pc["product"]["media"]["nodes"]):
                u = (n.get("image") or {}).get("url")
                key = u.split("?")[0].rsplit("/", 1)[-1] if u else None
                if not key and idx < len(supplied):
                    key = supplied[idx]
                if key:
                    by_url.setdefault(key, n["id"])

            vin = []
            for r in p["variants"]:
                v = {
                    "optionValues": [
                        {"optionName": "Color", "name": r["Option1 Value"]},
                        {"optionName": "Size",  "name": r["Option2 Value"]}],
                    "price": r["Variant Price"],
                    "compareAtPrice": r["Variant Compare At Price"],
                    "inventoryPolicy": "CONTINUE",
                    "inventoryItem": {
                        "sku": r["Variant SKU"], "tracked": False, "requiresShipping": True,
                        "measurement": {"weight": {"value": float(r["Variant Grams"]),
                                                   "unit": "GRAMS"}}},
                }
                if r.get(MF_VAR):
                    v["metafields"] = [{"namespace": "custom", "key": "blank_sku",
                                        "type": "single_line_text_field", "value": r[MF_VAR]}]
                key = (r["Variant Image"] or "").split("?")[0].rsplit("/", 1)[-1]
                if key in by_url:
                    v["mediaId"] = by_url[key]
                vin.append(v)

            for chunk in [vin[j:j + 100] for j in range(0, len(vin), 100)]:
                vr = gql(M_VARIANTS, {"productId": pid, "variants": chunk})
                ue = vr["data"]["productVariantsBulkCreate"]["userErrors"]
                if ue:
                    failed += 1; failures.append((p["handle"], ue)); break
            else:
                if publish_ids:
                    gql(M_PUBLISH, {"id": pid,
                                    "input": [{"publicationId": q} for q in publish_ids]})
                ok += 1
        except Exception as e:
            failed += 1; failures.append((p["handle"], str(e)[:200]))
        if i % 10 == 0:
            print(f"  {i}/{len(products)}  created={ok} skipped={skipped} failed={failed}")
    return ok, skipped, failed, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-publish", action="store_true")
    a = ap.parse_args()

    shop, token = os.environ.get("SHOP"), os.environ.get("TOKEN")
    if not a.dry_run and not (shop and token):
        sys.exit("SHOP and TOKEN must be set in the environment")

    products = load_csv(CSV_PATH)
    if a.limit:
        products = products[:a.limit]
    nv = sum(len(p["variants"]) for p in products)
    ni = sum(len(p["images"]) for p in products)
    print(f"parsed {len(products)} products / {nv} variants / {ni} images from CSV")

    if a.dry_run:
        print("\n--- dry run, nothing written ---")
        for p in products[:3]:
            print(f"  {p['handle']}: type={p['ptype']} colors={len(p['colors'])} "
                  f"sizes={len(p['sizes'])} variants={len(p['variants'])} images={len(p['images'])}")
        return

    gql = Shopify(shop, token)
    cur = gql("{ shop { currencyCode } }")["data"]["shop"]["currencyCode"]
    print(f"store currency: {cur}")
    if cur != "EGP":
        print(f"  !! expected EGP, found {cur} — prices would import as {cur}. Aborting.")
        print("     Settings > Store details > Store currency, then re-run.")
        sys.exit(2)

    pubs = []
    if not a.no_publish:
        pubs = [n["id"] for n in gql(Q_PUBS)["data"]["publications"]["nodes"]
                if n["name"] in ("Online Store", "Shop")]

    t0 = time.time()
    ok, skipped, failed, failures = push(gql, products, pubs)
    print(f"\ndone in {time.time()-t0:.0f}s: created={ok} skipped={skipped} failed={failed}")
    for h, e in failures[:15]:
        print(f"  FAIL {h}: {e}")
    if failures:
        json.dump(failures, open("catalog-build/push_failures.json", "w"), indent=2)
        print("  full list -> catalog-build/push_failures.json")


if __name__ == "__main__":
    main()
