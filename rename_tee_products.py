#!/usr/bin/env python3
"""
Put "T-Shirt" into the two oversized garment names, in the title and the URL.

"Oversized Light-Soft" and "Oversized Heavy Premium" do not say what the garment
actually is, so shoppers could not tell they were t-shirts. Regular Fit T-Shirt
already reads correctly and is left alone.

    ADHD Oversized Light-Soft            ->  ADHD Oversized Light-Soft T-Shirt
    /products/adhd-oversized-light-soft  ->  /products/adhd-oversized-light-soft-tshirt

Display text uses "T-Shirt" to match the existing Regular Fit T-Shirt; the handle
uses "-tshirt" to match the URL shape asked for.

`redirectNewHandle` makes Shopify create the old -> new redirect itself, so no
existing link breaks. Legacy redirects that already pointed at the old handle are
repointed at the new one by --fix-redirects, so visitors take one hop, not two.

WHAT IS DELIBERATELY NOT TOUCHED: productType and the custom.style metafield stay
"Oversized Light-Soft" / "Oversized Heavy Premium". They are the internal keys -
every automated collection matches on productType, and every script in this repo
plus the swatch CSS keys on style. Renaming them would mean rewriting the collection
rules, optimize_catalog.py and mk-swatches.css to buy nothing a shopper can see.

SHOP and TOKEN from the environment.
  --fix-redirects   also repoint legacy redirects at the new handles
  --run             execute; otherwise reports only
"""
import json, os, sys, time, urllib.request, collections

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
FIXRED = "--fix-redirects" in sys.argv

RENAME = {
    "Oversized Light-Soft":    ("Oversized Light-Soft T-Shirt",    "-oversized-light-soft",    "-oversized-light-soft-tshirt"),
    "Oversized Heavy Premium": ("Oversized Heavy Premium T-Shirt", "-oversized-heavy-premium", "-oversized-heavy-premium-tshirt"),
}

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

Q = '''query($c:String){ products(first:50,after:$c){ pageInfo{hasNextPage endCursor}
 nodes{ id handle title status
  style: metafield(namespace:"custom",key:"style"){value} } } }'''
cur, rows = None, []
while True:
    d = gql(Q, {"c": cur})["data"]["products"]
    rows += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]

plan, already, odd = [], 0, []
for r in rows:
    st = (r["style"] or {}).get("value")
    if st not in RENAME:
        continue
    newsuffix_title, oldh, newh = RENAME[st]
    done_t = r["title"].endswith(" T-Shirt")
    done_h = r["handle"].endswith(newh)
    if done_t and done_h:
        already += 1; continue
    if not r["handle"].endswith(oldh) and not done_h:
        odd.append(r["handle"]); continue
    plan.append({
        "id": r["id"], "status": r["status"],
        "old_title": r["title"],
        "new_title": r["title"] if done_t else r["title"] + " T-Shirt",
        "old_handle": r["handle"],
        "new_handle": r["handle"] if done_h else r["handle"][: -len(oldh)] + newh,
    })

per = collections.Counter()
for r in rows:
    st = (r["style"] or {}).get("value")
    if st in RENAME:
        per[st] += 1
print(f'products in scope : {sum(per.values())}  {dict(per)}')
print(f'already renamed   : {already}')
print(f'to rename         : {len(plan)}')
if odd:
    print(f'!! unexpected handle shape, skipped: {len(odd)} {odd[:5]}')
for p in plan[:4]:
    print(f'   {p["old_title"]}\n     -> {p["new_title"]}')
    print(f'   /products/{p["old_handle"]}\n     -> /products/{p["new_handle"]}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

M = """mutation($product: ProductUpdateInput!){
 productUpdate(product: $product){ product{ id handle title } userErrors{ field message } } }"""
ok = err = 0
mapping = {}
for i, p in enumerate(plan, 1):
    g = gql(M, {"product": {"id": p["id"], "title": p["new_title"],
                            "handle": p["new_handle"], "redirectNewHandle": True}})["data"]["productUpdate"]
    if g["userErrors"]:
        err += 1; print('  failed', p["old_handle"], g["userErrors"][:1]); continue
    mapping[p["old_handle"]] = g["product"]["handle"]
    ok += 1
    if i % 25 == 0:
        print(f'  ...{i}/{len(plan)}  renamed={ok}', flush=True)
print(f'\nRENAMED {ok} products   errors={err}')
json.dump(mapping, open("/tmp/handle_map.json", "w"), indent=1)

if not FIXRED:
    sys.exit()

# a legacy redirect that pointed at the old handle would now take two hops, because
# Shopify just added old -> new on top of it. Repoint it straight at the new handle.
print('\nrepointing legacy redirects...')
cur, reds = None, []
while True:
    d = gql('''query($c:String){ urlRedirects(first:250,after:$c){ pageInfo{hasNextPage endCursor}
      nodes{ id path target } } }''', {"c": cur})["data"]["urlRedirects"]
    reds += d["nodes"]
    if not d["pageInfo"]["hasNextPage"]:
        break
    cur = d["pageInfo"]["endCursor"]
U = """mutation($id:ID!,$redirect:UrlRedirectInput!){
 urlRedirectUpdate(id:$id, urlRedirect:$redirect){ userErrors{ field message } } }"""
fixed = 0
for r in reds:
    t = r["target"]
    if not t.startswith("/products/"):
        continue
    oldh = t[len("/products/"):]
    newh = mapping.get(oldh)
    # also catch ones renamed on an earlier run
    if not newh:
        for st, (_, o, n) in RENAME.items():
            if oldh.endswith(o):
                newh = oldh[: -len(o)] + n
                break
    if not newh or newh == oldh or r["path"] == f"/products/{newh}":
        continue
    g = gql(U, {"id": r["id"], "redirect": {"path": r["path"],
                                            "target": f"/products/{newh}"}})["data"]["urlRedirectUpdate"]
    if g["userErrors"]:
        print('  redirect failed', r["path"], g["userErrors"][:1])
    else:
        fixed += 1
print(f'repointed {fixed} legacy redirects')
