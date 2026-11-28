#!/usr/bin/env python3
"""
Make specific colour variants unavailable (out of stock) on the live store.

Owner rule (27 Nov 2026): dark designs never on dark garments, bright/white designs
never on White/Offwhite. Variants are print-on-demand (untracked + CONTINUE); to take
one off sale it is switched to tracked, quantity 0, policy DENY at every location.

  SHOP=... TOKEN=proxy-injected python3 set_unavailable.py          # dry run
  SHOP=... TOKEN=proxy-injected python3 set_unavailable.py --run
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_upload_file import gql

DRY = "--run" not in sys.argv
DARK = ["Black", "Purple", "Aegean Blue", "Iron Grey", "Dark Green", "Dark Blue", "Beetroot Purple"]
LIGHT = ["Offwhite", "White"]
RULES = {  # product handle -> colours to take off sale
    **{f"{d}-{s}": DARK for d in ["adhd", "andy-the-office", "fail", "grumpy-owl", "mood-swings", "pumba", "serious-lee"]
       for s in ("hoodie", "sweatshirt")},
    **{f"{d}-{s}": LIGHT for d in ["capitalism", "my-therapist"] for s in ("hoodie", "sweatshirt")},
}
# Owner asked (28 Nov) to remove these even though they have a photo: applied regardless of `shot`.
FORCE = {"veganism-hoodie": ["Purple"], "veganism-sweatshirt": ["Dark Blue"]}
for h, cols in FORCE.items():
    RULES[h] = sorted(set(RULES.get(h, [])) | set(cols))
Q = """query($h:String!){ productByHandle(handle:$h){ id title variants(first:100){ nodes{ id title
  selectedOptions{name value} inventoryPolicy image{id}
  inventoryItem{ id tracked inventoryLevels(first:5){ nodes{ location{ id } quantities(names:["available"]){ quantity } } } } } } } }"""
locs = [n["id"] for n in gql("{ locations(first:10){ nodes{ id isActive } } }")["locations"]["nodes"]]
todo = []
for h, cols in RULES.items():
    p = gql(Q, {"h": h})["productByHandle"]
    if not p:
        print("no product", h); continue
    for v in p["variants"]["nodes"]:
        c = {o["name"]: o["value"] for o in v["selectedOptions"]}.get("Color")
        if c in cols and (v["inventoryPolicy"] != "DENY" or not v["inventoryItem"]["tracked"]):
            todo.append((p, v))
    # keep colours the owner already photographed (deliberate versions): skip every size of that colour
    shot = {{o["name"]: o["value"] for o in v["selectedOptions"]}["Color"] for v in p["variants"]["nodes"] if v["image"]}
    shot -= set(FORCE.get(h, []))
    todo = [(pp, vv) for pp, vv in todo if not (pp is p and {o["name"]: o["value"] for o in vv["selectedOptions"]}["Color"] in shot)]
from collections import Counter
print(Counter(f'{p["title"]} / ' + {o["name"]: o["value"] for o in v["selectedOptions"]}["Color"] for p, v in todo))
withimg = {(p["title"], v["title"].split(" / ")[0]) for p, v in todo if v["image"]}
if withimg:
    print("NOTE: these colours currently HAVE a photo and will also go off sale:", sorted(withimg))
print(f"{len(todo)} variants to take off sale")
if DRY:
    print("DRY RUN - add --run"); sys.exit()
for p, v in todo:
    inv = v["inventoryItem"]["id"]
    gql("""mutation($id:ID!){ inventoryItemUpdate(id:$id, input:{tracked:true}){ userErrors{message} } }""", {"id": inv})
    for L in [n["location"]["id"] for n in v["inventoryItem"]["inventoryLevels"]["nodes"]] or locs:
        gql("""mutation($i:InventorySetQuantitiesInput!,$k:String!){ inventorySetQuantities(input:$i) @idempotent(key:$k){ userErrors{message} } }""",
            {"k": str(__import__("uuid").uuid4()), "i": {"name": "available", "reason": "correction",
                   "quantities": [{"inventoryItemId": inv, "locationId": L, "quantity": 0, "changeFromQuantity": None}]}})
    r = gql("""mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{message} } }""",
            {"p": p["id"], "v": [{"id": v["id"], "inventoryPolicy": "DENY"}]})["productVariantsBulkUpdate"]
    if r["userErrors"]:
        print("ERR", p["title"], v["title"], r["userErrors"])
print("done")
