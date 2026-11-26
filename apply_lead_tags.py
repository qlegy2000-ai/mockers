#!/usr/bin/env python3
"""
Tag one 'lead' product per design — the cheapest garment — so design-browsing
collections show 64 cards instead of 275, and the card can read "From LE 679".

Also writes custom.is_lead so the theme can branch on it without tag parsing.

  SHOP=... TOKEN=... python3 apply_lead_tags.py [--dry-run]
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
            if ts.get("currentlyAvailable", 2000) < 300:
                time.sleep(2)
            return out
        raise RuntimeError("retries exhausted")
    return gql


Q_ID = """query($handle: String!) {
  productByIdentifier(identifier: {handle: $handle}) { id handle tags } }"""

M_TAG = """mutation($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) { userErrors { field message } } }"""

M_MF = """mutation($mf: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $mf) { userErrors { field message } } }"""

M_COL = """mutation($i: CollectionInput!) {
  collectionCreate(input: $i) { collection { id handle } userErrors { field message } } }"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    groups = json.load(open(GROUPS))

    leads = {d: items[0] for d, items in groups.items()}   # already cheapest-first
    print(f"{len(leads)} designs -> lead garment:")
    tally = {}
    for d, it in leads.items():
        tally[it["style"]] = tally.get(it["style"], 0) + 1
    for s, n in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"   {n:3d}  {s}")
    entry = sorted(float(i["price"]) for i in leads.values())
    print(f"entry price: LE {entry[0]:.0f} – LE {entry[-1]:.0f}")

    if a.dry_run:
        print("\n--- dry run, nothing written ---")
        for d, it in list(leads.items())[:5]:
            print(f"   {d:28s} -> {it['handle']}  LE {it['price']}")
        return

    shop, token = os.environ.get("SHOP"), os.environ.get("TOKEN")
    if not (shop and token):
        sys.exit("SHOP and TOKEN required")
    gql = gql_factory(shop, token)

    ok = miss = 0
    for i, (design, item) in enumerate(leads.items(), 1):
        node = gql(Q_ID, {"handle": item["handle"]})["data"]["productByIdentifier"]
        if not node:
            miss += 1; print(f"   MISSING {item['handle']}"); continue
        gql(M_TAG, {"id": node["id"], "tags": ["lead"]})
        gql(M_MF, {"mf": [{"ownerId": node["id"], "namespace": "custom",
                           "key": "is_lead", "type": "boolean", "value": "true"}]})
        ok += 1
        if i % 20 == 0:
            print(f"   {i}/{len(leads)} tagged")
    print(f"\ntagged={ok} missing={miss}")

    # design-browsing collection: one card per design
    r = gql(M_COL, {"i": {
        "title": "All Designs", "handle": "all-designs",
        "descriptionHtml": "One card per design — the cheapest garment leads. "
                           "The style switcher on the product page moves between garments.",
        "ruleSet": {"appliedDisjunctively": False,
                    "rules": [{"column": "TAG", "relation": "EQUALS", "condition": "lead"}]}}})
    ue = r["data"]["collectionCreate"]["userErrors"]
    print("All Designs collection:", "created" if not ue else ue)


if __name__ == "__main__":
    main()
