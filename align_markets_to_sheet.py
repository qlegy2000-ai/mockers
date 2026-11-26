#!/usr/bin/env python3
"""
Align Shopify markets to the courier spreadsheet: the sheet's countries are the
only ones open for sale. Everything else is closed.

Source: Internatonail/filtered_gulf_europe_shipping_rates.xlsx
        42 countries - 6 Gulf, 36 Europe. Egypt is the primary market and is
        never touched.

What it does
  Europe market        regions set to exactly the sheet's 36 Europe countries
  "Middle East"        renamed "Gulf", regions set to the sheet's 6
  Africa / Asia /
  "Saudi Arabia"       status -> DRAFT (closed to customers, config preserved,
                       reversible - a delete is not)
  Saudi Profile        its SA delivery rate raised to the sheet's SA rate

Delivery zones for closed countries are deliberately left in place. They are
unreachable once the market is closed and keeping them means re-opening a
country later does not mean re-entering its rate.

SHOP and TOKEN from the environment.
  --run   execute; otherwise prints the full plan and writes nothing
"""
import json, os, sys, time, urllib.request
import openpyxl

SHOP = os.environ["SHOP"]; TOKEN = os.environ["TOKEN"]
DRY = "--run" not in sys.argv
SHEET = "Internatonail/filtered_gulf_europe_shipping_rates.xlsx"
CLOSE = {"Africa", "Asia", "Saudi Arabia"}
GULF_MARKET = "Middle East"          # renamed to "Gulf"
EUROPE_MARKET = "Europe"
KEEP_AS_IS = {"Egypt"}

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

# ---------- the sheet is the source of truth ----------
ws = openpyxl.load_workbook(SHEET, data_only=True)["Gulf & Europe"]
gulf, europe, sa_rate = set(), set(), None
for r in list(ws.iter_rows(values_only=True))[1:]:
    if not r or not r[2]:
        continue
    (gulf if r[0] == "Gulf" else europe).add(r[2])
    if r[2] == "SA":
        sa_rate = float(r[4])
print(f"sheet: {len(gulf)} Gulf {sorted(gulf)}")
print(f"       {len(europe)} Europe {sorted(europe)}")

Q = '''{ markets(first:50){nodes{ id name status
  conditions{ regionsCondition{ applicationLevel
    regions(first:100){nodes{ id ... on MarketRegionCountry { code name } }} } } }} }'''
markets = {m["name"]: m for m in gql(Q)["markets"]["nodes"]}

def regions_of(m):
    rc = (m["conditions"] or {}).get("regionsCondition") or {}
    return {r["code"]: r["id"] for r in ((rc.get("regions") or {}).get("nodes") or []) if r.get("code")}

plan = []
for mname, want in ((EUROPE_MARKET, europe), (GULF_MARKET, gulf)):
    m = markets.get(mname)
    if not m:
        raise SystemExit(f'market "{mname}" not found: {list(markets)}')
    have = regions_of(m)
    drop = sorted(set(have) - want)
    add = sorted(want - set(have))
    plan.append((m, mname, have, drop, add))
    label = "Gulf" if mname == GULF_MARKET else mname
    print(f'\n{mname} -> "{label}"   now {len(have)}  ->  {len(have)-len(drop)+len(add)}')
    print(f'   remove ({len(drop)}): {drop or "-"}')
    print(f'   add    ({len(add)}): {add or "-"}')

print(f'\nclose (status -> DRAFT): {sorted(CLOSE)}')
for n in sorted(CLOSE):
    if n in markets:
        print(f'   {n:<14} {sorted(regions_of(markets[n]))}')
print(f'untouched: {sorted(KEEP_AS_IS)}')
print(f'\nSaudi Profile delivery rate -> {sa_rate:.0f} EGP (sheet)')

if DRY:
    print("\nDRY RUN - nothing written. add --run to execute.")
    sys.exit()

M_UPD = """mutation($id:ID!,$input:MarketUpdateInput!){
  marketUpdate(id:$id, input:$input){ market{ id name status } userErrors{ field message } } }"""

def run(mid, inp, what):
    g = gql(M_UPD, {"id": mid, "input": inp})["marketUpdate"]
    if g["userErrors"]:
        print(f"  !! {what}: {g['userErrors']}"); return False
    print(f"  ok {what}")
    return True

print()
for m, mname, have, drop, add in plan:
    if drop:
        run(m["id"], {"conditions": {"conditionsToDelete": {"regionsCondition": {
            "regionIds": [have[c] for c in drop]}}}}, f"{mname}: removed {len(drop)}")
    if add:
        # MarketConditionsRegionsInput is @oneOf - "regions" must travel alone,
        # applicationLevel cannot be sent alongside it.
        run(m["id"], {"conditions": {"conditionsToAdd": {"regionsCondition": {
            "regions": [{"countryCode": c} for c in add]}}}}, f"{mname}: added {len(add)}")
    if mname == GULF_MARKET:
        run(m["id"], {"name": "Gulf"}, 'renamed "Middle East" -> "Gulf"')

for n in sorted(CLOSE):
    if n in markets:
        run(markets[n]["id"], {"status": "DRAFT"}, f"{n}: closed (DRAFT)")

# ---------- Saudi Profile rate ----------
QP = '''{ deliveryProfiles(first:10){nodes{ id name
 profileLocationGroups{ locationGroup{id} locationGroupZones(first:20){nodes{
   zone{ id name countries{ code{countryCode} } }
   methodDefinitions(first:5){nodes{ id name
     rateProvider{ ... on DeliveryRateDefinition { price{amount} } } }} }} } }} }'''
prof = next((p for p in gql(QP)["deliveryProfiles"]["nodes"] if p["name"] == "Saudi Profile"), None)
if not prof:
    print("\n  !! Saudi Profile not found")
else:
    lg = prof["profileLocationGroups"][0]
    for z in lg["locationGroupZones"]["nodes"]:
        md = z["methodDefinitions"]["nodes"]
        if not md:
            continue
        old = float(md[0]["rateProvider"]["price"]["amount"])
        g = gql("""mutation($id:ID!,$profile:DeliveryProfileInput!){
          deliveryProfileUpdate(id:$id, profile:$profile){ userErrors{ field message } } }""",
          {"id": prof["id"], "profile": {"locationGroupsToUpdate": [{
              "id": lg["locationGroup"]["id"],
              "zonesToUpdate": [{"id": z["zone"]["id"], "methodDefinitionsToUpdate": [{
                  "id": md[0]["id"], "name": md[0]["name"],
                  "rateDefinition": {"price": {"amount": sa_rate, "currencyCode": "EGP"}}}]}]}]}})["deliveryProfileUpdate"]
        print(f'  {"!!" if g["userErrors"] else "ok"} Saudi Profile {z["zone"]["name"]}: '
              f'{old:.0f} -> {sa_rate:.0f}  {g["userErrors"] or ""}')

print("\ndone.")
