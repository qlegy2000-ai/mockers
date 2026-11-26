#!/usr/bin/env python3
"""
Put every non-Egypt market on a percentage uplift over the EGP base price.

The base EGP price list stays the reference and is never touched - Egypt keeps its
0% adjustment. Each other ACTIVE market gets its own catalog and price list carrying
a single parent adjustment, so one number moves all products in that market at once.

Currency is EGP everywhere: Shopify Payments is not available in Egypt and
enabledPresentmentCurrencies is ['EGP'], so no other presentment currency exists.

compareAtMode ADJUSTED matches the Egypt list, so any compare-at price scales too
rather than being dropped.

SHOP and TOKEN from the environment.
  --pct N   uplift percentage (default 25)
  --run     execute; otherwise prints the plan and writes nothing
"""
import json, os, sys, time, urllib.request

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
PCT = float(sys.argv[sys.argv.index("--pct") + 1]) if "--pct" in sys.argv else 25.0
SKIP = {"Egypt"}                       # base reference - never adjusted

def gql(q, v=None):
    for _ in range(10):
        rq = urllib.request.Request(
            f"https://{SHOP}/admin/api/2026-07/graphql.json",
            data=json.dumps({"query": q, "variables": v or {}}).encode(),
            headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
        o = json.load(urllib.request.urlopen(rq))
        if o.get("errors") and "THROTTLED" in json.dumps(o["errors"]):
            time.sleep(5); continue
        if o.get("errors"):
            raise SystemExit("GQL " + json.dumps(o["errors"])[:500])
        ts = o.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
        if ts.get("currentlyAvailable", 2000) < 700:
            time.sleep(2)
        return o["data"]
    raise SystemExit("throttled out")

Q = '''{ markets(first:50){nodes{ id name status
  catalogs(first:10){nodes{ id title status
    ... on MarketCatalog {
      priceList{ id name currency parent{ adjustment{ type value } } }
    }
  }}
}}}'''
markets = gql(Q)["markets"]["nodes"]

todo = []
print(f"uplift: +{PCT:g}%  (Egypt stays at base)\n")
for m in sorted(markets, key=lambda x: x["name"]):
    cats = m["catalogs"]["nodes"]
    pl = next((c.get("priceList") for c in cats if c.get("priceList")), None)
    cur = f'{pl["parent"]["adjustment"]["type"]} {pl["parent"]["adjustment"]["value"]:g}' if pl else "-"
    if m["name"] in SKIP:
        note = "SKIP - base reference"
    elif m["status"] != "ACTIVE":
        note = "skip - market closed"
    else:
        note = f'set +{PCT:g}%' + ("  (update existing list)" if pl else "  (create catalog + price list)")
        todo.append((m, cats, pl))
    print(f'{m["name"]:<14} {m["status"]:<6} catalogs={len(cats):<2} priceList={cur:<26} {note}')

BASE = {"Hoodie": 1599, "Sweatshirt": 1499, "Oversized Heavy Premium": 930,
        "Oversized Light-Soft": 778, "Regular Fit T-Shirt": 679}
print(f'\nwhat +{PCT:g}% looks like:')
for k, v in BASE.items():
    print(f'   {k:<26}{v:>7.0f} ->{v*(1+PCT/100):>9.2f}')

if not todo:
    print("\nnothing to do."); sys.exit()
if DRY:
    print(f'\nwould change {len(todo)} market(s): {[m["name"] for m,_,_ in todo]}')
    print("DRY RUN - nothing written. add --run to execute.")
    sys.exit()

M_CAT = """mutation($input:CatalogCreateInput!){
  catalogCreate(input:$input){ catalog{ id title status publication{ id } } userErrors{ field message } } }"""
M_PUB = """mutation($input:PublicationCreateInput!){
  publicationCreate(input:$input){ publication{ id autoPublish } userErrors{ field message } } }"""
M_PL = """mutation($input:PriceListCreateInput!){
  priceListCreate(input:$input){ priceList{ id name currency parent{ adjustment{ type value } } }
    userErrors{ field message } } }"""
M_PLU = """mutation($id:ID!,$input:PriceListUpdateInput!){
  priceListUpdate(id:$id, input:$input){ priceList{ id parent{ adjustment{ type value } } }
    userErrors{ field message } } }"""

adj = {"adjustment": {"value": PCT, "type": "PERCENTAGE_INCREASE"},
       "settings": {"compareAtMode": "ADJUSTED"}}

print()
for m, cats, pl in todo:
    name = m["name"]
    if pl:
        g = gql(M_PLU, {"id": pl["id"], "input": {"parent": adj}})["priceListUpdate"]
        print(f'  {"!!" if g["userErrors"] else "ok"} {name}: price list -> +{PCT:g}%  {g["userErrors"] or ""}')
        continue

    cat = next((c for c in cats if c["status"] == "ACTIVE"), None)
    if not cat:
        g = gql(M_CAT, {"input": {"title": name, "status": "ACTIVE",
                                  "context": {"marketIds": [m["id"]]}}})["catalogCreate"]
        if g["userErrors"]:
            print(f'  !! {name}: catalogCreate {g["userErrors"]}'); continue
        cat = g["catalog"]
        print(f'  ok {name}: catalog created {cat["id"]}')

    # a catalog with no publication shows no products in that market
    if not cat.get("publication"):
        g = gql(M_PUB, {"input": {"catalogId": cat["id"], "autoPublish": True}})["publicationCreate"]
        print(f'  {"!!" if g["userErrors"] else "ok"} {name}: publication '
              f'{g["publication"]["id"] if g["publication"] else ""} autoPublish=True  {g["userErrors"] or ""}')

    g = gql(M_PL, {"input": {"name": name, "currency": "EGP",
                             "catalogId": cat["id"], "parent": adj}})["priceListCreate"]
    print(f'  {"!!" if g["userErrors"] else "ok"} {name}: price list +{PCT:g}%  {g["userErrors"] or ""}')

print("\ndone.")
