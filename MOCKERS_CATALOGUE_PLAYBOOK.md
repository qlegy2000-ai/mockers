# Mockers Catalogue — Playbook & Findings

Everything learned while rebuilding the Mockers catalogue, written so the next person
can run the store, repeat the work on the live shop, or pick up where this left off.

- **Store worked on:** `mockersnew.myshopify.com` (development store)
- **Live store not yet touched:** `mockers.shop`
- **Theme:** Minimog OS 2.0 v4.1.0 — `theme-export-mockers-shop-minimog-v4-1-0-12-23` (ID `169958703127`)
- **Admin API version used throughout:** `2026-07`
- **Last updated:** 29 September 2026

---

## 1. The root problem, stated once

The garment was stored as a **variant option**, not as a product.

One design was a single Shopify product with three options — Style × Colour × Size —
up to 137 variants on one product.

Shopify's entire merchandising layer works on **products**:

| Feature | Operates on | Can it see an option value? |
|---|---|---|
| Collections | Products | No |
| Discounts | Products / collections / variants | Not by option |
| Inventory | Variants, but reported per product | Not groupable by option |
| Reports & analytics | Products | No |
| Google / Meta feeds | Products | No |

So "25% off all hoodies" was unbuildable: there was no hoodie product and no collection
that could hold one. Discounting the old "Hoodies" collection discounted the t-shirts too,
because every product in it was a whole design.

**The fix:** one product = one design on one garment. Colour and Size stay as variants.
This is the Threadless model. 64 designs × their garments = **275 products / 5,563 variants**.

---

## 2. The collection architecture — and why it has three layers

This is the part that is easy to get wrong, and it was gotten wrong once. A collection
that is right for discounting is wrong for browsing.

- A **discount** must reach *every* garment, or the sale misses items.
- A **browse page** must show each design *once*, or the shopper scrolls past the same
  artwork two or three times.

One collection cannot do both. So there are three sets:

### Set 1 — Garment collections (shoppable, and discountable)

| Handle | Products | Rule |
|---|---|---|
| `hoodie` | 54 | `TYPE EQUALS Hoodie` |
| `sweatshirt` | 54 | `TYPE EQUALS Sweatshirt` |
| `regular-fit-t-shirt` | 45 | `TYPE EQUALS Regular Fit T-Shirt` |
| `oversized-heavy-premium` | 61 | `TYPE EQUALS Oversized Heavy Premium` |
| `oversized-light-soft` | 61 | `TYPE EQUALS Oversized Light-Soft` |

Each holds one garment only, so a design physically cannot appear twice.
These are safe for both jobs.

### Set 2 — Season collections (shoppable — what the menu and homepage link to)

| Handle | Products | Rule |
|---|---|---|
| `all-designs` | 64 | `TAG EQUALS lead` |
| `winter-collection` | 54 | `TAG EQUALS lead-winter` |
| `summer-collection` | 61 | `TAG EQUALS lead-summer` |

One card per design. The product shown is the **cheapest garment in that season** for
that design, so the shopper lands on the lowest price and can switch garment on the PDP.

### Set 3 — Discount targets (hidden from the storefront)

| Handle | Products | Rule | Published |
|---|---|---|---|
| `winter-all-garments` | 108 | `TYPE = Hoodie OR Sweatshirt` | **No** |
| `summer-all-garments` | 167 | `TYPE = Regular Fit T-Shirt OR Oversized Heavy Premium OR Oversized Light-Soft` | **No** |

> **Point discounts at Set 3. Point menus and the homepage at Set 2.**

These two are unpublished from Online Store *and* Shop, so they return 404 on the
storefront and cannot be stumbled into. **Unpublishing does not affect discounts** —
discount targeting uses collection IDs and is independent of sales-channel publication.

### The mistake that caused this layout

Originally `winter-collection` held all 108 winter products and the menu pointed at it.
The result: every design appeared twice, once as a sweatshirt and once as a hoodie.
The deduped collections existed (`winter-designs` / `summer-designs`) but only the
homepage used them — the menu still pointed at the 108-product version.

Rather than re-point the menu, the **handles were swapped** so the obvious, pretty URL
(`/collections/winter-collection`) is the customer-facing one. The all-garment rules moved
to the renamed `winter-all-garments` / `summer-all-garments`. The menu needed no change.

**Rule of thumb:** if a handle looks like something a customer would see in a URL,
it should be a deduped browse collection. Discount containers get ugly names and stay hidden.

### Why not dedupe in Liquid instead?

It was considered and rejected. **Shopify paginates before Liquid filters run.** Dropping
duplicate cards inside the template would give a 24-product page that renders 12 cards,
then 9, then 14 — uneven pages and a broken count. Deduping at the *collection rule* level
is the only clean way.

---

## 3. Metafields and tags — the glue

### Product metafields (namespace `custom`)

| Key | Type | Purpose |
|---|---|---|
| `design_id` | single_line_text | Groups all garments of one design. The join key for everything. |
| `design_title` | single_line_text | Human name of the design, used on cards. |
| `style` | single_line_text | Garment name, mirrors `product.type`. |
| `season` | single_line_text | `winter` or `summer`. |
| `is_lead` | boolean | True on the one product that represents the design. |
| `sibling_styles` | list.product_reference | Every other garment of the same design. Drives the PDP garment picker. |

### Variant metafield

| Key | Purpose |
|---|---|
| `custom.blank_sku` | Which physical blank garment to order from the supplier. |

### Tags that drive collections

| Tag | On | Feeds |
|---|---|---|
| `lead` | Cheapest garment of each design (64 products) | `all-designs` |
| `lead-winter` | Cheapest winter garment of each design (54) | `winter-collection` |
| `lead-summer` | Cheapest summer garment of each design (61) | `summer-collection` |

**Note:** `lead-winter` resolves to the Sweatshirt on every design, because sweatshirts
(1350) are cheaper than hoodies (1450). That is intended — the hoodie is one click away
on the PDP.

---

## 4. Price book and garment families

```
Hoodie                   1450.00 / compare 1599.00   winter
Sweatshirt               1350.00 / compare 1499.00   winter
Regular Fit T-Shirt       679.00 / compare  800.00   summer
Oversized Heavy Premium   930.00 / compare 1100.00   summer
Oversized Light-Soft      778.00 / compare 1100.00   summer
```

All EGP. Sizes normalised to six: `XS S M L XL 2XL`. Colours normalised to 15.

---

## 5. Shopify API gotchas worth remembering

**Variant image URLs are null at `productCreate` time.**
The CDN has not processed the media yet, so you cannot map variants to images by URL on
the create response. Fall back to *position*: the Nth media node corresponds to the Nth
URL you supplied.

```python
supplied = [u.split("?")[0].rsplit("/", 1)[-1] for u in p["images"][:150]]
for idx, n in enumerate(pc["product"]["media"]["nodes"]):
    u = (n.get("image") or {}).get("url")
    key = u.split("?")[0].rsplit("/", 1)[-1] if u else None
    if not key and idx < len(supplied):
        key = supplied[idx]          # positional fallback
```

**Always check shop currency before importing prices.** Prices carry no currency; they are
interpreted in the shop's currency. An import into a USD shop silently prices everything
in USD.

```python
cur = gql("{ shop { currencyCode } }")["data"]["shop"]["currencyCode"]
if cur != "EGP": sys.exit("wrong currency — prices would import as " + cur)
```

Changing the shop currency may be blocked by `UNIFIED_MARKETS_ENABLED`; it then has to be
done in the admin UI, not via `marketCurrencySettingsUpdate`.

**Menu items of type `PAGE` need `resourceId`, not `url`.** Passing a URL fails with
"Couldn't create link Contact, page not found". Same for `COLLECTION` and `PRODUCT`.

**Creating a collection does not publish it.** Products and collections publish separately.
Eight collections were created, products were live, and every menu link led nowhere —
because no collection had been published to any sales channel. Use `publishablePublish`.

**`tagsAdd` one product at a time is far too slow.** Use GraphQL alias batching, ~20 per
request. Tagging 115 products went from minutes to about four seconds.

```graphql
mutation { a0: tagsAdd(id:"gid://...1", tags:["lead"]) { userErrors { message } }
           a1: tagsAdd(id:"gid://...2", tags:["lead"]) { userErrors { message } } }
```

**The search index lags.** A `tag:` query can return stale results for a minute or so after
tagging. Read products directly when verifying; don't trust `products(query:"tag:x")`
immediately after a write.

**Theme file writes need `write_themes` *and* a Shopify exemption.** A normal custom-app
Admin token cannot write theme files — REST `Assets PUT` 404s on every API version, and
`themeFilesUpsert` / `themeCreate` return `ACCESS_DENIED`. It is not a scope you can
tick. **Theme Access app tokens (`shptka_…`) carry the exemption.** Use the Shopify CLI:

```bash
SHOPIFY_CLI_THEME_TOKEN=shptka_... shopify theme push \
  --store mockersnew.myshopify.com --theme 169958703127 \
  --only templates/index.json --allow-live
```

---

## 6. Theme work — files changed and why

All ten confirmed live on theme `169958703127`.

| File | What it does |
|---|---|
| `snippets/design-style-switcher.liquid` | The garment picker on the PDP. Reads `sibling_styles`. |
| `assets/mk-style-switcher.js` | Makes the picker work **inside quickview**. Must be global. |
| `assets/mk-swatches.css` | Forces correct colour swatch backgrounds. |
| `snippets/product-card-4.liquid` | Design-first cards: design name headline, garment subline. |
| `sections/product-recommendations.liquid` | Dedupes "You May Also Like" by design. |
| `assets/recently-viewed-products.js` | Dedupes "Recently Viewed" by design. |
| `sections/product-quickview.liquid` | Renders the picker in the quickview modal. |
| `templates/product.json` | Two-column PDP (`layout-7` → `layout-6`), picker after price. |
| `templates/index.json` | Rebuilt homepage. |
| `layout/theme.liquid` | Loads the two global assets. |

### Theme gotchas that cost real time

**Scripts inside AJAX-loaded HTML never execute.** The garment picker worked on the PDP and
did nothing in quickview, because the handler lived inside the snippet — and the snippet
only renders on product pages, *and* a `<script>` parsed out of an AJAX response is inert.
The fix was moving it to a global asset loaded in `theme.liquid`.

> Lesson: "I verified the markup shipped" is not "I verified the code ran."
> The real check was `mkStyleSwitcherBound` in the console on a **collection** page.

**Do not call `qv.close()` before `qv.fetchHtml()`.** Minimog's `Modal` class runs its
cleanup on a 200 ms timer (`transitionDuration = 200`). A fetch that resolves in ~80 ms
gets deleted by cleanup that fires afterwards. Remove the old node directly instead:

```js
var current = document.querySelector('.m-product-quickview');
if (current) current.remove();
qv.fetchHtml(opt.getAttribute('data-mk-handle'));
```

**Do not key quickview behaviour on `location.pathname`.** In a modal the URL is still the
collection URL, not the product's.

**Colour swatches went black** because `variant-picker.js` does
`label.style.backgroundColor = c || n` and the theme's colour map only knew `gingham` and
`flannel`. Any name CSS cannot parse — "Dark Green" — is discarded and falls through to
black. `mk-swatches.css` overrides all 15 colours with `!important` (it has to beat an
inline style), plus `background-image: none` and a ring on White.

**Don't assume `prefers-color-scheme`.** The storefront is always black regardless of the
OS setting, so the picker CSS uses neutral alpha values and `currentColor` rather than
light/dark variants.

**`templates/*.json` is not plain JSON** — Shopify allows a leading `/* … */` comment block.
`json.load()` fails at line 1. Strip to after `*/` before parsing:

```python
s = open('templates/index.json').read()
data = json.loads(s[s.index('*/') + 2:])
```

**The recently-viewed dedupe hardcodes garment suffixes.** Adding a sixth garment means
updating this regex:

```js
const STYLE_SUFFIX = /-(regular-fit-t-shirt|oversized-light-soft|oversized-heavy-premium|sweatshirt|hoodie)$/;
```

**Capture loop-invariant values before the loop.** In `product-recommendations.liquid` the
loop rebinds `product`, so the current design must be captured into `mk_current_design`
first or the dedupe compares each item against itself.

---

## 6b. The footer (four columns)

`sections/footer-group.json` → section `footer`, four blocks at `width: 25%`:

| Block | Type | Holds |
|---|---|---|
| `footer_about` | `custom_text` | Logo image (max 180px) + short about paragraph |
| `footer_quick_links` | `menu` → `quick-links` | Home, All Designs, Contact, Search, Privacy Policy, Your Privacy Choices |
| `footer_quick_shop` | `menu` → `quick-shop` | Winter, Summer, and the five garment collections |
| `footer_contact` | `our_store` | Email, phone, social icons |

### Things that bite here

**`our_store` reads email and phone from *theme settings*, not from the block.**
The block only has on/off switches. The values live in `config/settings_data.json` as
`contact_email` and `contact_phone_number`. Same for every social URL
(`social_facebook_link`, `social_instagram_link`, `social_tiktok_link`,
`social_whatsapp_link`, … 14 platforms supported).

**Never leave `contact_phone_number` unset.** Shopify falls back to the schema default,
which in this theme is the vendor's demo number `+84 (0)387 392 056` — a Vietnamese
number would have shipped on an Egyptian store. It is currently set to `""`.

**An empty string is truthy in Liquid.** Only `nil` and `false` are falsy, so
`{% if settings.contact_phone_number %}` passes on `""` and renders `<a href="tel:"></a>`.
That is why `show_phone` is `false` rather than relying on the blank value. To turn the
phone on: set `contact_phone_number` **and** flip `show_phone` to `true`. Both, or neither.

**The image picker reference must match the real filename exactly.** The footer logo was
silently blank because the setting pointed at
`shopify://shop_images/MOCKERS_1_….png` while the uploaded file is `…_1.avif`. A wrong
`shopify://` reference does not error — the block just renders nothing. Confirm the real
name via the Files API before trusting it:

```graphql
{ files(first:50, query:"MOCKERS"){ nodes{ ... on MediaImage { image { url width height } } } } }
```

Shopify transcodes the `.avif` on delivery (it serves PNG/WebP by `Accept` header), so the
`.avif` reference is fine.

**Images are revealed by JavaScript.** `responsive-image img { opacity: 0 }` until the
theme adds `m-image-loaded`. A static screenshot of saved HTML always shows the grey
`--bg-card-placeholder` box — that is a no-JS artifact, not a broken image.

**"Your Privacy Choices" renders conditionally.** Shopify region-gates that link, so the
column shows 5 of its 6 items for most visitors. Expected, not a bug.

**Footer palette:** `color_footer_bg` / `color_footer_bottom_bg` are `#1b1b1b`, text white,
link hover `#fbcd06` (the Mockers yellow). The yellow logo reads well on it.

**Menus are separate objects from the theme.** `quick-links` and `quick-shop` were created
with `menuCreate`; the footer blocks reference them by handle. A block pointing at a menu
handle that does not exist renders an empty column — which is what the old `brand-menu`
"Information" block was doing.

---

## 6c. The UI/UX rebuild (working copy theme)

Built from a reference recording of a separate Mockers prototype
(`preview-r0p8kme-….codeword.run`). **All of it lives on a duplicate theme, not the live one.**

| Theme | ID | Role |
|---|---|---|
| `theme-export-mockers-shop-minimog-v4-1-0-12-23` | `169958703127` | **MAIN** (live on the dev store) |
| `Mockers UI-UX rebuild (working copy)` | `176832053271` | unpublished |

Local source of truth: `theme-working/` (full 378-file pull, with `.theme-target` naming the theme ID).

### What was built

- **`sections/mk-hero.liquid`** (new) — oversized headline with an `<em>` accent, a stat row
  (blocks), and two CTAs. The old `slider` hero is `disabled`, not deleted.
- **Yellow nav marquee** — a second `scrolling-promotion` section, `custom_class: mk-navmarquee`.
  The theme already had this section type; no new marquee code was written.
- **Fit-first main menu** — `Tees ▾` (Regular / Light-Soft / Heavy Premium) then Hoodies,
  Sweatshirts, All Designs, Winter, Summer, Contact.
- **Garment chips on cards** (`snippets/product-card-4.liquid`) — every fit the design exists in,
  on every card, current one filled and first. Labels shortened by `snippets/mk-garment-label.liquid`.
- **Sold-out eyebrow** — `<GARMENT> — SOLD OUT` above the title. Currently never fires, because
  inventory policy is `continue` (print-on-demand). It only appears if tracking is turned on.
- **`assets/mk-ui.css`** — loaded globally from `layout/theme.liquid`.

### Things that bite here

**Never gate card logic on `product.metafields.custom.is_lead` directly.** In Liquid a metafield
object is truthy whenever it *exists*, so a stored `false` still reads as true. Use `.value`, or
avoid the check. The first version of the chips did this and worked only by accident, because
the metafield is absent on non-lead products rather than set to false.

**Do not give a menu item `href="#"`.** Minimog reads a bare `#` as a submenu toggle and attaches
`data-toggle-submenu`, so tapping it on mobile opens an empty panel. The "coming soon" note points
at `/collections/regular-fit-t-shirt#coming-soon` instead — harmless destination, and a stable
`a[href$="#coming-soon"]` selector to mute it with `pointer-events: none`.

**Section range settings must land on their step.** `scrolling-promotion`'s `text_size` has
`step: 2`, so `13` is rejected at push time with "Setting 'text_size' must be a step in the range".
Push fails the whole file, not just that setting.

**Counting rendered elements by class name over-counts.** `class="mk-chip mk-chip--current"`
matches `mk-chip` twice, and the section's own `<style>` block contains every class name again.
Match the full opening tag (`<div class="mk-card-chips">`) when verifying.

### The one thing that is NOT finished

**Colour / Size / Category filters need a 2-minute admin action that has no API.**
Filters are enabled on the collection template (`show_filter: true`,
`filters_type: storefront_filters`, `sidebar: fixed`), and Price + Availability work now.
Those two are all Shopify exposes by default. Verified directly:

```
name="filter.v.availability", "filter.v.price.gte", "filter.v.price.lte"   <- all that exists
```

To get Colour, Size and Product type: install the free first-party **Shopify Search & Discovery**
app, then Online Store → Navigation → Filters → add them. The theme picks them up with **no code
change**. There is no Admin API for storefront filter configuration, and `themeDuplicate` and
`appInstallations` are both blocked for this token, so this cannot be automated from here.

---

## 6d. Light catalogue, and the hidden prices

The storefront was dark everywhere. It now follows the reference build: **black header,
hero, announcement bar and footer; light catalogue below.**

Settings changed in `config/settings_data.json`: `color_main_bg` `#f2f0ed`,
`color_body_text` `#171717`, `color_heading_text` `#111111`, `color_sub_text` `#6b6b6b`,
`color_border` `#e0ddd6`, and the buttons inverted (`color_btn_bg` `#111111` /
`color_btn_text` `#ffffff`) because a white button on a light page is invisible.

**The colour settings are not all named `color_*`.** Four more were white or brand-yellow
and became unreadable on white. Grep for *every* setting whose value is a colour, not just
the `color_` prefix:

| Setting | Was | Now |
|---|---|---|
| `product_title_color` | `#ffffff` | `#111111` |
| `prod_desc_color` | `#ffffff` | `#444444` |
| `prod_type_color` | `#ffffff` | `#6b6b6b` |
| `prod_regular_price_color` | `#fbcd06` | `#111111` |

`product_title_color` is the one that bites: it feeds `--product-title-color`, which beats
a plain `.m-product-card__name { color: … }` rule, so card titles went invisible.

### Card prices were hidden on purpose, and should not be any more

Two sections carried `custom_css: ['.m-price {display: none;}']` — `templates/collection.json`
section `main`, and the SHOP BY DESIGN section in `templates/index.json`. Both predate this
work and both are now removed.

That rule made sense under the old model: one product was a whole design, so its card price
was a meaningless 679–1450 range. Under design × garment every card is one garment with one
real price, so the price belongs there — and the reference build shows one on every card.

**Section-level `custom_css` renders as an inline `<style>` scoped to a generated section id**
(`#shopify-section-template--<id>__main .m-price{display:none}`). It will not show up when
grepping the theme's `.css` assets, and the generated id differs per theme, so it cannot be
matched on literally. When something is invisible and no stylesheet explains it, dump the
page's inline `<style>` blocks and check every template's `custom_css` key.

### Verifying a themed page offline

Do not hand-assemble a preview by concatenating stylesheets — the cascade order will not
match the real page and the render will lie. It produced two different answers about whether
prices rendered, and both were wrong.

Instead take the saved HTML as-is, rewrite protocol-relative URLs, inject a `<base>`, and let
the browser fetch the real assets in the real order:

```python
h = re.sub(r'(?<![:\w])//shop\.myshopify\.com', 'https://shop.myshopify.com', h)
h = h.replace('<head>', '<head><base href="https://shop.myshopify.com/">', 1)
```

Remember two no-JS artifacts that are **not** bugs: `responsive-image img` stays at
`opacity: 0` until the theme adds `m-image-loaded`, and colour swatches keep the
`option-loading` class that `mk-swatches.css` forces transparent.

---

## 6e. Real garment colours, and adding client photography

**The swatch hexes are no longer estimates for the winter garments.** Mockers supplied the
real values on 29 Sept 2026. Those first values were sampled from the darkest part of each
garment and rendered as five indistinguishable black circles in a row, so each was re-sampled
from the mid-tone of the garment photo. **`assets/mk-swatches.css` is the source of truth** —
it is what the storefront renders — and `optimize_catalog.py`'s `COLOR_HEX` is kept equal to it:

| Colour | First estimate | Client value | **In use** |
|---|---|---|---|
| Aegean Blue | `#2E5A8A` | `#0e2833` | `#1c4054` |
| Iron Grey | `#6E6E6E` | `#242323` | `#302e2e` |
| Dark Green | `#1F3A2E` | `#0a2008` | `#2e422b` |
| Dark Blue | `#1B2A4A` | `#041224` | `#1b2533` |
| Beetroot Purple | `#5C2A42` | `#2a0611` | `#46131c` |
| Purple | *(new)* | `#381f3d` | `#4e2c49` |
| Offwhite | *(new)* | — | `#eee3cc` |

The remaining eight colours are still estimates.

**Two colours are garment-specific.** The hoodie blanks for Purple and Aegean Blue are not the
same shades as the sweatshirt/tee blanks, so `product-option.liquid` tags every option container
with `data-mk-style="{{ product.metafields.custom.style }}"` and `mk-swatches.css` carries
`[data-mk-style="Hoodie"]` overrides. `optimize_catalog.py` mirrors them in `GARMENT_HEX`:

| Garment | Colour | Hex |
|---|---|---|
| Hoodie | Purple | `#2a1b3d` |
| Hoodie | Aegean Blue | `#11334f` |

Every other garment keeps the generic value. Adding a third garment-specific colour means one
block in the CSS and one line in `GARMENT_HEX` — nothing else.

**Naming:** the client says *Offwhite* and *Augean Blue*; the catalogue says *White* and
*Aegean Blue*. Swatch rules exist for both spellings of the first; the second is only ever
written *Aegean* in product data.

### Design-level colour availability

A design whose artwork is white ink cannot be printed on Offwhite — the cream garment
(`#eee3cc`) swallows it. This is a **per-design** rule, not a garment rule: it covers that
design's hoodie and its sweatshirt alike, while the garment range still includes Offwhite for
every other design. Encoded as `WHITE_ARTWORK` + `winter_colours()` in `optimize_catalog.py`,
and as the same constant in `fill_winter_colours.py`.

**Do not decide membership from the design tile.** The tile shows the artwork on a dark
garment and is wrong twice over:

| Trap | Example | Why the tile misleads |
|---|---|---|
| **Knockout white** | `wish-you-were-beer` | White text sits *inside* a black badge. The garment colour shows through the letters, so it reads on cream exactly as well as on black. |
| **Re-coloured artwork** | `breaking-sad`, `capitalism`, `i-love-your-personality`, `see-right-through-you` | Mockers re-draw the artwork per garment. These look like white text on their dark tile but ship in green or teal on the cream one. |

A design belongs in `WHITE_ARTWORK` only when white ink sits **directly on the garment** with
no coloured version in evidence. The decisive test is the Offwhite variant's own mockup photo:
pull it from the variant image and look at it. A pixel test over the tile gets roughly a third
of the calls wrong.

The ten designs that fail it: `andy`, `dear-music`, `if-only`, `illegal`, `kill-bic`,
`millennials`, `national-psychotic`, `paranoid`, `pros-cons`, `trans-parent`.

**Three Offwhite colourways already on sale fail the same test** and were left alone rather
than pulled, because removing a live colourway was not part of the brief:

| Design | What breaks on cream |
|---|---|
| `natural-stupidity` | “FORGET” and “WORK ON” are white — the slogan reads with two lines missing. |
| `the-rolling-eyes` | The caption under the eyes is white and effectively invisible. |
| `need-weed` | The scrabble tiles are white, so only the green letters float on the garment. |

When a supplied Drive folder is the source instead, it encodes the same rule by simply omitting
the Offwhite mockup — *the set of images supplied for a design is the set of colours that design
should offer.*

### Every design in all five garments

A design is meant to exist as all five products. The old catalogue only listed the garments
that had been photographed, so on 16 Oct 2026 **33 of the 78 designs were short one or more**
— 69 products in all. All 69 were built with `create_missing_products.py` (1,815 variants).
**Every design now exists in all five garments: 390 products, 78 of each.**

The summer ranges had never been standardised — each tee carried whatever its old listing
happened to have, down to colours used on a single product. Agreed 16 Oct 2026: take the
colours the clear majority already use, drop the strays, and **leave existing products alone**
(unlike winter, the summer range was not trimmed). Sizes follow each garment's own majority
rather than one rule for all, because the blanks genuinely differ. Both live in
`optimize_catalog.py` as `SUMMER_RANGE` / `GARMENT_SIZES`.

| Garment | Colours | Sizes |
|---|---|---|
| Regular Fit T-Shirt | Black, White, Burgundy, Cashmere Pink, Aegean Blue, Pistache Green | S M L XL |
| Oversized Light-Soft | Black, White, Burgundy, Pink, Earth Green | S M L XL 2XL |
| Oversized Heavy Premium | Black, White, Burgundy, Pink, Royal Dark Green | XS S M L XL |

**The white-ink rule spans both seasons.** Winter's cream Offwhite and summer's pure White
fail the same way, so `WHITE_ARTWORK` governs both through `garment_colours()` and the `PALE`
map. The catalogue corroborates it: **9 of the 12 white-artwork designs had never been sold as
a White t-shirt** — the rule was being followed by hand before it was written down.

A design gaining its **first** winter product has never been assessed against the Offwhite
rule, so assess it then. The cheapest evidence is the design's existing **White** summer
mockup: White is less forgiving than cream, so anything that reads on White reads on Offwhite.
Nine of the sixteen had one. `palestine` and `personality-disorder` failed and were withheld.

**Two traps in `productCreate`, both now handled in the script:**

| Trap | What happens | Fix |
|---|---|---|
| It does not make an empty product | One variant is built from the FIRST value of each option, at **0.00 with no SKU**. `productVariantsBulkCreate` then rejects the entire batch with *"The variant 'Black / XS' already exists"*, leaving the product live and free. | Create everything **except** that combination, then `productVariantsBulkUpdate` the placeholder with the real price and SKU. |
| Status is not publication | A product can be `ACTIVE` and still 404, because it was never published to a sales channel. The Admin API reports nothing wrong. | Create as `DRAFT`, populate, then set `ACTIVE` **and** `publishablePublish`. A failure then leaves a draft, not a free product. |

`rebuild_design_groups.py` must run before `apply_lead_tags.py`, `tag_season_leads.py` or
`set_sibling_styles.py`. All three read `catalog-build/design_groups.json`, which was
originally generated from the export CSV and goes stale the moment a product is created or
drafted — a stale file silently skips new products, so their garment switcher stays empty.
**`tag_season_leads.py` has no `--dry-run`**: passing the flag runs it for real.

### Winter range as it stands

Filled out on live, 16 Oct 2026. Every hoodie and sweatshirt now carries its full range:

| | |
|---|---|
| Products | 156 — 78 hoodie, 78 sweatshirt (every design) |
| Variants | 4,536 |
| Whole catalogue | 390 apparel products, 9,622 variants |
| Sizes | `XS S M L XL 2XL` on all 124, no exceptions |
| Colours | 5 per garment, or 4 where Offwhite is withheld (20 products) |
| Price | Hoodie 1599, Sweatshirt 1499, no compare-at |
| Stock | Tracking off, policy `CONTINUE` throughout |

Built by `fill_winter_colours.py` (420 variants) then `fill_size_holes.py` (8). The second
script exists because the first only creates colours a product lacks entirely — a colour that
was already present but short a size keeps its gap, which is how three products ended up
selling 2XL in one colour and not the rest. **Run them in that order, and verify the grid
afterwards rather than trusting the create counts.**

### Pulling images out of a shared Drive folder

A Drive folder link renders its contents with JavaScript, so fetching the page gives nothing.
Use the embedded view, which returns plain HTML for a publicly-shared folder and needs no
credentials:

```
https://drive.google.com/embeddedfolderview?id=<FOLDER_ID>#list
```

Entries come back as `id="entry-<FILE_ID>"` plus a title; download each with
`https://drive.google.com/uc?export=download&id=<FILE_ID>`. If the fetch redirects to
`accounts.google.com`, the folder is not shared publicly yet.

### Attaching images to variants

`stagedUploadsCreate` (POST multipart to the returned url) → `productCreateMedia` →
poll until every media node reports `status: READY` → `productVariantsBulkUpdate` with
`mediaId`. Adding a colour that does not exist yet is `productVariantsBulkCreate` with
`optionValues: [{optionName: "Color", name: "..."}, {optionName: "Size", name: "..."}]`,
and must carry `inventoryPolicy: CONTINUE`, `inventoryItem.tracked: false`, the
`MK-{STYLE}-{DESIGN}-{COLOUR}-{SIZE}` SKU and the `custom.blank_sku` metafield, or the new
variants will not behave like the rest of the catalogue.

---

## 7. Operating the store

### Run a winter sale
1. Discounts → Create discount → **Amount off products** → Automatic
2. Applies to: **Specific collections** → `Winter - All Garments (Discount Target)`
3. Set value and dates. Save.

Covers every hoodie and sweatshirt across every design, including designs added next week,
and touches no t-shirt. **Do not pick "Winter Collection"** — that one is the browse
collection and holds only 54 of the 108 winter products.

### Add a new design
Create one product per garment. Each needs: `product.type` set to the exact garment name,
the `custom.design_id` metafield, and the `lead` / `lead-winter` / `lead-summer` tags on the
cheapest product in each group. Every collection then picks it up automatically.

### Add a sixth garment type
1. Create the products with the new `product.type`.
2. Create an automated collection `TYPE EQUALS <name>`, publish it.
3. Add the type to `winter-all-garments` or `summer-all-garments` rules.
4. Add the handle suffix to `STYLE_SUFFIX` in `recently-viewed-products.js`.
5. Add it to the Apparel menu.

Note steps 3 and 4 are the ones that get forgotten.

### Inventory
Tracking is **off** with policy **continue** — it is print-on-demand, so there is no unit
stock to count. Physical blanks are tracked on a 243-SKU master list
(`catalog-build/blanks_inventory_master.csv`), one row per real garment/colour/size.
This also fixed ~25% of the catalogue showing as sold out (4,216 variants parked at a fake
"1000", 1,730 stuck at "0").

---

## 7b. Product photography backlog

`reports/missing_product_images.csv` + `reports/images-needed/Mockers_Images_Needed.pdf`
(17 Oct 2026). A row per product and colour that is **on sale without a photo of that
colour** — 894 rows across 221 of the 390 products. Only colours that actually exist as
variants are listed, so it is a real shoot list, not a wish list.

The rows split into three groups, and the distinction matters because two of them are
different jobs:

| Group | What | Images | Work |
|---|---|---|---|
| **A** | The 69 products built 16 Oct | 355 | Nothing exists but the design tile. Create all. |
| **B** | Older products that already hold photos | 530 | Their galleries hold **1,393 photos not linked to any colour**. Check before creating. |
| **C** | Older products with no photos | 9 | Create all. |

**Group B is not an attaching job.** Those photos were uploaded in bulk and never assigned,
and a known share show the wrong garment — see §6 on the filename audit, where 2,609 of 3,476
images could not be identified by filename at all. Each needs looking at.

Regenerate by reading every active apparel product, treating a colour as photographed when any
of its variants has `image` or `media`, and comparing against the colours the product sells.
**Do not compare against the agreed range** — existing summer products were deliberately left
untrimmed, so the range would list colours they do not stock.

---

## 7c. Closing a size without deleting it

Hoodie 2XL was taken off sale on 19 Oct 2026, pending restock. **378 variants across all 78
hoodies.** Nothing was deleted: the variants, their SKUs, prices and place in the size picker
are untouched, so the restock is one command and no customer link breaks.

Reverse with `python3 close_hoodie_2xl.py --restock --run`.

**Why "set it to zero" does not work here.** Every variant in this catalogue ships with
inventory tracking OFF and policy CONTINUE, because Mockers print on demand — and Shopify
treats an untracked variant as infinitely available, so the quantity is simply ignored.
Showing a size as sold out needs all three:

| | Value | Why |
|---|---|---|
| `inventoryItem.tracked` | `true` | otherwise Shopify never counts stock at all |
| available quantity | `0` | at the single location |
| `inventoryPolicy` | `DENY` | otherwise it keeps selling past zero |

Restocking sets policy back to `CONTINUE` and tracking back to `false` — the state every other
variant is in.

**Three API traps in `inventorySetQuantities`,** all hit on the way through:

| Error | Cause |
|---|---|
| *Field `ignoreCompareQuantity` is not defined* | That field does not exist in 2026-07. |
| *must include the following argument: `changeFromQuantity`* | It is a compare-and-swap — you must state the quantity you believe is on record. A variant already at 0 needs no call at all. |
| *The `@idempotent` directive is required* | The mutation needs `@idempotent(key: ...)` with a unique key, so a retry cannot apply the same stock change twice. |

Most variants already sat at 0 with a live inventory level, so the quantity call was only
needed for a minority — worth checking first rather than writing every row.

---

## 7d. Garment naming — display vs internal

"Oversized Light-Soft" and "Oversized Heavy Premium" never said what the garment was, so
shoppers could not tell they were t-shirts. Renamed 19 Oct 2026, **customer-facing text only**:

| Where | Before | After |
|---|---|---|
| Product title | `ADHD Oversized Light-Soft` | `ADHD Oversized Light-Soft T-Shirt` |
| Product handle | `adhd-oversized-light-soft` | `adhd-oversized-light-soft-tshirt` |
| Tees dropdown | Regular / Oversized Light-Soft / … | Regular T-Shirt / Oversized Light-Soft T-Shirt / … |
| Collection title | Oversized Light-Soft | Oversized Light-Soft T-Shirt |
| PDP garment switcher | Oversized Light-Soft | Oversized Light-Soft T-Shirt |

156 products. Display text uses **T-Shirt**, handles use **-tshirt**.

**`productType` and `custom.style` were deliberately left as `Oversized Light-Soft`.** They are
the internal keys: every automated collection matches on `productType`, and `optimize_catalog.py`,
`mk-swatches.css` (`data-mk-style`) and every script here key on `style`. Renaming them buys a
shopper nothing and would mean rewriting the collection rules and all the maps. Instead
`snippets/mk-garment-name.liquid` maps style → display name, and anywhere a name is *shown*
renders through it. **Collection handles were left alone too** — the menu links to them and the
URLs are already in circulation.

**The longer names broke the Tees dropdown**, and fixing it needs two rules, not one —
`mk-ui.css`, scoped to `.m-menu__item--dropdown`:

| Theme rule | Effect on a long label |
|---|---|
| `.m-mega-menu { width:100%; min-width:250px }` | panel pinned at 250px, so the text folds mid-word |
| `.m-sub-menu__item > a { overflow:hidden }` | once it cannot fold, it is cropped instead |

So `width: max-content` alone still crops, and `white-space: nowrap` alone still folds. Both are
needed. Widening `.m-mega-menu__container` / `__inner` does nothing — they are not what holds the
width.

Handles were changed with `redirectNewHandle: true`, which makes Shopify write the old → new
redirect itself. The 17 legacy redirects that already pointed at an old handle were repointed at
the new one, so `/products/illegal` takes one hop rather than two.

**Theme files now go through the Admin API.** `themeFilesUpsert` works with the `shpat_` token —
the old Theme Access `shptka_` token is dead and the Asset REST endpoint returns 401. Use the
GraphQL mutation against theme `184985190569` (role MAIN).

---

## 7e. Mockups from the Canva deck

Mockers produce the garment photography in a Canva deck ("Ultra-Realistic Product Images").
As of 21 Oct 2026 it holds **40 winter mockups on slides 41-80** covering 8 of the 16 new
winter designs, in the order the products were built. Slides 1-40 are unrelated material.

`reports/canva_export_list.csv` maps every slide to a product handle and colour.
`reports/canva_winter_progress.csv` tracks all 156 winter images for the 16 new designs.

**Reading the deck without Canva access.** The public `/view` link returns real HTML: the page
thumbnails are `media.canva.com/v2/document-image/...type:B` URLs in page order, one per slide.
Two traps:

* the `csig` signature is **bound to the dimensions in the URL** - editing `width:`/`height:`
  to ask for a bigger render returns 403. Fetch them exactly as found.
* those thumbnails are only **400x500**, far below the 1024-3375px the store's real product
  images use. The full-resolution originals are lazy-loaded per slide and are *not* in the
  initial payload, and `?page=N` returns the same payload regardless. **Print-resolution
  mockups can only come from a Canva export**, not from scraping the link.

**Before attaching anything, check the deck against the colour rules.** The 21 Oct review found
one slide that must never be uploaded - `palestine` sweatshirt in Offwhite - because white
artwork disappears on cream and that colourway is not sold. It also found two colourways shot
twice (slides 52 and 53 repeat 44 and 49). The deck is not self-validating; the CSV is.

**Canva page numbers are NOT stable.** On 28 Oct 2026 the deck went from 80 to 123 pages
and a page inserted near the front shifted every mockup by **+1** - what was slide 41 became 42.
A batch exported before that date needs the v1 map, a batch after needs v2. Attaching with the
wrong map puts the right photo on the wrong product, so `--map` is a required argument with no
default. Old export folders are archived under `canva-exports-archive/` so they cannot be
re-run against the newer map by accident.

**Re-anchor on content, never on arithmetic.** To confirm a shift, compare the images you
already exported against the freshly downloaded page thumbnails and find the offset that scores
highest. Two cautions learned doing it: a 20x20 grayscale signature matches on *pose and
background*, so two different designs shot on the same model score ~0.95 and look like a match -
only ~0.99+ means the same image. And a genuine reshoot of the same product and colour scores
*lower* (~0.8) than a false positive, so neither a high nor a low score is conclusive on its own.
Confirm by eye.

**Watch for colours the catalogue does not sell.** The 28 Oct batch included five mockups on a
**white** sweatshirt; the range is Black, Offwhite, Dark Green, Dark Blue and Beetroot Purple,
with no white. Cream and white are easy to confuse at thumbnail size - separate them by warmth
(R minus B): the Offwhite blank measures +14 to +37, a true white measures about 0.

**Attaching:** `attach_canva_images.py --dir <folder> [--run]` reads exports, takes the slide
number as the **last number in the filename**, uploads via `stagedUploadsCreate` +
`productCreateMedia`, waits for `status: READY`, then pins the image to every variant of that
colour with `productVariantAppendMedia`. Anything whose number is not in the export list is
reported and skipped rather than guessed at. Waiting for READY matters - pinning media that is
still PROCESSING is what left variant images empty during the original migration.

---

## 8. Scripts in this repo

| Script | Purpose |
|---|---|
| `optimize_catalog.py` | Transforms the export CSV into the design × garment model. Holds all the normalisation maps and the price book. |
| `push_to_shopify.py` | GraphQL importer. Idempotent, with the currency guard. |
| `apply_lead_tags.py` | Tags the 64 lead products. |
| `set_sibling_styles.py` | Writes `sibling_styles` on all 275 products. |
| `tag_season_leads.py` | Tags the 54 winter / 61 summer season leads. |
| `cutover.py` | Publishes the migrated drafts on live and drafts the old products. |
| `fix_offwhite.py` | Renames Offwhite → White on the three summer garments. |
| `trim_winter_colours.py` | Deletes winter variants outside the five-colour range. |
| `fill_winter_colours.py` | The inverse: adds the colours a winter product is missing, applying the `WHITE_ARTWORK` Offwhite rule, then reorders both option axes. |
| `fill_size_holes.py` | Closes (colour × size) holes the colour fill cannot see. |
| `create_missing_products.py` | Builds the design × garment products that do not exist yet, to the agreed range. `--season winter\|summer\|all`. |
| `repair_new_products.py` | Populates products whose variant calls failed. Requires `--handles`. |
| `rebuild_design_groups.py` | Regenerates `design_groups.json` from live. **Run before the three tagging scripts.** |
| `set_winter_prices.py` | Hoodie 1599 / Sweatshirt 1499, compare-at cleared. |
| `fix_size_order.py` | Puts Size values back in XS→3XL order after any variant write. |
| `remove_winter_xs.py` / `add_winter_xs.py` | XS off and back onto winter garments. |

**Any script that creates variants must be followed by a size reorder** — Shopify appends new
option values to the end, so a fresh colour or size lands after `2XL` and the picker reads out
of order. `fill_winter_colours.py` and `add_winter_xs.py` do this themselves; `push_to_shopify.py`
does not, so run `fix_size_order.py` after it.

Outputs live in `catalog-build/`, including backups taken before destructive steps
(`BACKUP_devstore_113_products_pre_delete.json`, `BACKUP_theme_templates_index.json`).

Both importers are safe to re-run. Environment: `SHOP` and `TOKEN`.

---

## 9. PDF report generation

`reports/Mockers_Catalogue_Rebuild_Report.{html,pdf}`, built from the Qlegy template.

Playwright was unavailable, so rendering used headless Chrome:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=out.pdf --virtual-time-budget=6000 "file://$PWD/report.html"
```

**The pagination trap:** Chrome lays out content without knowing a `position: fixed` footer
exists, so paragraphs get drawn straight through it. Reserving space with `@page` bottom
margins *does* stop the overlap but breaks the repeating footer — it jumps to the top of
every page. Negative offsets do not help either.

What works: keep `@page { margin: 0 }`, give the footer `bottom: 8mm`, give `.doc` a
24 mm bottom padding, put `page-break-inside: avoid` on blocks, split long tables, and add
explicit `.fresh-page` breaks on a handful of sections. **Editing any section's length can
re-break a later section** — after every content edit, re-verify.

Verification is automated rather than eyeballed. Rasterise, then compare each page's
footer band against a known-clean page; the cover legitimately differs:

```bash
pdftoppm -png -r 110 report.pdf rp
# then diff the bottom 58px band of each page against page 2
```

---

## 10. Still outstanding

**Needs artwork, not code:**
- 72 variant images show the **wrong colour** (e.g. every colour of a design serving the
  black photo, so choosing White shows a black shirt).
- 88 colour/garment combinations have **no image** and fall back to a plain colour block.

Both problems existed in the old catalogue and were carried across unchanged. Every case is
listed by design, garment and colour in `catalog-build/QA_REPORT.md`.

**Needs a decision:**
- The 15 swatch hex values in `mk-swatches.css` are estimates derived from colour names.
  They should be confirmed against the real garments.
- A homepage block still promotes a "Varsity Round Neck Sweatshirt", which is not one of
  the five garments sold.
- Four older `custom-content` homepage blocks may now be redundant.

**Not yet done:**
- Everything above is on the **development store**. The live `mockers.shop` is untouched.
  `catalog-build/url_redirects.csv` exists for the live migration — old design URLs must
  redirect to the new lead product URLs or the store loses its search rankings.

---

## 11. Credentials

Tokens were kept only in a session scratchpad at `chmod 600` and never written into this
project directory. **Both the Admin API token and the Theme Access token should be rotated
now that the work is complete.** Do not commit tokens to this repo.
