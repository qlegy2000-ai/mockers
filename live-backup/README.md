# Live store backup — mockers-shop.myshopify.com

Captured: 04 October 2026, 19:15 (Africa/Cairo store time)

**Read-only capture. Nothing on the live store was created, edited or deleted.**

## Contents

| File | Holds | SHA-256 (first 16) |
|---|---|---|
| `products_full.json` | All products, variants, SKUs, prices, media URLs, metafields | `a2a6592348fd6c95` |
| `store_config.json` | Collections, menus, pages, redirects, discounts, publications | `f844047d872a6b9f` |
| `themes/LIVE_Mockers-Updated-S/` | Live theme #126496866346 — 379 files | directory |
| `themes/Waleed-Edit/` | Unpublished theme #140403212330 — 366 files | directory |

## What is in the catalogue

- **127 products total**, 7,814 variants, 1,382 media, 439 product metafields
- **86 ACTIVE and published** — what customers see today (7,735 variants)
- **41 DRAFT** — all "LUCKY PICKS" leftovers, already invisible to customers

### Active products by type

| product_type | Count |
|---|---|
| Design | 64 |
| (none) | 22 |

## Store configuration captured

- Collections: **14**
- Menus: **4**
- Pages: **5**
- URL redirects: **1**
- Discounts: **9**
- Sales channels: Online Store, Point of Sale, Facebook & Instagram, TikTok

### Existing discounts (must be preserved or re-pointed at cutover)

| Title | Type | Status |
|---|---|---|
| SAF100%MOC | DiscountCodeBasic | EXPIRED |
| SAF100%MOCK | DiscountCodeBasic | EXPIRED |
| MARKBYMASSY | DiscountCodeBasic | EXPIRED |
| 10%Off on checkout | DiscountAutomaticBasic | EXPIRED |
| MTOHAMY10% | DiscountCodeBasic | ACTIVE |
| SAVE10FREESHIP | DiscountCodeBasic | EXPIRED |
| SAVE%10FREESHIP | DiscountCodeBasic | EXPIRED |
| SAVE10FREESHIP1 | DiscountCodeBasic | EXPIRED |
| SAVE10FREESHIP11 | DiscountCodeBasic | ACTIVE |

## Restore

- **Theme:** `shopify theme push --path themes/LIVE_Mockers-Updated-S --theme 126496866346 --allow-live`
- **Products:** `products_full.json` carries every field needed to recreate a product, including variant SKUs and metafields. Media is referenced by CDN URL, not re-downloaded — the files stay in Shopify Files unless someone deletes them there.

**Caveat:** this is a catalogue and theme backup. It does **not** contain orders, customers or payment data, by design — the migration never touches them.
