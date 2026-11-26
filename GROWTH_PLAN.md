# Mockers Growth & Media Buying Plan

Plan only: nothing on the live store has been changed.
Data: live Shopify Admin API, read on 26 Nov 2026. Orders are the last 60 days (29 Sep – 13 Nov), which is all the API token can read.

## 1. Where the store actually is

| Metric (last 60 days) | Value |
|---|---|
| Orders (not cancelled) | 42 |
| Revenue | EGP 70,378 |
| Average order value | EGP 1,676 |
| Best week | EGP 14,852 (12 orders) |
| Last order | **13 Nov: 13 days with zero orders** |
| Payment | 74% Cash on Delivery, 26% Paymob card |
| Location | Cairo 76%, Giza 14%, rest of Egypt ~10%, international 0 |
| Repeat customers | 12 of 42 orders (29%), a strong loyalty signal |
| Last-click source | Instagram 52%, Direct 31%, Facebook 14%, Google 2% |
| Discount codes used | none |

Units sold by line: older "Design" products 18, Sweatshirt 13, Oversized Light-Soft 12, Oversized Heavy Premium 10, Hoodie 7, Regular Fit 5.
Top designs: OLD PEOPLE, NICEST ASSHOLE, AGGRESSIVE DUCK, NEED WEED, WORD FILTER, NATURAL STUPIDITY, TRUST THE PROCESS.

Current prices (EGP): Hoodie 1,599 · Sweatshirt 1,499 · Oversized Heavy 930 (shown as down from 1,100) · Oversized Light-Soft 778 (down from 1,100) · Regular Fit 679 (down from 800) · Thermal Flask 650 · Bucket Hat 750.

## 2. The EGP 500,000 in 3 weeks target: honest maths

- EGP 500k ÷ AOV 1,676 ≈ **300 orders in 21 days**, about 14 a day. The last 60 days averaged **0.7 a day**.
- That is about **7× the last 60 days' total in one-third of the time**, roughly a 20× jump in daily sales.
- Paid ads would have to deliver nearly all of it. Ad spend needed = 500k ÷ ROAS:

| Blended ROAS achieved | Ad spend needed |
|---|---|
| 4.0 (excellent for Egyptian apparel) | ~EGP 125k |
| 3.0 (good) | ~EGP 167k |
| 2.0 (typical while scaling) | ~EGP 250k |

- Cash on delivery adds a gap: 500k in *orders* is not 500k collected. Egyptian COD refusal or return often runs 10–25%, so track **delivered revenue**, not just orders.
- **Verdict:** possible only with about EGP 150–250k of ad budget, the winter peak, and the setup fixes below done first. On a small budget, a realistic first-3-week goal is EGP 120–200k, then scale what works.
- Fill in the real cost per purchase and ROAS from your Meta history; the table above is an assumption until then.

## 3. Issues found: fix BEFORE spending

Ranked by how much ad money each one would waste.

| # | Issue | Why it costs money | Fix |
|---|---|---|---|
| 1 | **Every variant is "infinitely available"** (inventory not tracked, oversell allowed). Beach towels, duffle bags and sweatpants are also live. | Ads can sell items you can't ship, leading to cancellations, refunds and bad reviews. | Hide or draft anything not in the stock list. Turn tracking on for in-stock lines, or set real quantities. |
| 2 | **Bucket hats: only 12 units in total** (7 + 2 + 3). The flask has 199. | A hat ad would sell out in hours. | Use hats only as cart add-ons, not ad heroes. The flask is a good bundle add-on. |
| 3 | **13 days without an order** | Either ads are off or something broke. | Confirm ad status, and run a real test order (COD then cancel) on mobile. |
| 4 | **Tracking not verified.** Last-click data shows Meta ad IDs in UTMs (good), but I can't see Pixel or Conversions API quality from here. | Meta optimises on what it's told. Missing or duplicate Purchase events mean it optimises blind. | In Events Manager, check that the **Purchase event exists, is deduplicated (Pixel + CAPI), with match quality ≥ 6**. Fix before scaling. |
| 5 | **Rename products:** Hoodie → "Oversized HOODIE", Sweatshirt → "Oversized SWEATSHIRT" (the user's request). | Clearer in ads and the catalogue (Advantage+ catalogue ads use product titles). | ~156 titles and handles to change, with URL redirects. Script ready to write on approval. |
| 6 | **Two card payment options** at checkout ("Credit card" and "Pay via Debit/Credit/Wallets/Installments"). | Confuses buyers at the last step. | Keep one Paymob option; label it "Card / Wallet / Installments (valU etc.)". |
| 7 | **Live theme is named "…(staging)"** | Risk of someone editing or publishing over it by mistake. | Rename it and duplicate a backup. |
| 8 | **Markets Europe, Gulf and Pakistan are active with 0 orders** | Scaling abroad before Egypt is proven splits budget and shipping risk. | Keep them live for organic traffic; **no paid ads abroad until Egypt hits target ROAS** (phase 3). |
| 9 | **Hoodie 2XL closure** (old script) is not applied: all sizes are buyable. | If 2XL is really out, it oversells. | Confirm 2XL stock and run `close_hoodie_2xl.py` only if needed. |
| 10 | No discount codes or offers used | Nothing to push urgency or bundles. | See offer plan (§5). |

## 4. What I still need from you (to finish the analysis)

1. **Meta Ads export:** Ads Manager → campaign, ad set and ad level, last 6–12 months, columns: spend, purchases, cost per purchase, purchase value/ROAS, CTR, CPM, frequency, plus the creative names. CSV is fine.
2. **Events Manager screenshot:** Purchase, AddToCart and InitiateCheckout, with event match quality.
3. **Customer list** (full history) for Custom and Lookalike audiences. Use the Shopify customer export; I'll segment it by governorate and spend.
4. **Delivery and return rate per courier** (for the true COD loss).
5. **Instagram insights:** top 10 posts and reels by reach and saves, plus follower demographics.
6. **Monthly budget**, so I can fit the plan to it.
7. **Older order history** (Shopify export since launch): the API only shows 60 days.
8. **Competitor names** you consider direct rivals.
9. **"Codewords" account:** tell me what it is and how to access it.

Customer data: share it as a file into this session, **not pasted in chat**, and it won't be committed to the repo.

## 5. Media buying plan (Egypt first)

**Principles:** spend only behind proven winners, keep few campaigns so Meta learns faster, and judge everything on cost per *delivered* purchase.

### Offers (set up before launch)
- **Bundle:** any 2 tees save 10%; Hoodie + tee combo.
- **Flask as add-on** at checkout or cart (199 in stock, EGP 650).
- **Free shipping over EGP 2,000** (pushes AOV from 1,676 toward 2k+).
- Winter push: Oversized HOODIE / SWEATSHIRT as heroes now (peak season).

### Campaign structure (3 campaigns only)

| Campaign | Audience | Budget share | Creative |
|---|---|---|---|
| **A. Advantage+ Sales (prospecting)** | Egypt, Cairo + Giza + Alexandria first, age 18–34, broad | 60% | 6–10 ads: top designs (OLD PEOPLE, NICEST ASSHOLE, AGGRESSIVE DUCK, NEED WEED…), sarcastic-hook reels, UGC try-ons, catalogue ad |
| **B. Retargeting** | Site visitors 14d, add-to-cart 7d, IG/FB engagers 30d, excluding buyers 30d | 20% | Product carousel, "still thinking?" + bundle offer, reviews |
| **C. Existing customers / lookalike** | Customer list (29% already repeat) + 1–3% lookalike | 20% | New drops, "complete the set", flask/hat add-on |

### Spend and kill rules (protects budget)
- **Test phase (days 1–5):** each ad gets 1.5× target CPA in spend. No purchase by then = **off**.
- **Kill:** CPA above 1.5× target after 2 days, CTR (link) under 0.8%, or frequency above 3.5 in prospecting.
- **Scale:** CPA at or below target for 3 days in a row, then raise budget **+20% per day**, never more (resets learning).
- **Target CPA** = profit per order ÷ 2 until known. Send me product costs and I'll compute exact numbers.
- Review **daily** for 15 min (spend, CPA, ROAS, delivered vs refused); do a full rework weekly.

### Phases
1. **Week 0 (2–3 days):** fix §3 items 1–7, verify tracking, set up offers.
2. **Weeks 1–3:** Egypt, campaigns A/B/C. Scale winners, refresh creatives weekly.
3. **Month 2+:** Gulf (Saudi Arabia is draft; UAE and Kuwait via the Gulf market) with a separate budget and USD/SAR pricing, only after Egypt ROAS ≥ 3.

## 6. Competitor study (to do once names are confirmed)
For each rival: price per product line, offers, shipping and COD terms, ad library (active ads, how long running = winners), angles and hooks, IG engagement. Output: price-position table plus 5 angles to test against them.
Pending: needs competitor list, plus web and Meta Ad Library access from this session.

## 7. Not done / limits
- No Meta, Instagram, Facebook or customer data access yet; none of it was analysed.
- Orders: last 60 days only.
- Mobile checkout and real payment not tested; desktop checkout to the payment step passed (see chat log, 26 Nov).
- Nothing on the live store was changed.
