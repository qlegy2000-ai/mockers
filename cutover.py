#!/usr/bin/env python3
"""
Live cutover for mockers-shop.myshopify.com.

Order matters:
  1. publish the new design x garment catalogue (ACTIVE + Online Store + Shop)
  2. swap the three contested collection handles so the customer-facing URLs
     point at the new collections
  3. draft the 78 old apparel designs

The 8 accessories stay ACTIVE and untouched, by instruction.
URL redirects were created before this script runs, so no existing product
link breaks when the old products are drafted.
"""
import json, os, time, urllib.request

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
assert SHOP == "mockers-shop.myshopify.com", f"wrong store: {SHOP}"

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
        if ts.get("currentlyAvailable", 2000) < 600:
            time.sleep(2)
        return o
    raise SystemExit("throttled out")

Q = '''query($c:String){ products(first:250,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ id handle status style: metafield(namespace:"custom",key:"style"){value} } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

new = [r for r in rows if (r["style"] or {}).get("value")]

# kept live by instruction - not apparel, not part of the rebuild
ACCESSORIES = {
    'microfiber-beach-towel', 'stainless-steel-insulated-flask', 'my-spot-beach-towel',
    'seagull-in-the-ass-beach-towel', 'bad-influence-bucket-hats',
    'emotionally-expensive-bucket-hat', 'if-lost-bucket-hat', 'casual-sweatpants',
}
old_apparel = [r for r in rows
               if r["status"] == "ACTIVE"
               and not (r["style"] or {}).get("value")
               and r["handle"] not in ACCESSORIES]

print(f'new products to publish : {len(new)}')
print(f'old apparel to draft    : {len(old_apparel)}')
print(f'accessories kept live   : {len(ACCESSORIES)}')
assert len(new) == 321, f"expected 321 new products, found {len(new)}"
assert len(old_apparel) == 78, f"expected 78 old apparel, found {len(old_apparel)}"

pubs = [{"publicationId": p["id"]}
        for p in gql('{ publications(first:10){ nodes{ id name } } }')["data"]["publications"]["nodes"]
        if p["name"] in ("Online Store", "Shop")]
print(f'sales channels          : {len(pubs)}\n')

U = 'mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{status} userErrors{message} } }'
P = 'mutation($id:ID!,$input:[PublicationInput!]!){ publishablePublish(id:$id,input:$input){ userErrors{message} } }'

# 1 -------------------------------------------------- publish the new catalogue
n = 0
for r in new:
    g = gql(U, {"p": {"id": r["id"], "status": "ACTIVE"}})["data"]["productUpdate"]
    if g["userErrors"]:
        print('  activate failed', r["handle"], g["userErrors"][:1]); continue
    gql(P, {"id": r["id"], "input": pubs})
    n += 1
    if n % 50 == 0:
        print(f'  published {n}/{len(new)}', flush=True)
print(f'PUBLISHED {n} new products\n')

# 2 -------------------------------------------------- swap collection handles
CU = 'mutation($input:CollectionInput!){ collectionUpdate(input:$input){ collection{handle} userErrors{message} } }'
BY = 'query($h:String!){ collectionByHandle(handle:$h){ id } }'
for old_h, archived_h, mk_h, final_h in [
        ("all-designs", "all-designs-old", "mk-all-designs", "all-designs"),
        ("winter-collection", "winter-collection-old", "mk-winter-collection", "winter-collection"),
        ("summer-collection", "summer-collection-old", "mk-summer-collection", "summer-collection")]:
    o = gql(BY, {"h": old_h})["data"]["collectionByHandle"]
    if o:
        gql(CU, {"input": {"id": o["id"], "handle": archived_h}})
        print(f'  {old_h} -> {archived_h}')
    m = gql(BY, {"h": mk_h})["data"]["collectionByHandle"]
    if m:
        gql(CU, {"input": {"id": m["id"], "handle": final_h}})
        print(f'  {mk_h} -> {final_h}')
print()

# 3 -------------------------------------------------- retire the old apparel
d = 0
for r in old_apparel:
    g = gql(U, {"p": {"id": r["id"], "status": "DRAFT"}})["data"]["productUpdate"]
    if g["userErrors"]:
        print('  draft failed', r["handle"], g["userErrors"][:1]); continue
    d += 1
print(f'DRAFTED {d} old apparel products (not deleted - recoverable)')
print('\nCUTOVER COMPLETE')
