# Mockers: project memory

Egyptian sarcastic-slogan apparel brand. Shopify store + catalogue scripts + growth plan.

## Stores
- **Live:** `mockers-shop.myshopify.com` / mockers.shop. Currency EGP, Basic plan, ~520 products (401 active).
- **Dev (old):** `mockersnew.myshopify.com`, not on the network allowlist.
- Live theme is named "Mockers catalogue rebuild (staging)".

## API access (cloud sessions, QlegyCAI environment)
- Admin API token is saved as a **network secret** for `mockers-shop.myshopify.com`. The proxy injects `X-Shopify-Access-Token`. Never paste or commit tokens.
- Scripts read `SHOP`/`TOKEN` env vars. Run them with a placeholder token:
  `SHOP=mockers-shop.myshopify.com TOKEN=proxy-injected python3 <script>.py`
- Admin API version used: `2026-07` (GraphQL). Orders are readable for the last 60 days only.
- The token is broad (orders, customers, payments); the owner was advised to narrow its scopes.
- Allowed hosts added for storefront tests: mockers.shop, www.mockers.shop, cdn.shopify.com, checkout.pci.shopifyinc.com.
- Do NOT use the ShopMCP connector (it points at a different store, qlegystore). Use the Admin API directly.

## Working rules from the owner
- **Live store: plan and advise only.** No changes without explicit approval. Scripts: dry run first (`--run` executes).
- Be economical: no repeated history checks or long re-analysis.
- Customer data: never commit to the repo.

## Catalogue facts
- Product types: Hoodie (1,599 EGP), Sweatshirt (1,499), Oversized Heavy Premium (930, compare-at 1,100), Oversized Light-Soft (778, compare-at 1,100), Regular Fit T-Shirt (679, compare-at 800). Options: `Color`, `Size` (XS–2XL).
- Hoodie colours: Black, Purple, Aegean Blue, Iron Grey, Offwhite.
- Print on demand: variants untracked + CONTINUE policy, so everything shows as in stock. `close_hoodie_2xl.py` closes 2XL; it is NOT applied on live (all sizes sellable as of 26 Nov 2026).
- In stock (owner, Nov 2026): hoodies, sweatshirts, oversized tees, regular tees, black thermal flask (199), bucket hats (12 total). Beach towels, duffle bags and sweatpants are live but not on the stock list.
- Pending rename: Hoodie → "Oversized HOODIE", Sweatshirt → "Oversized SWEATSHIRT" (awaiting approval).
- Draft test product "Waleed" (15 variants, 100 EGP) was created on live 26 Nov 2026.

## Status (26 Nov 2026)
- Last 60 days: 42 orders, EGP 70k, AOV 1,676, 74% COD, 76% Cairo, 29% repeat, Instagram is the top source. No orders since 13 Nov.
- Desktop checkout tested to the payment step: works. Two card options shown (possible duplication).
- Goal: EGP 500k orders in 3 weeks. See `GROWTH_PLAN.md` for maths, fixes, the 3-campaign Meta structure and kill/scale rules.
- Meta: not connected yet. Options: read-only system-user token for `graph.facebook.com`, or a third-party custom connector. Still waiting on Meta CSV export, customer list, budget, product costs, competitors, "Codewords" access.

## Key docs
`GROWTH_PLAN.md`, `MOCKERS_CATALOGUE_PLAYBOOK.md`, `MIGRATION_PLAN_LIVE.md`, `catalog-build/`, `reports/live_products.csv`.
