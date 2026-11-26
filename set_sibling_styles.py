#!/usr/bin/env python3
"""
Populate custom.sibling_styles (list.product_reference) on every product, so the
PDP style switcher can render a design's other garments with no JS and no app.

Each product in a design group gets the WHOLE ordered group (cheapest first,
itself included) — the snippet highlights the current one.

  SHOP=... TOKEN=... python3 set_sibling_styles.py [--dry-run]
"""
import json, os, sys, time, argparse, urllib.request, urllib.error

API = "2026-07"
HERE = os.path.dirname(os.path.abspath(__file__))
GROUPS = os.path.join(HERE, "catalog-build", "design_groups.json")


def gql_factory(shop, token):
    url = f"https://{shop}/admin/api/{API}/graphql.json"
    def gql(q, v=None):
        body = json.dumps({"query": q, "variables": v or {}}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "X-Shopify-Access-Token": token, "Content-Type": "application/json"})
        for a in range(6):
            try:
                with urllib.request.urlopen(req) as r:
                    out = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503):
                    time.sleep(2 * (a + 1)); continue
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}")
            if out.get("errors"):
                if "THROTTLED" in json.dumps(out["errors"]):
                    time.sleep(3); continue
                raise RuntimeError(json.dumps(out["errors"])[:400])
            ts = out.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
            if ts.get("currentlyAvailable", 2000) < 400:
                time.sleep(2)
            return out
        raise RuntimeError("retries exhausted")
    return gql


M_DEF = """mutation($d: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $d) {
    createdDefinition { id }
    userErrors { field message code } } }"""

Q_ALL = """query($cursor: String) {
  products(first: 250, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle } } }"""

M_SET = """mutation($mf: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $mf) { userErrors { field message } } }"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    groups = json.load(open(GROUPS))
    print(f"{len(groups)} design groups, "
          f"{sum(len(v) for v in groups.values())} product references to write")

    if a.dry_run:
        for d, items in list(groups.items())[:3]:
            print(f"  {d}: {[i['handle'] for i in items]}")
        print("--- dry run, nothing written ---")
        return

    shop, token = os.environ.get("SHOP"), os.environ.get("TOKEN")
    if not (shop and token):
        sys.exit("SHOP and TOKEN required")
    gql = gql_factory(shop, token)

    r = gql(M_DEF, {"d": {
        "name": "Sibling styles", "namespace": "custom", "key": "sibling_styles",
        "description": "The other garments carrying this design, cheapest first.",
        "type": "list.product_reference", "ownerType": "PRODUCT", "pin": True}})
    ue = r["data"]["metafieldDefinitionCreate"]["userErrors"]
    codes = [e.get("code") for e in ue]
    print("definition custom.sibling_styles:",
          "already exists" if "TAKEN" in codes else (ue or "created"))

    ids, cursor = {}, None
    while True:
        d = gql(Q_ALL, {"cursor": cursor})["data"]["products"]
        ids.update({n["handle"]: n["id"] for n in d["nodes"]})
        if not d["pageInfo"]["hasNextPage"]:
            break
        cursor = d["pageInfo"]["endCursor"]
    print(f"resolved {len(ids)} product ids from the store")

    payload, missing = [], []
    for design, items in groups.items():
        gids = []
        for it in items:
            gid = ids.get(it["handle"])
            (gids.append(gid) if gid else missing.append(it["handle"]))
        if len(gids) < 2:
            continue
        for gid in gids:
            payload.append({"ownerId": gid, "namespace": "custom", "key": "sibling_styles",
                            "type": "list.product_reference", "value": json.dumps(gids)})
    if missing:
        print(f"  !! {len(missing)} handles not found in store (import incomplete?)")
        for h in missing[:10]:
            print(f"     {h}")

    ok = err = 0
    for chunk in [payload[i:i + 25] for i in range(0, len(payload), 25)]:
        res = gql(M_SET, {"mf": chunk})
        ue = res["data"]["metafieldsSet"]["userErrors"]
        if ue:
            err += len(ue); print("  errors:", ue[:3])
        ok += len(chunk) - len(ue)
    print(f"\nsibling_styles written: {ok}  errors: {err}")


if __name__ == "__main__":
    main()
