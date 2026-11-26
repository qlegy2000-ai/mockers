#!/usr/bin/env python3
"""
Publish every ACTIVE product into the Gulf and Europe market catalogs.

Why this is needed: catalogCreate's autoPublish only covers products created
AFTER the catalog. Products that already existed are not published to it, and a
market price list only adjusts products that are in its catalog - so without this
step the +25% uplift silently does nothing and customers see the base EGP price.

This only ADDS a market publication. The Online Store, POS, Facebook and TikTok
publications are untouched, as is the Egypt catalog.

SHOP and TOKEN from the environment.
  --run   execute; otherwise counts what would be published and writes nothing
"""
import json, os, sys, time, urllib.request

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
TARGETS = ("Gulf", "Europe")

def gql(q, v=None):
    for _ in range(12):
        rq = urllib.request.Request(
            f"https://{SHOP}/admin/api/2026-07/graphql.json",
            data=json.dumps({"query": q, "variables": v or {}}).encode(),
            headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
        try:
            o = json.load(urllib.request.urlopen(rq))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 520):
                time.sleep(4); continue
            raise
        if o.get("errors") and "THROTTLED" in json.dumps(o["errors"]):
            time.sleep(5); continue
        if o.get("errors"):
            raise SystemExit("GQL " + json.dumps(o["errors"])[:500])
        ts = o.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
        if ts.get("currentlyAvailable", 2000) < 700:
            time.sleep(2)
        return o["data"]
    raise SystemExit("throttled out")

Q_MK = '''{ markets(first:50){nodes{ name status
  catalogs(first:10){nodes{ id title status
    ... on MarketCatalog { publication{ id autoPublish } } }}
}}}'''
pubs = {}
for m in gql(Q_MK)["markets"]["nodes"]:
    if m["name"] in TARGETS and m["status"] == "ACTIVE":
        for c in m["catalogs"]["nodes"]:
            if c.get("publication"):
                pubs[m["name"]] = c["publication"]["id"]
missing = [t for t in TARGETS if t not in pubs]
if missing:
    raise SystemExit(f"no market catalog publication for: {missing}")
for k, v in pubs.items():
    print(f"target publication  {k:<8} {v}")

Q_P = '''query($c:String){ products(first:250, after:$c, query:"status:active"){
  pageInfo{ hasNextPage endCursor } nodes{ id handle } } }'''
prods, cur = [], None
while True:
    d = gql(Q_P, {"c": cur})["products"]
    prods += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]
print(f"\nACTIVE products: {len(prods)}")
print(f"publications each: {len(pubs)}  ->  {len(prods)*len(pubs)} publish operations")

if DRY:
    print("\nDRY RUN - nothing written. add --run to execute.")
    sys.exit()

M = """mutation($id:ID!,$input:[PublicationInput!]!){
  publishablePublish(id:$id, input:$input){ userErrors{ field message } } }"""
inp = [{"publicationId": p} for p in pubs.values()]

ok = err = 0
t0 = time.time()
for i, p in enumerate(prods, 1):
    try:
        g = gql(M, {"id": p["id"], "input": inp})["publishablePublish"]
        if g["userErrors"]:
            err += 1; print(f'  !! {p["handle"]}: {g["userErrors"][:1]}')
        else:
            ok += 1
    except Exception as e:
        err += 1; print(f'  !! {p["handle"]}: {str(e)[:120]}')
    if i % 50 == 0:
        print(f"  {i}/{len(prods)}  ok={ok} err={err}  {time.time()-t0:.0f}s")
print(f"\nPUBLISHED {ok} products to {len(pubs)} catalogs, errors={err}")
