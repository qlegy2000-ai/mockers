#!/usr/bin/env python3
"""Dec 2026 offers (owner-approved 28 Nov): automatic free shipping in Egypt (no minimum) and
a free tee (any tee type, 100% off, 1 per order) when hoodies/sweatshirts in the cart total >= 2,990 EGP.
  SHOP=... TOKEN=proxy-injected python3 setup_offers.py [--run]"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_upload_file import gql
DRY = "--run" not in sys.argv
cid = lambda h: gql('query($h:String!){ collectionByHandle(handle:$h){ id } }', {"h": h})["collectionByHandle"]["id"]
winter = cid("winter-all-garments"); tees = [cid(h) for h in ("regular-fit-t-shirt", "oversized-heavy-premium", "oversized-light-soft")]
START = "2026-11-28T00:00:00+02:00"
ship = {"title": "FREE SHIPPING (Egypt)", "startsAt": START, "destination": {"countries": {"add": ["EG"]}},
        "combinesWith": {"productDiscounts": True, "orderDiscounts": True}}
bxgy = {"title": "FREE TEE with 2 hoodies/sweatshirts (2,990+)", "startsAt": START, "usesPerOrderLimit": "1",
        "customerBuys": {"value": {"amount": "2990"}, "items": {"collections": {"add": [winter]}}},
        "customerGets": {"value": {"discountOnQuantity": {"quantity": "1", "effect": {"percentage": 1.0}}},
                         "items": {"collections": {"add": tees}}},
        "combinesWith": {"shippingDiscounts": True}}
print("free shipping:", ship["title"]); print("free tee:", bxgy["title"], "buy collection", winter, "get", tees)
if DRY: print("DRY RUN"); sys.exit()
r = gql("""mutation($d:DiscountAutomaticFreeShippingInput!){ discountAutomaticFreeShippingCreate(freeShippingAutomaticDiscount:$d){
  automaticDiscountNode{ id } userErrors{ field message } } }""", {"d": ship})["discountAutomaticFreeShippingCreate"]; print(r)
r = gql("""mutation($d:DiscountAutomaticBxgyInput!){ discountAutomaticBxgyCreate(automaticBxgyDiscount:$d){
  automaticDiscountNode{ id } userErrors{ field message } } }""", {"d": bxgy})["discountAutomaticBxgyCreate"]; print(r)
