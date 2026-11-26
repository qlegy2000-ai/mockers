# Mockers catalogue rebuild — QA report

## Result

- Designs processed: **64**
- Products out: **275** (was 64)
- Variants out: **5563**
- Largest product: **42** variants (was 137)
- Duplicate variants merged by normalising colour/size casing: **5**
- Junk handles dropped: **40**
- Non-design handles left alone: **23** (accessories etc.)

## Products per garment

| Garment | Products | Variants |
|---|---|---|
| Oversized Heavy Premium | 61 | 1211 |
| Oversized Light-Soft | 61 | 1211 |
| Hoodie | 54 | 1176 |
| Sweatshirt | 54 | 1106 |
| Regular Fit T-Shirt | 45 | 859 |

## Data fixed automatically

| Field | Before | After |
|---|---|---|
| Size values | 22 (`X-Lagre`, `Smalll`, `2x-Large`, `s`/`S`/`small-1`…) | 6 (`XS S M L XL 2XL`) |
| Colour values | 29 (`black`/`Black`, `white-1`/`White`…) | 15 canonical |
| Style values | 6 (`SWEATSHIRT`, `swestshirt`…) | 5 canonical, now `product_type` |
| Vendor | `Mockers` + `mockers-shop` | `Mockers` |
| SKUs | none on 6,640 variants | every variant |
| Compare-at price | mixed, some **below** price | canonical per garment |
| Inventory | fake `1000` / stale `0` blocking sales | untracked + `continue` (POD) |

## Needs a human eye


### color without image — 88

- palestine / Oversized Heavy Premium: White
- palestine / Oversized Light-Soft: White
- paranoid / Hoodie: Aegean Blue
- paranoid / Sweatshirt: Dark Blue
- paranoid / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green
- mood-swings / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green, White
- lies / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green
- need-weed / Regular Fit T-Shirt: Aegean Blue
- i-love-your-personality / Sweatshirt: Dark Blue
- i-love-your-personality / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green
- pumba / Hoodie: Dark Blue
- pumba / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green, White
- kill-bic / Hoodie: Black, Burgundy
- kill-bic / Sweatshirt: Beige, Black, Iron Grey
- kill-bic / Regular Fit T-Shirt: Black, Burgundy, White
- national-psychotic / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green
- mommy-issues / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green, White
- pros-cons / Hoodie: Aegean Blue, Iron Grey
- pros-cons / Sweatshirt: Dark Blue, Dark Green
- pros-cons / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green
- wish-you-were-beer / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green, White
- stop-wars / Hoodie: Aegean Blue
- stop-wars / Sweatshirt: Dark Blue
- stop-wars / Regular Fit T-Shirt: Aegean Blue, Burgundy, Cashmere Pink, Pistache Green, White
- stranger-shit / Hoodie: Aegean Blue
- …and 63 more

### compare at below price — 382

- must-be-ai / Oversized Heavy Premium / Beetroot Purple / S: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Beetroot Purple / M: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Beetroot Purple / L: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Beetroot Purple / XL: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Beetroot Purple / XS: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Dark Green / S: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Dark Green / M: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Dark Green / L: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Dark Green / XL: price 930.00 vs compare 800.00
- must-be-ai / Oversized Heavy Premium / Dark Green / XS: price 930.00 vs compare 800.00
- led-zep / Hoodie / White / S: price 1450.00 vs compare 550.00
- led-zep / Hoodie / White / M: price 1450.00 vs compare 550.00
- led-zep / Hoodie / White / L: price 1450.00 vs compare 550.00
- led-zep / Hoodie / White / XL: price 1450.00 vs compare 550.00
- led-zep / Hoodie / White / 2XL: price 1450.00 vs compare 550.00
- led-zep / Sweatshirt / White / S: price 1350.00 vs compare 550.00
- led-zep / Sweatshirt / White / M: price 1350.00 vs compare 550.00
- led-zep / Sweatshirt / White / L: price 1350.00 vs compare 550.00
- led-zep / Sweatshirt / White / XL: price 1350.00 vs compare 550.00
- led-zep / Sweatshirt / White / 2XL: price 1350.00 vs compare 550.00
- grumpy-owl / Hoodie / White / 2XL: price 1450.00 vs compare 500.00
- grumpy-owl / Hoodie / Dark Blue / 2XL: price 1450.00 vs compare 500.00
- grumpy-owl / Sweatshirt / White / 2XL: price 1350.00 vs compare 500.00
- grumpy-owl / Sweatshirt / Cashmere Pink / 2XL: price 1350.00 vs compare 500.00
- paranoid / Hoodie / Aegean Blue / 2XL: price 1450.00 vs compare 500.00
- …and 357 more

### variant image wrong color — 72

- middle-fingers / Regular Fit T-Shirt / **White** shows a *Black* mockup -> MiddleFingers_RegularT_Black_1c4afaf5-8b91-4eeb-85b1-19eae72f9dea.png
- middle-fingers / Regular Fit T-Shirt / **Burgundy** shows a *Black* mockup -> MiddleFingers_RegularT_Black_1c4afaf5-8b91-4eeb-85b1-19eae72f9dea.png
- middle-fingers / Regular Fit T-Shirt / **Beetroot Purple** shows a *Black* mockup -> MiddleFingers_RegularT_Black_1c4afaf5-8b91-4eeb-85b1-19eae72f9dea.png
- middle-fingers / Regular Fit T-Shirt / **Dark Green** shows a *Black* mockup -> MiddleFingers_RegularT_Black_1c4afaf5-8b91-4eeb-85b1-19eae72f9dea.png
- middle-fingers / Regular Fit T-Shirt / **Earth Green** shows a *Black* mockup -> MiddleFingers_RegularT_Black_1c4afaf5-8b91-4eeb-85b1-19eae72f9dea.png
- middle-fingers / Regular Fit T-Shirt / **Aegean Blue** shows a *Black* mockup -> MiddleFingers_RegularT_Black_1c4afaf5-8b91-4eeb-85b1-19eae72f9dea.png
- middle-fingers / Oversized Heavy Premium / **Black** shows a *White* mockup -> MiddleFingers_OversizedSoftT_White_8db2dcc3-2ae4-4587-84d8-672b9260cd50.png
- middle-fingers / Oversized Heavy Premium / **Burgundy** shows a *White* mockup -> MiddleFingers_OversizedSoftT_White_8db2dcc3-2ae4-4587-84d8-672b9260cd50.png
- middle-fingers / Oversized Heavy Premium / **Beetroot Purple** shows a *White* mockup -> MiddleFingers_OversizedSoftT_White_8db2dcc3-2ae4-4587-84d8-672b9260cd50.png
- middle-fingers / Oversized Heavy Premium / **Dark Green** shows a *White* mockup -> MiddleFingers_OversizedSoftT_White_8db2dcc3-2ae4-4587-84d8-672b9260cd50.png
- middle-fingers / Oversized Heavy Premium / **Earth Green** shows a *White* mockup -> MiddleFingers_OversizedSoftT_White_8db2dcc3-2ae4-4587-84d8-672b9260cd50.png
- middle-fingers / Oversized Heavy Premium / **Aegean Blue** shows a *White* mockup -> MiddleFingers_OversizedSoftT_White_8db2dcc3-2ae4-4587-84d8-672b9260cd50.png
- middle-fingers / Oversized Light-Soft / **Black** shows a *Burgundy* mockup -> MiddleFingers_OversizedSoftT_Burgundy_568705bd-1765-49ef-a84e-7cd8bfb8fef4.png
- middle-fingers / Oversized Light-Soft / **White** shows a *Burgundy* mockup -> MiddleFingers_OversizedSoftT_Burgundy_568705bd-1765-49ef-a84e-7cd8bfb8fef4.png
- middle-fingers / Oversized Light-Soft / **Beetroot Purple** shows a *Burgundy* mockup -> MiddleFingers_OversizedSoftT_Burgundy_568705bd-1765-49ef-a84e-7cd8bfb8fef4.png
- middle-fingers / Oversized Light-Soft / **Dark Green** shows a *Burgundy* mockup -> MiddleFingers_OversizedSoftT_Burgundy_568705bd-1765-49ef-a84e-7cd8bfb8fef4.png
- middle-fingers / Oversized Light-Soft / **Earth Green** shows a *Burgundy* mockup -> MiddleFingers_OversizedSoftT_Burgundy_568705bd-1765-49ef-a84e-7cd8bfb8fef4.png
- middle-fingers / Oversized Light-Soft / **Aegean Blue** shows a *Burgundy* mockup -> MiddleFingers_OversizedSoftT_Burgundy_568705bd-1765-49ef-a84e-7cd8bfb8fef4.png
- grumpy-owl / Hoodie / **Dark Blue** shows a *Beige* mockup -> beige_hoodie_bdf18cc0-b561-48c3-ba31-ab80cb9f0eee.png
- paranoid / Oversized Heavy Premium / **Royal Dark Green** shows a *Dark Green* mockup -> Paranoid_Oversized_DarkGreen.png
- paranoid / Oversized Light-Soft / **Earth Green** shows a *Dark Green* mockup -> Paranoid_Oversized_DarkGreen.png
- mood-swings / Hoodie / **Dark Blue** shows a *Beige* mockup -> beige_hoodie_6c30f221-80a3-46ee-bd73-13033d718541.png
- lies / Oversized Heavy Premium / **Royal Dark Green** shows a *Dark Green* mockup -> LIES_Oversized_DarkGreen.png
- lies / Oversized Light-Soft / **Earth Green** shows a *Dark Green* mockup -> LIES_Oversized_DarkGreen.png
- i-love-your-personality / Oversized Heavy Premium / **Royal Dark Green** shows a *Dark Green* mockup -> ILoveYourPersonality_Oversized_DarkGreen.png
- …and 47 more

## Junk handles dropped

- `adhdlucky-picks-copy` (2 rows)
- `aggressive-duck-lucky-picks` (1 rows)
- `aggressive-duck-lucky-picks-copy` (1 rows)
- `anti-stalking-lucky-picks` (1 rows)
- `capitalism-lucky-picks-copy` (4 rows)
- `comma-sutra-lucky-picks-copy` (3 rows)
- `comma-sutra-lucky-picks-copy-1` (2 rows)
- `crocs-lucky-picks-copy` (1 rows)
- `dear-music-lucky-picks-copy` (3 rows)
- `diet-joke-lucky-picks-copy` (3 rows)
- `disappointed-but-not-surprised-lucky-picks` (1 rows)
- `disappointed-but-not-surprisedlucky-picks-copy` (1 rows)
- `disappointed-but-not-surprisedlucky-picks-copy-1` (4 rows)
- `dwight-the-office-lucky-picks-copy` (2 rows)
- `dwight-the-office-lucky-picks-copy-1` (2 rows)
- `fail-lucky-picks-copy` (2 rows)
- `forget-ai-lucky-picks-copy` (1 rows)
- `funny-how-lucky-picks-copy` (1 rows)
- `hang-on-lucky-picks` (1 rows)
- `hope-lucky-picks` (1 rows)
- `im-not-judgemental-lucky-picks-copy` (2 rows)
- `im-not-judgmental-lucky-picks` (1 rows)
- `jomo-lucky-picks-copy` (4 rows)
- `kill-bic-lucky-picks` (1 rows)
- `kill-bic-lucky-picks-copy` (4 rows)
- `lies-lucky-picks-copy` (2 rows)
- `millennials-copy` (3 rows)
- `mixed-drinks-lucky-picks-copy` (2 rows)
- `mood-swings-lucky-picks-copy` (1 rows)
- `national-psychotic-lucky-picks` (1 rows)
- `need-weed-lucky-picks` (1 rows)
- `need-weed-lucky-picks-copy` (3 rows)
- `paranoid-lucky-picks-copy` (2 rows)
- `pros-cons-lucky-picks-copy` (6 rows)
- `pumba-lucky-picks-copy` (2 rows)
- `stranger-shit-lucky-picks` (1 rows)
- `therapist-lucky-picks-copy` (2 rows)
- `trust-the-process-lucky-picks-copy` (1 rows)
- `wish-you-were-beer-lucky-picks-copy` (1 rows)
- `word-filter-lucky-picks` (1 rows)
