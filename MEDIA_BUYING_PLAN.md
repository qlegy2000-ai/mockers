# Mockers: Media Buying Plan (Dec 2026, 10k EGP test)

Built from our own data: 12 months of Meta spend, 60 days of store sales, unit costs and the owner's offers.
Goal: the most profitable orders per pound spent, then scale only what is proven.

---

## 1. The maths first (why this plan looks the way it does)

**Unit cost: hoodie/sweatshirt ~515 EGP, any tee 400 EGP (incl. print + packaging). Free shipping costs us ~80 EGP per order (Cairo/Giza; up to 205 for far zones). COD refusals 5-10%.**

| Basket | Price | Margin after item cost + free shipping | Max we can pay Meta and still profit |
|---|---|---|---|
| 1 Regular tee | 679 | 199 | ~0: never advertise tees alone |
| 1 Oversized heavy tee | 930 | 450 | ~250 |
| 1 Sweatshirt | 1,499 | 904 | ~600 |
| 1 Hoodie | 1,599 | 1,004 | ~650 |
| 2 Sweatshirts + free tee | 2,998 | 1,488 | ~1,000 |
| 2 Hoodies + free tee | 3,198 | 1,688 | ~1,100 |

With the 200 EGP post discount (no minimum, owner decision): a tee-only order breaks even (199 - 200), every hoodie/sweatshirt order stays clearly profitable.

- **Target CPA: 350 EGP. Kill line: 600 EGP.** Our best-ever ads ran 192-410 CPA, so 350 is realistic, not hopeful.
- **Ads sell hoodies and sweatshirts only.** Tees appear only as the free gift or an add-on.
- **Target ROAS: 4x or better** on purchase value (break-even is about 1.6-2x).

### Offer tweaks (small changes, big effect)
1. **Free shipping, no minimum:** keep it. For COD buyers it removes the last objection. It's the headline of every ad.
2. **Free tee above 3,000:** set the threshold to **2,990 EGP**. 2 sweatshirts = 2,998, so then *any two winter pieces* qualify. "Buy any 2 hoodies/sweatshirts, get a tee free" is a much easier sentence to sell than a number. The gift tee costs us 515 but lifts the order margin from ~950 to ~1,400.
3. **200 EGP for an Instagram post (no minimum, owner decision):**
   - The post must be **public, tag @mockers.eg, and stay up 30 days**. The DM must arrive **before the order ships** (we reduce the COD amount). Otherwise it becomes a code for the next order (which also brings repeat orders).
   - This offer is our **free content engine.** Every post is ad creative (reshare with permission), and we have no content production.

---

## 2. Before spending 1 pound (blockers, ~1 day)

| # | Fix | Who | Why |
|---|---|---|---|
| 1 | Raise the **Meta account spend limit** (Billing → Account spending limit) | Owner | Nothing has delivered since 24 Nov. |
| 2 | **Turn off** 11/12 sales, Awareness, Engagement, Catalog and "Mac Comedian" campaigns | Owner / Claude with OK | They spent ~3.85k for 0 sales. |
| 3 | Shopify: Egypt shipping rate → **0 EGP** | Claude (with OK) | Free shipping must match the ad. |
| 4 | Shopify automatic discount: **free tee on orders ≥ 2,990** (Buy X get Y) | Claude (with OK) | Mechanism for the bundle. |
| 5 | Announcement bar: "FREE SHIPPING • 2 hoodies/sweatshirts = FREE TEE"; free-tee progress line in cart | Claude (with OK) | Lifts order value without ad spend. |
| 6 | Turn on **WhatsApp chat** + the hidden **story-reviews** section (once stories are uploaded) | Claude (with OK) | Trust for COD buyers; add-to-cart fell 5.5% → 3.2%. |
| 7 | Pin an Instagram highlight "200 EGP OFF": how the post offer works | Owner | Explains the UGC offer in one tap. |
| 8 | Upload past customers (2H + JEX sheets, ~800 phones) as a **Meta Custom Audience** in Ads Manager | Owner | Cheapest buyers are past buyers. Meta hashes the list; it never goes into our repo. |

---

## 3. Free sales first (0 EGP spend)

WhatsApp is parked for now (owner, 28 Nov).
- **Instagram stories daily:** 1 design close-up, 1 customer repost, 1 offer reminder.
- **Reshare every customer post** that comes in for the 200 EGP offer (social proof, plus content for ads).

## 4. Campaign structure (Meta, 3 campaigns only)

Small budgets die when split thin. So: few ad sets, broad targeting, let the pixel (Purchase EMQ 8/10) do the work.

**Location: all of Egypt** (shipping is free nationwide; Meta finds the buyers, 76% are Cairo). **Age 22-45 as a suggestion.** No international.

### A. SCALE: "Winners" (Advantage+ Sales / ASC), 55% of budget
- Objective Sales → Purchase. One campaign, broad audience. Existing customers capped at 20%.
- **Reuse the winning posts by post ID** (keeps their likes/comments): the 30.6s reel (video 27146229395058380, ~177 purchases across 3 ads, CPA 192) and the 6.6s "Special discounts" reel (CPA 319). Swap the first-frame text and caption to the new offer.
- Add the 2 best new creatives from Campaign B every week.
- **Don't relaunch/duplicate to "reset":** edits and constant relaunches are what wrecked Jun-Oct (CPM 80 → 158).

### B. TEST: "Creative lab" (ABO), 30% of budget
- One ad set, broad Cairo/Giza, Purchase optimisation, **3-4 ads at a time**, one new concept each:
  1. **"Design is the joke":** 9:16 reel, 6-8 designs, each print full-screen and readable for 1.5s, end card "Free shipping • 2 pieces = free tee". (Built from our mockups + artwork; this matches the winning reel's style.)
  2. **"Pick your personality":** carousel of 5 hoodie designs by theme (The Office, Breaking Bad, overthinkers, introverts, sarcasm).
  3. **Bundle maths:** "2 hoodies 3,198 + tee worth 930 = FREE + shipping FREE" static/reel.
  4. **UGC/reviews:** customer story screenshots + real posts (as they arrive from the 200 EGP offer).
- Hook rule: the print must be **large and readable in the first second**; text overlay names the joke, not the product.

### C. RETARGET + PAST BUYERS, 15% of budget
- Audiences: site visitors 30 days, add-to-cart 14 days, IG engagers 60 days, past-customer list. Exclude purchasers 7 days.
- Message: "Still thinking? Free shipping, cash on delivery, 2 pieces = free tee." + reviews creative.

---

## 5. Budget and timeline (10,000 EGP over 21 days)

| Phase | Days | Daily | A Scale | B Test | C Retarget | Gate to move on |
|---|---|---|---|---|---|---|
| 1 Launch | 1-7 | 400 | 220 | 120 | 60 | ≥ 6 purchases, CPA ≤ 450 |
| 2 Optimise | 8-14 | 480 | 300 | 110 | 70 | Blended ROAS ≥ 3 |
| 3 Push (pre-New Year) | 15-21 | 550 | 360 | 100 | 90 | (end of test) |
| **Total** | 21 | | | | | **~10,000** |

If Phase 1 misses its gate: **stop, don't spend more.** Fix the site/offer/creative first. December is the best month (Dec 2025: 30k spend → 179k sales, 5.9x), so timing is on our side.

---

## 6. Rules (no feelings, just numbers)

**Kill an ad when:**
- spent 350 (1 target CPA) with **no add-to-cart**, or
- spent 700 (2x CPA) with **no purchase**, or
- CTR (link) < 0.8% after 3,000 impressions.

**Scale when:**
- an ad set has CPA ≤ 300 for **3 days in a row** → +20% budget, max once every 48h.
- a test creative has CPA ≤ 350 with 2+ purchases → move it into Campaign A (by post ID).

**Never:**
- edit a winning ad (copy it instead), or restart campaigns to "refresh",
- run awareness/engagement for sales,
- advertise tees alone.

**Every morning (5 min):** spend, purchases, CPA, CTR, CPM, add-to-cart rate, and **blended MER = Shopify total sales ÷ Meta spend** (the honest number; Meta over/under-counts COD).

---

## 7. What to expect (honest, recalculated 28 Nov without WhatsApp)

Contribution = margin after item cost, free shipping, free tee share, ~20% of orders using the 200 EGP post discount and 7.5% COD refusals, minus the 10k ad spend.

| Scenario | CPA | Orders from 10k | Avg order | Ad sales | + organic (~3 wks) | Total sales | Contribution after ads |
|---|---|---|---|---|---|---|---|
| Weak | 500 | 20 | 1,800 | 36k | 8k | ~44k | ~+9k |
| Expected | 350 | 28 | 2,000 | 57k | 8k | ~65k | ~+20k |
| Strong (Mar-May 2026 level) | 220 | 45 | 2,100 | 95k | 10k | ~105k | ~+40k |

- Even the weak case pays for itself, because the offer pushes 2-piece orders.
- **500k is not reachable on 10k EGP.** Even at our best-ever 8x it needs ~60-70k of spend.
- The test's job is to **prove a CPA ≤ 350 machine in 3 weeks.** Then scale budget week by week (+20-30%) as long as blended MER stays ≥ 3.

## 7b. What is built (28 Nov 2026)

**Store (live):** automatic discount "FREE SHIPPING (Egypt)" (no minimum); automatic "FREE TEE with 2 hoodies/sweatshirts (2,990+)" (any tee type, customer adds the tee, it drops to 0; tested in cart); announcement bar on every page. Script: `setup_offers.py`. Theme backup: `live-backup/theme-20261128/header-group.json`.

**Meta (drafts, not published, 400 EGP/day total):**
| Campaign | ID | Budget | Ad set | Ads |
|---|---|---|---|---|
| DEC26 / A Scale / Sales / Winter | 120249657970910701 | 190/day (CBO) | Egypt, 21+, age 22-45 as suggestion, Purchase | A1 new reel "Design is the joke" (14s); A2 best-ever video with winter copy |
| DEC26 / B Creative Test / Sales | 120249657971010701 | 150/day (ad set) | same | B1 carousel of 8 best sellers; B2 bundle static (4:5 + 9:16) |
| DEC26 / C Retarget / Sales | 120249657971040701 | 60/day (CBO) | Site visitors / ATC / buyers 120d only | C1 bundle; C2 carousel |

Old campaigns paused: "Mac Comedian" and the "Everyone else is boring" boost. Creative files: built by `build_ad_creatives.py` from the website mockups.

## 8. Division of work

| Claude | Owner |
|---|---|
| Build reels/carousels from mockups + artwork (no AI, no Canva credits) | Raise Meta spend limit, approve campaigns before they go live |
| Shopify: free shipping, free-tee discount, announcement bar (done 28 Nov); reviews section when stories are uploaded | Upload customer list to Meta (optional) |
| Set up campaigns as **paused drafts** in Meta for review | Handle UGC DMs (200 EGP) and reshare posts |
| Daily numbers + kill/scale calls | Post daily stories |
