# Live Migration Plan — mockers-shop.myshopify.com

Plan only. **No change is made to the live store until this is approved.**

- **Source (built & tested):** `mockersnew.myshopify.com` — dev store, 275 products, theme `176832053271`
- **Target (untouched):** `mockers-shop.myshopify.com` / `mockers.shop` — live, real orders and rankings
- **Written:** 4 October 2026 · decisions added 5 October

---

## 0. Connection status right now

| Store | Admin API | Theme writes | Status |
|---|---|---|---|
| Dev `mockersnew` | Connected, 174 scopes | Connected (`shptka_`) | **Working** — 275 products, EGP, 3 themes listed |
| Live `mockers-shop` | **No credentials** | **No credentials** | Public pages reachable only |

Everything below about the live store was read from its **public** endpoints
(`/products.json`), which need no key.

---

## 1. What I need from you, and exactly why

### a) Admin API access token — live store

Create a custom app in the live store (Settings → Apps → Develop apps), grant the scopes
below, install, copy the `shpat_…` token.

**Do not reuse the dev store's scope set.** That token has 174 scopes including
`read_customers`, `read_orders` and payments access. The migration needs none of that.
Grant only:

| Scope | Why |
|---|---|
| `read_products`, `write_products` | Create the design × garment products; also covers product metafield definitions |
| `read_product_listings`, `write_product_listings` | Make new products visible to sales channels |
| `read_publications`, `write_publications` | Publish products and collections to Online Store / Shop |
| `read_inventory`, `write_inventory` | Set print-on-demand stock policy |
| `read_files`, `write_files` | Upload product photography |
| `read_online_store_navigation`, `write_online_store_navigation` | Rebuild the Apparel / Winter / Summer menus |
| `read_content`, `write_content` | **URL redirects** — the single most important scope for protecting search rankings |
| `read_online_store_pages`, `write_online_store_pages` | Redirects sit here on some API versions; grant both to be safe |
| `read_themes` | Read the live theme to duplicate it |
| `read_discounts`, `write_discounts` | Build and test the winter sale before handover |

**Deliberately NOT requested:** `read_customers`, `read_orders`, `write_orders`, any
`*_payments_*`, any `customer_*`. The migration never touches customer or order data, so
the token should not be able to.

### b) Theme Access token — live store

Separate and unavoidable. A normal Admin API token **cannot write theme files** — Shopify
requires `write_themes` *plus* a per-app exemption. We hit this on the dev store: REST
`Assets PUT` 404s on every API version and `themeFilesUpsert` returns `ACCESS_DENIED`.

Install the free first-party **Shopify Theme Access** app on the live store, issue a token
for the theme, send the `shptka_…` value.

### c) Three decisions, not credentials

1. **The 14 missing designs** (section 2) — rebuild them too, or go live with 64?
2. **Accessories** — bucket hats, towels, flasks, sweatpants: in or out?
3. **Colours not in your range** — Dark Green hoodie, Burgundy and Cashmere Pink
   sweatshirt. Keep, or retire?

### d) How to send the tokens

Not in chat. Put them in a file and tell me the path, or paste them and **rotate both the
moment the migration finishes**. The dev tokens have been sitting in chat history for two
weeks and should be rotated regardless.

---

## 2. The live store is bigger than the dev rebuild

Read from the live store's public product feed:

| | Count | Covered by the dev rebuild? |
|---|---|---|
| Apparel designs with `product_type = Design` | 64 | **Yes** |
| Apparel designs with **no** `product_type` | **14** | **No — missed** |
| True accessories (hats, towels, flasks, sweatpants) | 8 | No |
| **Total live products** | **86** | |

The original export filtered on `product_type = "Design"`. Fourteen apparel designs have the
same Style / Colour / Size structure but an empty product type, so they were never pulled in:

> MILLENNIALS · SORRY PRINCESS · ROLEX · CROCS · DRUNKIN · STONED · TELEFREAK · WTF ·
> SHIT · FUNNY HOW? · JOMO · INTO-RESTING · NICEST ASSHOLE · ANDY

They carry **47 further design × garment combinations and 1,087 variants**. Rebuilding them
takes the catalogue from 275 to roughly **322 products**.

They also contain a new data error the dev run never saw: one Style value is spelled
**`Swestshirt`**. The normaliser must map it before import or it becomes a sixth garment type.

---

## 3. Principles

1. **Never edit the live theme.** Duplicate first, work on the copy, publish only at the end.
2. **Add before removing.** New products are created alongside the old ones. Nothing is
   deleted during the migration.
3. **Old products are unpublished, not deleted.** They stay in the admin for 30 days as a
   rollback path. Deletion is a separate decision, later.
4. **Redirects before go-live.** Every old product URL must resolve before the old products
   come down, or the store loses its rankings and every ad and social link breaks.
5. **Every destructive step is confirmed with you first**, in writing, with the exact count
   of affected records.

---

## 4. Phases — 10 working days

### Phase 1 · Preparation & backup — Days 1–2
- Full JSON export of all 86 live products with every variant, image URL and metafield
- Full theme download of the live theme, zipped and kept outside the repo
- Export existing URL redirects, menus, collections and current discounts
- Snapshot the live colour/size vocabulary and diff it against the dev normalisation maps
- **Checkpoint:** backup verified restorable before anything is written

### Phase 2 · Catalogue build — Days 3–5
- Run the normaliser over all 78 apparel designs, including the 14 missed and the
  `Swestshirt` fix
- Currency guard: abort unless the live shop reports EGP
- Import as **draft**, not active — nothing customer-visible yet
- Write metafields (`design_id`, `sibling_styles`, `style`, `season`, `is_lead`), tags and SKUs
- Build the 10 automated collections, unpublished for now
- **Checkpoint:** product and variant counts match the plan exactly

### Phase 3 · Theme & storefront — Days 6–8
- Duplicate the live theme; deploy the 6 new files and 9 edits onto the copy
- Configure homepage, navigation, product page, collection pages, footer
- Point the copy at the new collections and verify on the theme preview URL
- **Checkpoint:** you review the preview link before anything is published

### Phase 4 · Cutover & testing — Days 9–10
- Create URL redirects: every old design URL → its new lead product
- Publish new products and collections; unpublish the old 86
- Publish the theme copy
- Test on desktop and mobile: browse, switch garment, add to cart, **complete a real checkout**
- Create the winter discount and verify it reaches every hoodie and sweatshirt and no tee
- Monitor for 24h; rollback plan stays armed
- **Checkpoint:** go-live is your call, not mine

---

## 5. Risks specific to the live store

| Risk | Mitigation |
|---|---|
| **Loss of search rankings.** 86 indexed URLs are replaced. | Redirects created *before* old products are unpublished; verified with a crawl of every old handle. |
| **Paid ads and social links break.** Existing campaigns point at old URLs. | Same redirects cover them. Give me the list of active ad URLs and I will verify each one resolves. |
| **Product feeds reset.** Google/Meta feeds will re-sync 322 items instead of 86. | Expect a re-review period. Schedule the cutover away from a campaign launch. |
| **Orders placed mid-migration.** | New products are drafts until cutover; the old catalogue stays live and sellable throughout. Cutover is a minutes-long window, scheduled off-peak. |
| **An active discount is running.** | Phase 1 exports current discounts; any live promotion is re-pointed at the new collections before the old ones go. |
| **Inventory policy change.** POD "continue selling" applied to real sellable stock. | Confirmed per garment with you before it is written. |
| **Theme regressions on real traffic.** | The duplicate theme is never published until you have reviewed the preview. |

---

## 6. Rollback

At every phase up to publication, rollback is: unpublish the new theme, re-publish the old
products, delete the new ones. The live catalogue is untouched until Phase 4.

After cutover, rollback is: re-publish the original 86 products, re-publish the original
theme, remove the redirects. Possible for the 30 days the old products are retained.

---

## 7. What this changes in the signed proposal

The proposal quotes **275 products across 64 designs**. The live store actually holds
**78 apparel designs plus 8 accessories**. Rebuilding everything is roughly **322 products**
— about 17% more than quoted, plus the accessories if they are included.

I am flagging this now rather than at invoice time. The timeline of 10 working days still
holds; whether the extra scope changes the fee is your call.

---

## 8. Decisions — confirmed 5 October 2026

| Question | Decision |
|---|---|
| Discount codes | **Leave exactly as they are.** No code is created, edited or deleted. The two active codes target all products, so they carry over untouched. The two expired 100%-off codes stay dormant. |
| Accessories (8 products) | **Leave as they are.** Bucket hats, beach towels, thermal flasks and sweatpants are not migrated and not restructured. |
| Three off-spec colours | **Keep.** Dark Green hoodie, Burgundy sweatshirt and Cashmere Pink sweatshirt stay, on their current images. |
| "Lucky Picks" (41 drafts) | **Leave as drafts.** Untouched. |

**Standing instruction: do not begin work.** Nothing is to be created, edited or deleted on
either store until explicitly told to start.

### Open issue these decisions do not resolve

The dev store holds **64 designs / 275 products**. The live store has **78 apparel designs**.
Fourteen exist only on live and were never built in the new model:

> andy · crocs · drunkin · funny-how · into-resting · jomo · millennials · rolex ·
> shit · sorry-princess · stoned · telefreak · the-nicest-asshole · wtf

A straight dev → live import therefore covers 64 of 78. The remaining 14 would stay on the
old Style × Colour × Size structure, leaving the live catalogue **mixed**: 64 designs in the
new model, 14 in the old. Collections, discounts and the garment picker would work for the
64 and not for the 14.

This must be settled before Day One. See the message of 5 October for the three options.

---

## 9. Do not touch — hard constraints

Instructed 5 October 2026. These are absolute, for the whole migration.

### Never read, never written

| Area | Constraint |
|---|---|
| **Orders** | No order is read, edited, cancelled, refunded or exported. No order API call is made at all. |
| **Customers** | No customer record is read, edited, created, deleted, tagged or exported. |
| **Payments & payouts** | Shopify Payments, payouts, bank details and disputes are never queried. |
| **Gift cards & store credit** | Never read or modified. |
| **Draft orders, returns, fulfilments** | Untouched. |

The live token was granted all 174 scopes, so it *can* reach this data. **That is a risk to
close, not a permission to use.** Two options, your call:
1. Reissue the token with only the ~14 scopes the migration needs — makes the constraint
   technically enforced rather than a promise; or
2. Leave it and rotate the token the moment the migration finishes.

### Not configured, not installed, not removed

| Area | Constraint |
|---|---|
| **Apps** | Nothing installed, uninstalled, reconfigured or re-authorised. |
| **Markets & currencies** | No market, region, currency or pricing rule changed. |
| **Shipping, taxes, duties** | Untouched. |
| **Checkout & payment settings** | Untouched. |
| **Domains & DNS** | Untouched. |
| **Notifications & email templates** | Untouched. |
| **Staff, permissions, store settings** | Untouched. |
| **Discounts** | Left exactly as they are — see section 8. |

### Existing themes

| Theme | ID | Treatment |
|---|---|---|
| Mockers - Updated - S | `126496866346` | **LIVE. Read only.** Duplicated, never edited. Stays published until the final switch and remains available to republish. |
| Dawn | `126496768042` | Not opened, not edited, not deleted. |
| Copy of MINIMOG — Halloween | `136804991018` | Not opened, not edited, not deleted. |
| Waleed Edit | `140403212330` | Backed up read-only. Not edited, not deleted. |
| Copy of MINIMOG — Lucky Picks | `146055790634` | Not opened, not edited, not deleted. |

All storefront work happens on a **new duplicate** created for the purpose. No existing
theme is modified or removed at any point, including after go-live.

### What the migration does write

For the avoidance of doubt, the only things created or changed on the live store are:

- New **products** and their variants, images and metafields
- New **collections**
- New **URL redirects**
- The **menus**, re-pointed at the new collections
- One **new duplicate theme**, and at the final step which theme is published
- The old products set to **unpublished** — not deleted, kept 30 days

Nothing else.

---

## 10. Scope settled — all 78 designs (5 October 2026)

**Decision: the 14 designs that exist only on the live store are optimised the same way as
the other 64.** No mixed catalogue. Confirmed against the live data:

| | |
|---|---|
| Apparel designs on live | **78** |
| Design × garment products to create | **322** |
| Variants in the current (old) structure | 7,711 |

### Data problems to fix during the rebuild

Measured from the live backup, not assumed:

**Garment names** — one typo, `Swestshirt` (1 product). Left unmapped it becomes a sixth
garment type and breaks every collection rule.

**Sizes** — 15 distinct spellings, **9 of them wrong**, normalising to the 6 canonical sizes:

> `2X-Large` · `2x-Large` · `Large` · `Medium` · `Small` · `Smalll` · `X- Large` ·
> `X-Lagre` · `X-Large`

**Colours** — 17 distinct values, including **`Off-White` and `Offwhite` as separate
colours**, plus `White` as a third. These are the same garment under three names and must be
merged, or they become three swatches and three sets of variants.

### Revised timeline

| Stage | Time |
|---|---|
| Optimise the 14 missing designs on the dev store | **1 day** |
| Import all 78 designs to live + storefront + go-live | **2 days** |
| **Total** | **3 working days** |

The client-facing steps document still says 2 working days. It needs reissuing at 3 before
it goes out.

**Still not started.** Awaiting explicit go-ahead.
