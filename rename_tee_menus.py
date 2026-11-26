#!/usr/bin/env python3
"""
Say "T-Shirt" in the navigation and on the collection pages.

The Tees dropdown read "Regular / Oversized Light-Soft / Oversized Heavy Premium",
none of which says t-shirt. This renames the menu entries and the collection titles
to match the product names.

Collection HANDLES are left alone on purpose - the menu items link to them by
handle, and /collections/oversized-light-soft is a working, linked-to URL. Only the
display title changes.

menuUpdate replaces the whole item tree, so every item is sent back, renamed or not;
anything omitted would be deleted.

SHOP and TOKEN from the environment. --run to execute, otherwise reports only.
"""
import json, os, sys, time, urllib.request

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv

# exact current title -> new title, applied only inside the menus named below
TITLES = {
    "Regular":                 "Regular T-Shirt",
    "Oversized Light-Soft":    "Oversized Light-Soft T-Shirt",
    "Oversized Heavy Premium": "Oversized Heavy Premium T-Shirt",
}
MENUS = {"main-menu", "quick-shop"}
COLLECTIONS = {
    "oversized-light-soft":    "Oversized Light-Soft T-Shirt",
    "oversized-heavy-premium": "Oversized Heavy Premium T-Shirt",
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
        return o
    raise SystemExit("throttled out")

menus = gql('''{ menus(first:20){nodes{ id handle title
  items{ id title type url resourceId tags
    items{ id title type url resourceId tags } } }} }''')["data"]["menus"]["nodes"]

def conv(it):
    """Rebuild one item for menuUpdate, renaming it if it is one of ours."""
    out = {"title": TITLES.get(it["title"], it["title"]),
           "type": it["type"], "url": it["url"]}
    if it.get("resourceId"):
        out["resourceId"] = it["resourceId"]
    if it.get("tags"):
        out["tags"] = it["tags"]
    kids = it.get("items") or []
    if kids:
        out["items"] = [conv(k) for k in kids]
    return out

work, changes = [], []
for m in menus:
    if m["handle"] not in MENUS:
        continue
    items = [conv(i) for i in m["items"]]
    def walk(src, dst, path=""):
        for a, b in zip(src, dst):
            if a["title"] != b["title"]:
                changes.append(f'{m["handle"]}: {path}{a["title"]}  ->  {b["title"]}')
            walk(a.get("items") or [], b.get("items") or [], path + a["title"] + " / ")
    walk(m["items"], items)
    work.append({"id": m["id"], "handle": m["handle"], "title": m["title"], "items": items})

cols = gql('''{ collections(first:100){nodes{ id handle title }} }''')["data"]["collections"]["nodes"]
colwork = [{"id": c["id"], "handle": c["handle"], "old": c["title"], "new": COLLECTIONS[c["handle"]]}
           for c in cols if c["handle"] in COLLECTIONS and c["title"] != COLLECTIONS[c["handle"]]]

print(f'menu items to rename : {len(changes)}')
for c in changes:
    print('   ', c)
print(f'collection titles to rename : {len(colwork)}')
for c in colwork:
    print(f'   /collections/{c["handle"]:<26}{c["old"]}  ->  {c["new"]}')
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

MU = """mutation($id:ID!,$title:String!,$handle:String!,$items:[MenuItemUpdateInput!]!){
 menuUpdate(id:$id, title:$title, handle:$handle, items:$items){
  menu{ id } userErrors{ field message } } }"""
for w in work:
    g = gql(MU, {"id": w["id"], "title": w["title"], "handle": w["handle"],
                 "items": w["items"]})["data"]["menuUpdate"]
    print(('  menu ok   ' if not g["userErrors"] else '  menu FAIL '), w["handle"],
          g["userErrors"][:2] if g["userErrors"] else "")

CU = """mutation($input:CollectionInput!){
 collectionUpdate(input:$input){ collection{ id title } userErrors{ field message } } }"""
for c in colwork:
    g = gql(CU, {"input": {"id": c["id"], "title": c["new"]}})["data"]["collectionUpdate"]
    print(('  coll ok   ' if not g["userErrors"] else '  coll FAIL '), c["handle"],
          g["userErrors"][:2] if g["userErrors"] else "")
print('\ndone')
