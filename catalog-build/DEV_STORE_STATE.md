# Mockers dev store — state

Store **mockersnew.myshopify.com** · currency **EGP** · theme *Minimog v4.1.0* (live)
All numbers below were verified against the rendered storefront, not just the API.

## Catalogue

| | |
|---|---|
| Products | **275** (design × garment) |
| Variants | **5,563** |
| Import | created 273, skipped 2, **failed 0** |
| Metafields | `custom.design_id`, `design_title`, `style`, `season`, `is_lead`, `sibling_styles` (product) · `blank_sku` (variant) |
| Tags | `lead` (64) · `lead-winter` (54) · `lead-summer` (61) · `design:*` · `style:*` · `color:*` |

## Collections — 11, all automated, all published

**For discounts** — whole garment sets:

| Handle | n | Rule |
|---|---|---|
| `hoodie` | 54 | type = Hoodie |
| `sweatshirt` | 54 | type = Sweatshirt |
| `regular-fit-t-shirt` | 45 | type = Regular Fit T-Shirt |
| `oversized-heavy-premium` | 61 | type = Oversized Heavy Premium |
| `oversized-light-soft` | 61 | type = Oversized Light-Soft |
| **`winter-collection`** | **108** | Hoodie OR Sweatshirt |
| **`summer-collection`** | **167** | the three tee types |

**For browsing** — one card per design:

| Handle | n | Rule |
|---|---|---|
| `all-designs` | 64 | tag = lead |
| `winter-designs` | 54 | tag = lead-winter |
| `summer-designs` | 61 | tag = lead-summer |

> Point discounts at `winter-collection` / `summer-collection`.
> Point navigation and homepage rows at the `*-designs` ones.

## Theme — pushed via Theme Access token

| File | Purpose |
|---|---|
| `snippets/design-style-switcher.liquid` | garment switcher, per-garment prices, theme-agnostic CSS |
| `templates/product.json` | switcher block between price and variant picker |
| `sections/product-quickview.liquid` | switcher in quick-view too |
| `snippets/product-card-4.liquid` | design-first cards |
| `templates/index.json` | homepage rebuilt |

No JavaScript, no app, no script tags. The earlier script-tag workaround and its two
uploaded JS files were deleted.

### Homepage order

```
0 custom-code · 1 slider
2 SHOP BY DESIGN ....... all-designs, 12 cards
3 SHOP BY GARMENT ...... 5 tiles with live counts (45/61/61/54/54)
4 scrolling-promotion
5 WINTER ............... winter-designs
6 SUMMER ............... summer-designs
7-12 brand content · 13 newsletter
```

### Card behaviour

- Lead card → `ADHD` / *5 styles · from LE 679.00*
- Any other → `ADHD` / *Hoodie*

So `winter-collection` can hold both garments of a design without two identical tiles.

## Verified on the storefront

- `/` `/collections/{all,winter,summer}-designs` `/collections/hoodie`
  `/collections/winter-collection` `/products/adhd-hoodie` → all **200**
- Style switcher renders 5 options with correct prices and sibling links
- No duplicate design cards in any browsing collection
- `winter-collection` repeats a design only with distinct garment sublines

## Still open

- **72 variant images show the wrong colour** — carried from the old catalogue
- **88 colour/garment combos have no image at all**

Both enumerated in `QA_REPORT.md`. These need correct mockup files, not code.

- Homepage section 9 is an `image-with-text` for **"VARSITY ROUND NECK SWEATSHIRT"** —
  a garment not in the five styles. Probably stale; left in place pending a decision.
- 4 `custom-content` sections remain on the homepage; some may now be redundant.

## Credentials used

Admin API token, Theme Access token and the storefront password were all shared in
chat. Rotate the two tokens when the work is done.
