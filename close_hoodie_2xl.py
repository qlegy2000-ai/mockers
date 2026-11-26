#!/usr/bin/env python3
"""
Take hoodie 2XL out of stock without deleting it, and put it back later.

Mockers print on demand, so every variant ships with inventory tracking OFF and
policy CONTINUE - Shopify treats an untracked variant as infinitely available.
That is why a 2XL cannot simply be "set to zero": with tracking off the number is
ignored and the variant stays buyable.

Showing it as sold out needs all three of:

    tracked          = true      so Shopify counts stock at all
    available        = 0         at the only location
    inventoryPolicy  = DENY      so it cannot be bought past zero

--restock reverses exactly that: policy back to CONTINUE and tracking back off,
which is the state every other variant is in. The variant, its SKU, its price and
its place in the size picker are never touched, so nothing is lost in between and
no customer link breaks.

Only Hoodie 2XL is touched. Sweatshirt 2XL and every other hoodie size are left
exactly as they are.

SHOP and TOKEN from the environment.
  --restock    put it back on sale instead of closing it
  --only N     act on the first N variants (for a trial run)
  --run        execute; otherwise reports only
"""
import json, os, sys, time, urllib.request, collections, uuid

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
RESTOCK = "--restock" in sys.argv
ONLY = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
STYLE, SIZE = "Hoodie", "2XL"

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

locs = gql('{ locations(first:10){nodes{id name isActive}} }')["data"]["locations"]["nodes"]
locs = [l for l in locs if l["isActive"]]
if len(locs) != 1:
    raise SystemExit(f"expected one active location, found {len(locs)}: {[l['name'] for l in locs]}")
LOC = locs[0]["id"]

Q = '''query($c:String){ products(first:25,after:$c, query:"product_type:Hoodie"){
 pageInfo{hasNextPage endCursor}
 nodes{ id handle status
  style: metafield(namespace:"custom",key:"style"){value}
  variants(first:250){ nodes{ id title sku inventoryPolicy inventoryQuantity
    selectedOptions{name value}
    inventoryItem{ id tracked
      inventoryLevels(first:5){ nodes{ location{id} } } } } } } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

byprod = collections.OrderedDict()
state = collections.Counter()
for r in rows:
    if (r["style"] or {}).get("value") != STYLE or r["status"] != "ACTIVE":
        continue
    for v in r["variants"]["nodes"]:
        if next(o["value"] for o in v["selectedOptions"] if o["name"] == "Size") != SIZE:
            continue
        closed = (v["inventoryItem"]["tracked"] and v["inventoryPolicy"] == "DENY"
                  and (v["inventoryQuantity"] or 0) <= 0)
        state["closed" if closed else "on sale"] += 1
        if RESTOCK and not closed:
            continue
        if not RESTOCK and closed:
            continue
        byprod.setdefault((r["id"], r["handle"]), []).append({
            "vid": v["id"], "iid": v["inventoryItem"]["id"], "title": v["title"],
            "active_at_loc": any(n["location"]["id"] == LOC
                                 for n in v["inventoryItem"]["inventoryLevels"]["nodes"]),
            "qty": v["inventoryQuantity"] or 0,
        })

todo = [v for vs in byprod.values() for v in vs]
if ONLY:
    keep, n = collections.OrderedDict(), 0
    for k, vs in byprod.items():
        take = vs[:max(0, ONLY - n)]
        if take:
            keep[k] = take; n += len(take)
        if n >= ONLY:
            break
    byprod, todo = keep, [v for vs in keep.values() for v in vs]

action = "RESTOCK (put back on sale)" if RESTOCK else "CLOSE (show as sold out)"
print(f'action      : {action}')
print(f'scope       : {STYLE} {SIZE} only')
print(f'location    : {locs[0]["name"]}')
print(f'current     : {dict(state)}')
print(f'to change   : {len(todo)} variants across {len(byprod)} products')
if DRY:
    for (pid, h), vs in list(byprod.items())[:5]:
        print(f'   {h:<36}{[v["title"] for v in vs]}')
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

M_VAR = """mutation($productId:ID!,$variants:[ProductVariantsBulkInput!]!){
 productVariantsBulkUpdate(productId:$productId, variants:$variants){
  productVariants{ id } userErrors{ field message } } }"""
M_ACT = """mutation($id:ID!,$locationId:ID!,$available:Int){
 inventoryActivate(inventoryItemId:$id, locationId:$locationId, available:$available){
  inventoryLevel{ id } userErrors{ field message } } }"""
# inventorySetQuantities is guarded: it requires @idempotent with a unique key so a
# retried request cannot apply the same stock change twice.
M_SET = """mutation($input:InventorySetQuantitiesInput!, $key:String!){
 inventorySetQuantities(input:$input) @idempotent(key:$key){
  userErrors{ field message } } }"""

ok = err = 0
for i, ((pid, handle), vs) in enumerate(byprod.items(), 1):
    if RESTOCK:
        # policy first, then stop tracking - an untracked variant is always available
        upd = [{"id": v["vid"], "inventoryPolicy": "CONTINUE",
                "inventoryItem": {"tracked": False}} for v in vs]
        g = gql(M_VAR, {"productId": pid, "variants": upd})["data"]["productVariantsBulkUpdate"]
        if g["userErrors"]:
            err += 1; print('  failed', handle, g["userErrors"][:1]); continue
        ok += len(vs)
    else:
        # tracking on and policy DENY, then force the count to zero
        upd = [{"id": v["vid"], "inventoryPolicy": "DENY",
                "inventoryItem": {"tracked": True}} for v in vs]
        g = gql(M_VAR, {"productId": pid, "variants": upd})["data"]["productVariantsBulkUpdate"]
        if g["userErrors"]:
            err += 1; print('  failed', handle, g["userErrors"][:1]); continue
        quantities, bad = [], False
        for v in vs:
            if not v["active_at_loc"]:
                a = gql(M_ACT, {"id": v["iid"], "locationId": LOC, "available": 0})["data"]["inventoryActivate"]
                if a["userErrors"]:
                    err += 1; print('  activate failed', handle, a["userErrors"][:1]); bad = True; break
            elif v["qty"] != 0:
                # this is a compare-and-swap: changeFromQuantity is required and must
                # match what is on record, so a variant already at 0 is left alone
                quantities.append({"inventoryItemId": v["iid"], "locationId": LOC,
                                   "quantity": 0, "changeFromQuantity": v["qty"]})
        if bad:
            continue
        if quantities:
            r = gql(M_SET, {"input": {"name": "available", "reason": "correction",
                                      "quantities": quantities},
                            "key": f"mk-hod-2xl-{handle}-{uuid.uuid4().hex[:12]}"})["data"]["inventorySetQuantities"]
            if r["userErrors"]:
                err += 1; print('  setQty failed', handle, r["userErrors"][:1]); continue
        ok += len(vs)
    if i % 20 == 0:
        print(f'  ...{i}/{len(byprod)} products, {ok} variants', flush=True)

print(f'\n{"RESTOCKED" if RESTOCK else "CLOSED"} {ok} variants   errors={err}')
