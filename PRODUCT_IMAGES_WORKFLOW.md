# Product Images — Canva to Live

How garment mockups get from the Canva deck onto mockers.shop, what must never be
uploaded, and where the work stands.

Last updated 30 Oct 2026.

---

## 1. The short version

Mockers shoot garment mockups in a Canva deck. Each slide is one design on one garment
in one colour. Those slides have to end up pinned to the matching colour variant on
Shopify, so that picking a swatch changes the photo.

Three steps, in this order:

1. **Export** the agreed slides from Canva as PNG into a folder.
2. **Verify** the exported files still line up with the deck.
3. **Attach** them with `attach_canva_images.py`.

Step 2 is not optional. Canva page numbers move (see §4).

---

## 2. The deck

**Ultra-Realistic Product Images** — <https://canva.link/g4p3nf8z4c9swka>
(view link: `https://www.canva.com/design/DAHUzYk1siQ/7i5rOzbjxf7GjTV25O1DOw/view`)

123 pages as of 30 Oct 2026. Pages 1–41 are other material — sweatpants ads, design
concepts, bucket hats, care labels. **The garment mockups start at page 42.**

The Canva connector is not authorised for this workspace, so the deck is read through
its public view link. That gives page thumbnails at 400×500 — enough to identify a
design and colour, nowhere near enough to use as a product photo. **Usable images can
only come from a Canva export.** The full-resolution originals are lazy-loaded per
slide and are not reachable from the link.

---

## 3. What must never be uploaded

The deck is not self-validating. It contains mockups of colourways that do not exist in
the catalogue, and the same colourway shot twice. Uploading those creates products that
look buyable in a colour nobody can order.

| Rule | Why |
|---|---|
| **No white sweatshirts** | The sweatshirt range is Black, Offwhite, Dark Green, Dark Blue, Beetroot Purple. There is no white blank. |
| **No pale colour on a white-ink design** | White artwork disappears on cream. Twelve designs are affected — see `WHITE_ARTWORK` in `optimize_catalog.py`. |
| **No duplicate colourways** | Two shots of the same product and colour; only one is needed. |

Rejected so far:

| Slide | Deck | What it was |
|---|---|---|
| 52, 53 | v1 | duplicates of 44 and 49 |
| 60 | v1 | palestine sweatshirt, Offwhite — white caption vanishes on cream |
| 86, 93, 102, 118, 122 | v2 | shot on a **white** sweatshirt |

The map CSV is the gate: anything not listed as `EXPORT` is skipped by name, and the
script reports it rather than guessing.

**Cream vs white is the trap.** At thumbnail size they look the same. Separate them by
warmth — red channel minus blue:

* Offwhite blank: **+14 to +37**
* True white: **about 0**

---

## 4. Canva page numbers are not stable

On 28 Oct 2026 the deck went from 80 to 123 pages and a page inserted near the front
**shifted every mockup by +1** — what was slide 41 became 42.

A batch exported before that date needs the v1 map; after it, v2. Using the wrong one
puts the right photo on the wrong product. That is why `--map` is a required argument
with no default, and why old export folders live under `canva-exports-archive/` where
they cannot be re-run against a newer map by accident.

**Re-anchor on content, never on arithmetic.** Compare the exported files against
freshly downloaded page thumbnails and find the offset that scores best. Two cautions
learned the hard way:

* A coarse grayscale signature matches on **pose and background**. Two different designs
  shot on the same model score ~0.95 and look like a match. Only **0.99+** means the
  same image.
* A genuine **reshoot** of the same product and colour scores *lower* (~0.8) than a
  false positive. Neither a high nor a low score settles it on its own — confirm by eye.

---

## 5. Running a batch

```bash
cd "/Users/mackbook/Mockers website"
set -a; . <scratchpad>/.live_env; set +a      # SHOP + TOKEN

# 1. dry run — resolves every product and colour, uploads nothing
python3 attach_canva_images.py \
    --dir canva-exports-v2 \
    --map reports/canva_export_list_v2.csv

# 2. for real
python3 attach_canva_images.py \
    --dir canva-exports-v2 \
    --map reports/canva_export_list_v2.csv --run
```

The script takes the slide number from the **last number in the filename**, so Canva's
own export names work unchanged. For each image it uploads via `stagedUploadsCreate`,
creates the media, **waits for `status: READY`**, then pins it to every variant of that
colour with `productVariantAppendMedia`.

Waiting for READY matters: pinning media that is still processing is what left variant
images empty during the original catalogue migration.

### Always verify against live, not the log

A background run reported `ATTACHED 36 errors=1` — one image hit a transient
`HTTP 520` mid-upload. The log named the product but not the colour. Querying live
found the single gap (`uncle-wes` / Beetroot Purple, slide 109); re-running the script
against a folder holding only that file fixed it.

Re-running a whole folder would duplicate everything that already succeeded, so **retry
only the missing files**.

---

## 6. Image sizes

No resizing needed. Exports run **3.1–5.7 MP** and **1.8–6.1 MB**, against Shopify's
limits of 20 MP and 20 MB per file. They sit inside the range the store already uses
(1024×1024 up to 3375×3375).

Shopify generates its own smaller renditions on upload and the theme requests those, so
a shopper never downloads the original and page speed is unaffected. Keeping the
original large is what makes zoom look sharp.

One wrinkle: `i-choose-violance-sweatshirt` now mixes aspect ratios — older images at
1215×1215 and 912×1172, new ones at 2380×2380. Every other product is internally
consistent. If that gallery looks jumpy, drop the five older unlinked photos; the four
new ones already cover every colour it sells.

---

## 7. Where it stands

**74 images attached across two batches** — 37 on 21 Oct, 37 on 28 Oct.

For the **16 designs that gained their first winter product**:

| | |
|---|---|
| Images live | **70 of 156** |
| Variants showing their own colour | 420 |
| Remaining | 86 — **75 hoodie**, 11 sweatshirt |

Plus `i-choose-violance-sweatshirt`, which is not one of the 16 and went from nothing to
all four of its colours.

### Sweatshirts — 11 left

| Design | Missing |
|---|---|
| telefreak | **all 5** — only ever shot in white |
| must-be-ai, old-people, shit, stoned | Offwhite |
| middle-fingers | Beetroot Purple |
| rolex | Dark Green |

Six shots finish every sweatshirt except telefreak.

### Hoodies — the whole remaining job

75 of the 86 outstanding. Only `middle-fingers` has any, and it is still short Purple
and Aegean Blue.

**Nothing can be reused between the two garments.** The hoodie range is Black, Offwhite,
Purple, Aegean Blue, Iron Grey; the sweatshirt range is Black, Offwhite, Dark Green,
Dark Blue, Beetroot Purple. They overlap on Black and Offwhite only, and those are
different blanks photographed differently.

### Catalogue-wide

| | |
|---|---|
| Active apparel products | 390 |
| Colourways on sale | 1,857 |
| With a photo | 1,037 |
| Still needing one | **820** |

By garment, shot of total colourways: Regular Fit T-Shirt 10/419, Oversized Light-Soft
277/340, Oversized Heavy Premium 242/342, Sweatshirt 286/378, Hoodie 222/378.

The Regular Fit T-Shirt is barely photographed at all and is the largest single gap in
the catalogue.

---

## 8. Files

| Path | What it is |
|---|---|
| `attach_canva_images.py` | Uploads exports and pins them to the right colour. Requires `--dir` and `--map`. |
| `reports/canva_export_list.csv` | **v1 map** — pre-28 Oct deck numbering. |
| `reports/canva_export_list_v2.csv` | **v2 map** — current deck numbering. |
| `reports/canva_winter_progress.csv` | Every winter image for the 16 designs, live or not. |
| `reports/missing_product_images.csv` | Catalogue-wide shoot list, grouped by how much work each needs. |
| `canva-exports-v2/` | Current batch of exports. |
| `canva-exports-archive/` | Previous batches, kept out of reach of newer maps. |

Colour rules live in `optimize_catalog.py`: `GARMENT_RANGE`, `WHITE_ARTWORK`,
`garment_colours()`. The script reads them, so the rules are enforced in one place.

---

## 9. Starting the next batch

1. Pull the deck's current page count and thumbnails from the view link.
2. Identify each new mockup's design and colour; check warmth on anything pale.
3. Drop anything that breaks a rule in §3.
4. Write a new map CSV — **in the deck's current numbering** — and bump the version.
5. Ask for exactly those pages as PNG.
6. Verify alignment (§4), dry run, then run.
7. Check live and retry only what is missing.
