#!/usr/bin/env python3
"""
Apply the Gulf & Europe shipping rates from the client spreadsheet.

Source: Internatonail/filtered_gulf_europe_shipping_rates.xlsx - 43 countries,
6 Gulf and 37 Europe, each with a "first shipment rate" and a "repeat shipment rate".

ONLY THE FIRST RATE IS APPLIED, and that is a limitation worth understanding rather
than a shortcut: the repeat rate is a per-extra-weight-step charge, which Shopify can
only express as weight-banded rates. Every variant in this store has weight 0.0, so
Shopify cannot band anything - a ten-item order weighs the same as a one-item order.
Until real weights are set, a flat first rate is the only honest option, and it
under-charges multi-item international orders.

Rates are EGP. The store cannot present any other currency - Shopify Payments is not
available in Egypt and enabledPresentmentCurrencies is ['EGP'].

Countries in the sheet but not yet in the store get a new zone. Countries already in
the store get their existing rate updated. Countries NOT in the sheet are left alone.

SHOP and TOKEN from the environment.
  --profile NAME   delivery profile to edit (default "General profile")
  --run            execute; otherwise prints the full diff and writes nothing
"""
import json, os, sys, time, urllib.request, collections
import openpyxl

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
PROFILE = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "General profile"
SHEET = "Internatonail/filtered_gulf_europe_shipping_rates.xlsx"

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

wb = openpyxl.load_workbook(SHEET, data_only=True)
ws = wb["Gulf & Europe"]
want = {}
for r in list(ws.iter_rows(values_only=True))[1:]:
    if not r or not r[2]:
        continue
    want[r[2]] = {"region": r[0], "name": r[1], "first": float(r[4]), "repeat": float(r[5])}
print(f'sheet: {len(want)} countries  ({sum(1 for v in want.values() if v["region"]=="Gulf")} Gulf, '
      f'{sum(1 for v in want.values() if v["region"]=="Europe")} Europe)')

Q = '''{ deliveryProfiles(first:10){nodes{ id name default
 profileLocationGroups{ locationGroup{id}
  locationGroupZones(first:100){nodes{
   zone{ id name countries{ id code{countryCode} } }
   methodDefinitions(first:10){nodes{ id name active
     rateProvider{ ... on DeliveryRateDefinition { id price{amount currencyCode} } } }} }} } }} }'''
profs = gql(Q)["data"]["deliveryProfiles"]["nodes"]
prof = next((p for p in profs if p["name"] == PROFILE), None)
if not prof:
    raise SystemExit(f'profile "{PROFILE}" not found: {[p["name"] for p in profs]}')
lg = prof["profileLocationGroups"][0]

cur = {}
for z in lg["locationGroupZones"]["nodes"]:
    for c in z["zone"]["countries"]:
        code = c["code"]["countryCode"]
        md = z["methodDefinitions"]["nodes"]
        cur[code] = {"zoneId": z["zone"]["id"], "zoneName": z["zone"]["name"],
                     "countryId": c["id"],
                     "defId": md[0]["id"] if md else None,
                     "price": float(md[0]["rateProvider"]["price"]["amount"]) if md and md[0].get("rateProvider") else None}

update, create, same = [], [], []
for iso, w in sorted(want.items()):
    c = cur.get(iso)
    if not c:
        create.append((iso, w)); continue
    if c["price"] is not None and abs(c["price"] - w["first"]) < 0.01:
        same.append((iso, w)); continue
    update.append((iso, w, c))

print(f'\n{"ISO":<5}{"country":<22}{"now":>9}{"sheet":>9}{"change":>10}')
for iso, w, c in update:
    print(f'{iso:<5}{w["name"][:20]:<22}{c["price"]:>9.0f}{w["first"]:>9.0f}{w["first"]-c["price"]:>+10.0f}')
print(f'\nnew zones to create ({len(create)}):')
for iso, w in create:
    print(f'   {iso:<5}{w["name"][:22]:<24}{w["first"]:>8.0f}')
print(f'\nalready correct: {len(same)}')
tot_up = sum(w["first"]-c["price"] for _,w,c in update)
print(f'\nSUMMARY  update {len(update)}   create {len(create)}   unchanged {len(same)}')
if update:
    print(f'         average increase {tot_up/len(update):+.0f} EGP, '
          f'range {min(w["first"]-c["price"] for _,w,c in update):+.0f} to {max(w["first"]-c["price"] for _,w,c in update):+.0f}')
print('\nNOT in the sheet and therefore untouched:',
      sorted(set(cur) - set(want) - {"EG"}))
if DRY:
    print('\nDRY RUN - nothing written. add --run to execute.')
    sys.exit()

M_UPD = """mutation($id:ID!,$profile:DeliveryProfileInput!){
 deliveryProfileUpdate(id:$id, profile:$profile){
  profile{id} userErrors{ field message } } }"""

ok = err = 0
for iso, w, c in update:
    g = gql(M_UPD, {"id": prof["id"], "profile": {"locationGroupsToUpdate": [{
        "id": lg["locationGroup"]["id"],
        "zonesToUpdate": [{"id": c["zoneId"], "methodDefinitionsToUpdate": [{
            "id": c["defId"], "name": "Standard",
            "rateDefinition": {"price": {"amount": w["first"], "currencyCode": "EGP"}}}]}]}]}})["data"]["deliveryProfileUpdate"]
    if g["userErrors"]:
        err += 1; print("  update failed", iso, g["userErrors"][:1])
    else:
        ok += 1
print(f'\nUPDATED {ok} rates  errors={err}')

made = 0
for iso, w in create:
    g = gql(M_UPD, {"id": prof["id"], "profile": {"locationGroupsToUpdate": [{
        "id": lg["locationGroup"]["id"],
        "zonesToCreate": [{"name": w["name"], "countries": [{"code": iso}],
            "methodDefinitionsToCreate": [{"name": "Standard",
                "rateDefinition": {"price": {"amount": w["first"], "currencyCode": "EGP"}}}]}]}]}})["data"]["deliveryProfileUpdate"]
    if g["userErrors"]:
        err += 1; print("  create failed", iso, g["userErrors"][:1])
    else:
        made += 1
print(f'CREATED {made} zones   total errors={err}')
