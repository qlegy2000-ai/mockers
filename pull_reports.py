#!/usr/bin/env python3
"""Pull fresh read-only reports from the live store.

Writes to reports/:
  live_products.csv          one row per product (same columns as before)
  sales_summary.md           headline numbers for the last 60 days
  sales_daily.csv            orders and revenue per day
  sales_by_product.csv       units and revenue per product
  sales_by_type.csv          units and revenue per product type
  sales_by_channel.csv       orders by source, payment gateway and city

Only aggregated order data is saved. No customer names, emails, phones or
addresses are written. Read-only: no mutations.

  SHOP=mockers-shop.myshopify.com TOKEN=proxy-injected python3 pull_reports.py
"""
import csv, json, os, sys, time, urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

SHOP = os.environ.get("SHOP", "mockers-shop.myshopify.com")
TOKEN = os.environ.get("TOKEN", "proxy-injected")
API = f"https://{SHOP}/admin/api/2026-07/graphql.json"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    for attempt in range(5):
        req = urllib.request.Request(API, body, {"Content-Type": "application/json",
                                                 "X-Shopify-Access-Token": TOKEN})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        if "errors" in d:
            if any("THROTTLED" in json.dumps(e) for e in d["errors"]):
                time.sleep(2 + attempt * 2)
                continue
            sys.exit(f"GraphQL error: {d['errors']}")
        avail = d.get("extensions", {}).get("cost", {}).get("throttleStatus", {}).get("currentlyAvailable", 2000)
        if avail < 300:
            time.sleep(3)
        return d["data"]
    sys.exit("Throttled too many times")


def paginate(query, path, variables=None):
    cursor = None
    while True:
        data = gql(query, {**(variables or {}), "cursor": cursor})
        conn = data[path]
        for n in conn["nodes"]:
            yield n
        if not conn["pageInfo"]["hasNextPage"]:
            return
        cursor = conn["pageInfo"]["endCursor"]


PRODUCTS_Q = """
query($cursor: String) {
  products(first: 100, after: $cursor, sortKey: TITLE) {
    pageInfo { hasNextPage endCursor }
    nodes {
      title handle status productType vendor onlineStoreUrl totalInventory
      variantsCount { count }
      priceRangeV2 { minVariantPrice { amount } maxVariantPrice { amount } }
    }
  }
}"""

ORDERS_Q = """
query($cursor: String, $q: String) {
  orders(first: 100, after: $cursor, query: $q, sortKey: CREATED_AT) {
    pageInfo { hasNextPage endCursor }
    nodes {
      createdAt cancelledAt test
      displayFinancialStatus displayFulfillmentStatus
      paymentGatewayNames sourceName
      customerJourneySummary { firstVisit { source referrerUrl } }
      customer { id numberOfOrders }
      shippingAddress { city province countryCodeV2 }
      currentTotalPriceSet { shopMoney { amount } }
      lineItems(first: 50) {
        nodes { title quantity product { productType handle }
                originalTotalSet { shopMoney { amount } } }
      }
    }
  }
}"""


def products_report():
    rows = []
    for p in paginate(PRODUCTS_Q, "products"):
        pr = p["priceRangeV2"]
        rows.append({
            "title": p["title"], "handle": p["handle"], "status": p["status"],
            "type": p["productType"], "vendor": p["vendor"],
            "min_price": float(pr["minVariantPrice"]["amount"]),
            "max_price": float(pr["maxVariantPrice"]["amount"]),
            "variants": p["variantsCount"]["count"],
            "inventory": p["totalInventory"],
            "on_website": "yes" if p["onlineStoreUrl"] else "no",
            "url": p["onlineStoreUrl"] or "",
        })
    write_csv("live_products.csv", rows)
    return rows


def write_csv(name, rows):
    if not rows:
        return
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def orders_report(products):
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=60)).strftime("%Y-%m-%d")
    orders = [o for o in paginate(ORDERS_Q, "orders", {"q": f"created_at:>={since}"})
              if not o["test"]]
    live = [o for o in orders if not o["cancelledAt"]]

    daily = defaultdict(lambda: [0, 0.0])
    by_prod = defaultdict(lambda: [0, 0.0, ""])
    by_type = defaultdict(lambda: [0, 0.0])
    src, gw, city, fin, ful = Counter(), Counter(), Counter(), Counter(), Counter()
    repeat = 0
    revenue = 0.0
    for o in live:
        total = float(o["currentTotalPriceSet"]["shopMoney"]["amount"])
        revenue += total
        day = o["createdAt"][:10]
        daily[day][0] += 1
        daily[day][1] += total
        fv = (o.get("customerJourneySummary") or {}).get("firstVisit") or {}
        src[fv.get("source") or o["sourceName"] or "unknown"] += 1
        gw[" + ".join(o["paymentGatewayNames"]) or "none"] += 1
        a = o["shippingAddress"] or {}
        city[a.get("province") or a.get("city") or "unknown"] += 1
        fin[o["displayFinancialStatus"]] += 1
        ful[o["displayFulfillmentStatus"]] += 1
        if o["customer"] and int(o["customer"]["numberOfOrders"]) > 1:
            repeat += 1
        for li in o["lineItems"]["nodes"]:
            amt = float(li["originalTotalSet"]["shopMoney"]["amount"])
            t = (li["product"] or {}).get("productType") or "unknown"
            by_prod[li["title"]][0] += li["quantity"]
            by_prod[li["title"]][1] += amt
            by_prod[li["title"]][2] = t
            by_type[t][0] += li["quantity"]
            by_type[t][1] += amt

    write_csv("sales_daily.csv", [{"date": d, "orders": v[0], "revenue_egp": round(v[1], 2)}
                                  for d, v in sorted(daily.items())])
    write_csv("sales_by_product.csv", [{"product": k, "type": v[2], "units": v[0], "revenue_egp": round(v[1], 2)}
                                       for k, v in sorted(by_prod.items(), key=lambda x: -x[1][1])])
    write_csv("sales_by_type.csv", [{"type": k, "units": v[0], "revenue_egp": round(v[1], 2)}
                                    for k, v in sorted(by_type.items(), key=lambda x: -x[1][1])])
    ch = []
    for dim, c in (("source", src), ("payment", gw), ("region", city),
                   ("financial_status", fin), ("fulfillment_status", ful)):
        ch += [{"dimension": dim, "value": k, "orders": n} for k, n in c.most_common()]
    write_csv("sales_by_channel.csv", ch)

    n = len(live)
    pct = lambda c: f"{100 * c / n:.0f}%" if n else "-"
    last = max((o["createdAt"] for o in live), default="none")
    status = Counter(p["status"] for p in products)
    types = Counter(p["type"] or "(none)" for p in products if p["status"] == "ACTIVE")
    top = lambda c, k=5: "\n".join(f"| {a} | {b} | {pct(b)} |" for a, b in c.most_common(k))
    md = f"""# Store report ({now:%d %b %Y})

Source: Admin API, live store `{SHOP}`. Window: {since} to {now:%Y-%m-%d} (60 days).
Test orders excluded. Cancelled orders excluded from sales figures.

## Headline
| Metric | Value |
|---|---|
| Orders (not cancelled) | {n} |
| Cancelled | {len(orders) - n} |
| Revenue | EGP {revenue:,.0f} |
| AOV | EGP {revenue / n if n else 0:,.0f} |
| Repeat-customer orders | {repeat} ({pct(repeat)}) |
| Last order | {last[:16].replace('T', ' ')} UTC |

## Catalogue
| Status | Products |
|---|---|
""" + "\n".join(f"| {k} | {v} |" for k, v in status.most_common()) + f"""
| **Total** | **{len(products)}** |

Active products by type:

| Type | Products |
|---|---|
""" + "\n".join(f"| {k} | {v} |" for k, v in types.most_common()) + f"""

## Payment
| Gateway | Orders | Share |
|---|---|---|
{top(gw)}

## Source (first visit)
| Source | Orders | Share |
|---|---|---|
{top(src)}

## Region
| Region | Orders | Share |
|---|---|---|
{top(city)}

## Top product types
| Type | Units | Revenue (EGP) |
|---|---|---|
""" + "\n".join(f"| {k} | {v[0]} | {v[1]:,.0f} |" for k, v in sorted(by_type.items(), key=lambda x: -x[1][1])) + """

## Top 10 products
| Product | Units | Revenue (EGP) |
|---|---|---|
""" + "\n".join(f"| {k} | {v[0]} | {v[1]:,.0f} |" for k, v in sorted(by_prod.items(), key=lambda x: -x[1][1])[:10]) + "\n"
    with open(os.path.join(OUT, "sales_summary.md"), "w") as f:
        f.write(md)
    return md


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    prods = products_report()
    print(f"products: {len(prods)}")
    print(orders_report(prods))
