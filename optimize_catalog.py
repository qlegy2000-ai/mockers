#!/usr/bin/env python3
"""
Mockers catalog optimizer
=========================
Turns the current "1 design = 1 product with Style/Color/Size variants" export
into the Threadless-style model: product = design x garment, variants = color x size.

Input : products_export_1 (20).csv   (Shopify product export)
Output: catalog-build/*.csv|md       (Shopify-importable + ops files)
"""
import csv, re, os, sys, json, collections

SRC = "products_export_1 (20).csv"
OUT = "catalog-build"

# ---------------------------------------------------------------- normalization
STYLE_MAP = {
    "hoodie": "Hoodie",
    "sweatshirt": "Sweatshirt", "swestshirt": "Sweatshirt",
    "regular fit t-shirt": "Regular Fit T-Shirt",
    "oversized heavy premium": "Oversized Heavy Premium",
    "oversized light-soft": "Oversized Light-Soft",
}
STYLE_ABBR = {
    "Hoodie": "HOD", "Sweatshirt": "SWT", "Regular Fit T-Shirt": "RFT",
    "Oversized Heavy Premium": "OHP", "Oversized Light-Soft": "OLS",
}
# garment family -> drives seasonal collections & discounts
STYLE_FAMILY = {
    "Hoodie": "winter", "Sweatshirt": "winter",
    "Regular Fit T-Shirt": "summer",
    "Oversized Heavy Premium": "summer", "Oversized Light-Soft": "summer",
}

SIZE_MAP = {
    "xs": "XS", "x-small": "XS", "extra small": "XS",
    "s": "S", "small": "S", "small-1": "S", "smalll": "S",
    "m": "M", "medium": "M", "medium-1": "M",
    "l": "L", "large": "L", "large-1": "L",
    "xl": "XL", "x-large": "XL", "x- large": "XL", "x-lagre": "XL", "xlarge": "XL",
    "2xl": "2XL", "2x-large": "2XL", "2-x-large": "2XL", "xxl": "2XL", "2x large": "2XL",
}
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]

COLOR_MAP = {
    "white": "White", "white-1": "White",
    # live spells the cream garment both ways; canonical form follows live's dominant
    # spelling (34 products vs 6). It is a separate colour from White.
    "offwhite": "Offwhite", "off-white": "Offwhite", "off white": "Offwhite",
    "black": "Black", "black-1": "Black",
    "burgundy": "Burgundy",
    "dark green": "Dark Green", "dark-green": "Dark Green", "dark-green-1": "Dark Green",
    "aegean blue": "Aegean Blue", "aegean-blue": "Aegean Blue",
    "dark blue": "Dark Blue", "dark-blue": "Dark Blue",
    "pink": "Pink", "pink-1": "Pink",
    "cashmere pink": "Cashmere Pink", "cashmere-pink": "Cashmere Pink",
    "iron grey": "Iron Grey", "iron-grey": "Iron Grey",
    "grey": "Iron Grey", "gray": "Iron Grey",
    "pistache green": "Pistache Green", "pistache-green": "Pistache Green",
    "earth green": "Earth Green", "earth-green": "Earth Green",
    "royal dark green": "Royal Dark Green", "royal-dark-green": "Royal Dark Green",
    "beetroot purple": "Beetroot Purple", "beetroot-purple": "Beetroot Purple",
    # Purple and Beetroot Purple are DIFFERENT garments: 51 live products carry both
    # as separate colour options. Collapsing them cost 48 designs a real colourway.
    "purple": "Purple",
    "beige": "Beige", "beige cafe": "Beige Cafe", "beige-cafe": "Beige Cafe",
    "yellow": "Yellow", "red": "Red", "blue": "Blue", "green": "Green",
}
COLOR_ABBR = {
    "White": "WHT", "Black": "BLK", "Burgundy": "BRG", "Dark Green": "DGN",
    "Aegean Blue": "AEG", "Dark Blue": "DBL", "Pink": "PNK", "Cashmere Pink": "CPK",
    "Iron Grey": "IGY", "Pistache Green": "PGN", "Earth Green": "EGN",
    "Royal Dark Green": "RDG", "Beetroot Purple": "BPR", "Purple": "PUR", "Offwhite": "OFW", "Beige": "BEI",
    "Beige Cafe": "BCF", "Yellow": "YEL", "Red": "RED", "Blue": "BLU", "Green": "GRN",
}
# canonical hex, for theme colour swatches
# Single source of truth for swatch hex. These values must match
# theme-working/assets/mk-swatches.css - that file is what the storefront renders,
# so when the two disagree the CSS is right and this map is stale. Five of these
# were measured off the real garment photos in Sept 2026 and only the CSS was
# updated at the time; they are corrected here.
COLOR_HEX = {
    "White": "#FFFFFF", "Black": "#111111", "Burgundy": "#6B1F2B", "Dark Green": "#2e422b",
    "Aegean Blue": "#1c4054", "Dark Blue": "#1b2533", "Pink": "#E8A0B4", "Cashmere Pink": "#D9A7A0",
    "Iron Grey": "#302e2e", "Pistache Green": "#9CBF8A", "Earth Green": "#4A5D3A",
    "Royal Dark Green": "#14452F", "Beetroot Purple": "#46131c", "Beige": "#D9CBB3",
    "Beige Cafe": "#C2A98B", "Yellow": "#E8C547", "Red": "#B3261E", "Blue": "#2B4C9B", "Green": "#3A7D44",
    "Purple": "#4e2c49", "Offwhite": "#eee3cc",
}

# canonical price book (price, compare_at) in EGP, taken from the dominant values in the export
PRICE_BOOK = {
    "Hoodie":                  ("1599.00", None),
    "Sweatshirt":              ("1499.00", None),
    "Regular Fit T-Shirt":     ("679.00",  "800.00"),
    "Oversized Heavy Premium": ("930.00",  "1100.00"),
    "Oversized Light-Soft":    ("778.00",  "1100.00"),
}
GRAMS = {"Hoodie": 700, "Sweatshirt": 600, "Regular Fit T-Shirt": 200,
         "Oversized Heavy Premium": 300, "Oversized Light-Soft": 250}

JUNK_RE = re.compile(r"(lucky-picks|-copy\d*$|-copy-)", re.I)

# filename tokens that betray which colour a mockup actually shows
COLOR_TOKENS = {
    "Black": ["black"], "White": ["white"], "Burgundy": ["burgundy", "maroon"],
    "Dark Green": ["darkgreen", "dark_green", "dark-green"],
    "Aegean Blue": ["aegean"], "Dark Blue": ["darkblue", "dark_blue", "dark-blue", "navy"],
    "Pink": ["pink"], "Cashmere Pink": ["cashmere"], "Iron Grey": ["irongrey", "iron_grey", "iron-grey", "grey", "gray"],
    "Pistache Green": ["pistache"], "Earth Green": ["earth"], "Royal Dark Green": ["royal"],
    "Beetroot Purple": ["beetroot", "purple"], "Beige": ["beige"], "Beige Cafe": ["beigecafe", "beige_cafe"],
}
def image_color_conflict(color, url):
    """Return the colour the FILENAME claims, when it clearly contradicts `color`."""
    if not url:
        return None
    name = re.sub(r"[^a-z]+", "", url.rsplit("/", 1)[-1].split("?")[0].lower())
    mine = [t for t in COLOR_TOKENS.get(color, []) if re.sub(r"[^a-z]+", "", t) in name]
    if mine:
        return None
    for other, toks in COLOR_TOKENS.items():
        if other == color:
            continue
        for t in toks:
            if re.sub(r"[^a-z]+", "", t) in name:
                # 'pink' is a substring trap for 'cashmere pink'; require a clean call
                if color == "Cashmere Pink" and other == "Pink":
                    continue
                if color == "Pink" and other == "Cashmere Pink":
                    continue
                return other
    return None

def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

def norm_style(v):
    return STYLE_MAP.get((v or "").strip().lower().rstrip("-1").strip())

def norm_size(v):
    v = (v or "").strip().lower()
    v = re.sub(r"-1$", "", v)
    return SIZE_MAP.get(v) or SIZE_MAP.get(v.replace(" ", ""))

# Purple and Aegean Blue are different blanks on a hoodie than on a tee, so the
# swatch cannot be keyed on colour name alone. assets/mk-swatches.css carries the
# hoodie overrides, scoped by the data-mk-style attribute that product-option.liquid
# writes. Keep these two in step with that file.
GARMENT_HEX = {
    ("Hoodie", "Purple"):      "#2a1b3d",
    ("Hoodie", "Aegean Blue"): "#11334f",
}

SUMMER_STYLES = {"Regular Fit T-Shirt", "Oversized Light-Soft", "Oversized Heavy Premium"}

# The full range each winter garment is actually made in. Anything outside this
# cannot be fulfilled; anything inside it should be offered on every design.
WINTER_RANGE = {
    "Hoodie":     ["Black", "Offwhite", "Purple", "Aegean Blue", "Iron Grey"],
    "Sweatshirt": ["Black", "Offwhite", "Dark Green", "Dark Blue", "Beetroot Purple"],
}

# Offwhite (#eee3cc) is a cream garment: a design printed in white ink vanishes on
# it. These designs are therefore sold in the other four winter colours only. The
# rule is per DESIGN - it covers that design's hoodie and its sweatshirt alike.
#
# Membership was decided from the real Offwhite mockups, not from the design tile,
# because the tile is misleading twice over:
#   * white inside a dark printed shape is a KNOCKOUT and reads on any garment
#     (wish-you-were-beer is white text in a black badge and prints fine);
#   * Mockers re-colour artwork per garment, so breaking-sad, capitalism,
#     i-love-your-personality and see-right-through-you look like white text on
#     their dark tile but ship in green/teal on cream.
# A design belongs here only when white ink sits directly on the garment with no
# coloured version in evidence.
WHITE_ARTWORK = {
    "andy", "dear-music", "if-only", "illegal", "kill-bic", "millennials",
    "national-psychotic", "paranoid", "pros-cons", "trans-parent",
    # assessed when they gained their first winter product: palestine has a white
    # caption and a white flag band, personality-disorder a white "EXTROVERTED"
    "palestine", "personality-disorder",
}

# The summer ranges were never standardised the way winter's were - each tee carried
# whatever its old listing happened to have, down to colours used on a single product.
# Agreed 16 Oct 2026: take the colours the clear majority already use and drop the
# strays. Existing products keep their colours; this governs anything built from here.
SUMMER_RANGE = {
    "Regular Fit T-Shirt":     ["Black", "White", "Burgundy", "Cashmere Pink",
                                "Aegean Blue", "Pistache Green"],
    "Oversized Light-Soft":    ["Black", "White", "Burgundy", "Pink", "Earth Green"],
    "Oversized Heavy Premium": ["Black", "White", "Burgundy", "Pink", "Royal Dark Green"],
}
GARMENT_RANGE = {**WINTER_RANGE, **SUMMER_RANGE}

# Sizes follow each garment's own majority rather than one rule for all - the blanks
# genuinely differ. Winter is the only range that runs XS through 2XL.
GARMENT_SIZES = {
    "Hoodie":                  ["XS", "S", "M", "L", "XL", "2XL"],
    "Sweatshirt":              ["XS", "S", "M", "L", "XL", "2XL"],
    "Regular Fit T-Shirt":     ["S", "M", "L", "XL"],
    "Oversized Light-Soft":    ["S", "M", "L", "XL", "2XL"],
    "Oversized Heavy Premium": ["XS", "S", "M", "L", "XL"],
}

# The colour a white-ink design cannot be printed on, per garment. Winter's cream
# Offwhite and summer's pure White fail the same way, so WHITE_ARTWORK governs both.
# Corroborated by the catalogue itself: 9 of the 12 white-artwork designs have never
# been sold as a White tee.
PALE = {"Hoodie": "Offwhite", "Sweatshirt": "Offwhite",
        "Regular Fit T-Shirt": "White", "Oversized Light-Soft": "White",
        "Oversized Heavy Premium": "White"}

def garment_colours(design_id, style):
    """The colours a design should be offered in for this garment. [] if unknown."""
    rng = GARMENT_RANGE.get(style)
    if not rng:
        return []
    if design_id in WHITE_ARTWORK:
        return [c for c in rng if c != PALE[style]]
    return rng

def winter_colours(design_id, style):
    """Winter-only view of garment_colours. [] for summer garments."""
    if style not in WINTER_RANGE:
        return []
    return garment_colours(design_id, style)

def colour_for_style(colour, style):
    """Offwhite is a winter-only garment colour.

    The three summer garments are only made in White - they never came in Offwhite,
    whatever the source data says. Hoodie and Sweatshirt keep Offwhite.
    Apply this AFTER norm_color, on every (colour, style) pair.
    """
    if colour == "Offwhite" and style in SUMMER_STYLES:
        return "White"
    return colour

def norm_color(v):
    v = (v or "").strip().lower()
    v = re.sub(r"-1$", "", v).replace("_", " ")
    return COLOR_MAP.get(v) or COLOR_MAP.get(v.replace("-", " ")) or (v.title() if v else None)

# ---------------------------------------------------------------- load
def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault(r["Handle"], []).append(r)
    return groups

def main():
    if not os.path.exists(SRC):
        sys.exit(f"missing {SRC}")
    os.makedirs(OUT, exist_ok=True)
    groups = load(SRC)
    head = {h: g[0] for h, g in groups.items()}

    designs, skipped_junk, skipped_other = [], [], []
    for h, g in groups.items():
        if JUNK_RE.search(h):
            skipped_junk.append(h); continue
        if head[h].get("Type") != "Design":
            skipped_other.append(h); continue
        designs.append(h)

    issues = collections.defaultdict(list)
    new_products = []          # list of dicts describing each design x style product
    redirects = []
    blanks = set()

    for h in designs:
        g = groups[h]
        hd = head[h]
        title = (hd["Title"] or h).strip()
        body  = hd["Body (HTML)"] or ""
        # gallery images shared by the whole design (position-ordered)
        gallery = [(int(r["Image Position"]), r["Image Src"], r["Image Alt Text"])
                   for r in g if r["Image Src"] and r["Image Position"]]
        gallery.sort()
        hero = gallery[0][1] if gallery else ""

        # bucket variants by normalized style
        by_style = collections.OrderedDict()
        raw_counts = {}
        for r in g:
            if not r.get("Variant Price"):
                continue
            st = norm_style(r["Option1 Value"])
            co = norm_color(r["Option2 Value"])
            sz = norm_size(r["Option3 Value"])
            if not st:
                issues["unknown_style"].append(f"{h}: {r['Option1 Value']!r}"); continue
            if not sz:
                issues["unknown_size"].append(f"{h}: {r['Option3 Value']!r}"); continue
            if not co:
                issues["unknown_color"].append(f"{h}: {r['Option2 Value']!r}"); continue
            # flag the compare-at bug before we overwrite it
            try:
                if r["Variant Compare At Price"] and float(r["Variant Compare At Price"]) < float(r["Variant Price"]):
                    issues["compare_at_below_price"].append(
                        f"{h} / {st} / {co} / {sz}: price {r['Variant Price']} vs compare {r['Variant Compare At Price']}")
            except ValueError:
                pass
            by_style.setdefault(st, {})[(co, sz)] = r
            raw_counts[st] = raw_counts.get(st, 0) + 1

        for st, vmap in by_style.items():
            colors = sorted({c for c, _ in vmap})
            sizes  = sorted({s for _, s in vmap}, key=lambda z: SIZE_ORDER.index(z) if z in SIZE_ORDER else 99)
            # variant image per colour (first non-empty wins)
            vimg = {}
            for (c, s), r in vmap.items():
                if r["Variant Image"] and c not in vimg:
                    vimg[c] = r["Variant Image"]
            missing = [c for c in colors if c not in vimg]
            if missing:
                issues["color_without_image"].append(f"{h} / {st}: {', '.join(missing)}")
            for c, url in vimg.items():
                clash = image_color_conflict(c, url)
                if clash:
                    issues["variant_image_wrong_color"].append(
                        f"{h} / {st} / **{c}** shows a *{clash}* mockup -> {url.rsplit('/',1)[-1].split('?')[0]}")

            price, compare = PRICE_BOOK[st]
            fam = STYLE_FAMILY[st]
            nh = f"{h}-{slug(st)}"
            tags = sorted({
                "design:" + h, "style:" + slug(st), "season:" + fam,
                title.lower(), st.lower(),
                *[f"color:{slug(c)}" for c in colors],
            })
            for c in colors:
                for s in sizes:
                    blanks.add((st, c, s))

            new_products.append(dict(
                handle=nh, title=f"{title} {st}", body=body, design_id=h, design_title=title,
                style=st, family=fam, colors=colors, sizes=sizes, vmap=vmap, vimg=vimg,
                raw=[0]*raw_counts.get(st, len(vmap)),
                price=price, compare=compare, tags=tags, hero=hero, gallery=gallery,
                seo_title=f"{title} {st} | Mockers",
                seo_desc=f"{title} printed on a {st.lower()}. Sarcastic apparel by Mockers, made in Egypt. Available in {len(colors)} colours, sizes {sizes[0]}–{sizes[-1]}.",
            ))
        redirects.append((f"/products/{h}", f"/products/{h}-{slug(sorted(by_style, key=lambda s: -len(by_style[s]))[0])}"))

    write_products(new_products)
    write_redirects(redirects)
    write_blanks(blanks)
    write_collections(new_products)
    write_swatches(new_products)
    write_design_groups(new_products)
    write_report(new_products, designs, skipped_junk, skipped_other, issues, groups)
    print(f"designs in: {len(designs)}   products out: {len(new_products)}   "
          f"variants out: {sum(len(p['vmap']) for p in new_products)}")

# ---------------------------------------------------------------- writers
COLS = ["Handle","Title","Body (HTML)","Vendor","Product Category","Type","Tags","Published",
        "Option1 Name","Option1 Value","Option2 Name","Option2 Value","Option3 Name","Option3 Value",
        "Variant SKU","Variant Grams","Variant Inventory Tracker","Variant Inventory Qty",
        "Variant Inventory Policy","Variant Fulfillment Service","Variant Price",
        "Variant Compare At Price","Variant Requires Shipping","Variant Taxable","Variant Barcode",
        "Image Src","Image Position","Image Alt Text","Gift Card","SEO Title","SEO Description",
        "Variant Image","Variant Weight Unit","Variant Tax Code","Cost per item","Status",
        "Metafield: custom.design_id [single_line_text_field]",
        "Metafield: custom.design_title [single_line_text_field]",
        "Metafield: custom.style [single_line_text_field]",
        "Metafield: custom.season [single_line_text_field]",
        "Metafield: custom.blank_sku [single_line_text_field]"]

def write_products(prods):
    path = os.path.join(OUT, "shopify_import_products.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader()
        for p in prods:
            first = True
            img_pos = 0
            # product images = one per colour, in colour order (so the gallery matches the swatches)
            pimgs = [p["vimg"][c] for c in p["colors"] if c in p["vimg"]]
            if p["hero"] and p["hero"] not in pimgs:
                pimgs.insert(0, p["hero"])
            for c in p["colors"]:
                for s in p["sizes"]:
                    if (c, s) not in p["vmap"]:
                        continue
                    blank = f"{STYLE_ABBR[p['style']]}-{COLOR_ABBR.get(c, slug(c)[:3].upper())}-{s}"
                    row = {k: "" for k in COLS}
                    row.update({
                        "Handle": p["handle"],
                        "Option1 Name": "Color", "Option1 Value": c,
                        "Option2 Name": "Size",  "Option2 Value": s,
                        "Variant SKU": f"MK-{STYLE_ABBR[p['style']]}-{slug(p['design_id'])[:14].upper()}-{COLOR_ABBR.get(c, slug(c)[:3].upper())}-{s}",
                        "Variant Grams": GRAMS[p["style"]],
                        "Variant Inventory Tracker": "",            # POD: do not block the sale
                        "Variant Inventory Qty": "",
                        "Variant Inventory Policy": "continue",
                        "Variant Fulfillment Service": "manual",
                        "Variant Price": p["price"],
                        "Variant Compare At Price": p["compare"],
                        "Variant Requires Shipping": "TRUE",
                        "Variant Taxable": "TRUE",
                        "Variant Weight Unit": "g",
                        "Variant Image": p["vimg"].get(c, ""),
                        "Metafield: custom.blank_sku [single_line_text_field]": blank,
                    })
                    if first:
                        img_pos += 1
                        row.update({
                            "Title": p["title"], "Body (HTML)": p["body"], "Vendor": "Mockers",
                            "Product Category": "Apparel & Accessories > Clothing",
                            "Type": p["style"], "Tags": ", ".join(p["tags"]), "Published": "TRUE",
                            "Gift Card": "FALSE", "Status": "active",
                            "SEO Title": p["seo_title"], "SEO Description": p["seo_desc"],
                            "Image Src": pimgs[0] if pimgs else "", "Image Position": 1,
                            "Image Alt Text": f"{p['design_title']} {p['style']}",
                            "Metafield: custom.design_id [single_line_text_field]": p["design_id"],
                            "Metafield: custom.design_title [single_line_text_field]": p["design_title"],
                            "Metafield: custom.style [single_line_text_field]": p["style"],
                            "Metafield: custom.season [single_line_text_field]": p["family"],
                        })
                        first = False
                    w.writerow(row)
            # remaining gallery images as image-only rows
            for src in pimgs[1:]:
                img_pos += 1
                row = {k: "" for k in COLS}
                row.update({"Handle": p["handle"], "Image Src": src, "Image Position": img_pos,
                            "Image Alt Text": f"{p['design_title']} {p['style']}"})
                w.writerow(row)
    print("wrote", path)

def write_redirects(redirects):
    path = os.path.join(OUT, "url_redirects.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["Redirect from", "Redirect to"])
        w.writerows(sorted(set(redirects)))
    print("wrote", path)

def write_blanks(blanks):
    path = os.path.join(OUT, "blanks_inventory_master.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Blank SKU", "Garment", "Color", "Size", "On hand", "Reorder point", "Supplier", "Cost"])
        for st, c, s in sorted(blanks):
            w.writerow([f"{STYLE_ABBR[st]}-{COLOR_ABBR.get(c, slug(c)[:3].upper())}-{s}", st, c, s, "", "", "", ""])
    print("wrote", path, f"({len(blanks)} blank SKUs)")

def write_collections(prods):
    styles = sorted({p["style"] for p in prods})
    path = os.path.join(OUT, "collections_plan.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Automated collections (Shopify: Products > Collections > Automated)\n\n")
        fh.write("Every one of these is self-maintaining: new designs join automatically.\n\n")
        fh.write("## Garment collections — one per style\n\n")
        fh.write("| Collection | Handle | Condition | Products |\n|---|---|---|---|\n")
        for s in styles:
            n = sum(1 for p in prods if p["style"] == s)
            fh.write(f"| {s} | `{slug(s)}` | Product type **is equal to** `{s}` | {n} |\n")
        fh.write("\n## Season collections — these are what you discount\n\n")
        fh.write("| Collection | Handle | Condition | Products |\n|---|---|---|---|\n")
        for fam in ("winter", "summer"):
            members = [s for s in styles if STYLE_FAMILY[s] == fam]
            n = sum(1 for p in prods if p["family"] == fam)
            cond = " OR ".join(f"Product type = `{m}`" for m in members)
            fh.write(f"| {fam.title()} Collection | `{fam}-collection` | {cond} (match **any**) | {n} |\n")
        fh.write("\n> Set the condition matcher to **any** for season collections, **all** for garment collections.\n")
        fh.write("\n## Winter sale, the native way\n\n")
        fh.write("1. Discounts > Create discount > **Amount off products** > Automatic\n")
        fh.write("2. Applies to: **Specific collections** > `Winter Collection`\n")
        fh.write("3. Value: e.g. 25% off. Set start/end dates. Save.\n\n")
        fh.write("That is the whole job. It covers every hoodie and sweatshirt across every design, "
                 "including designs you add next week, and it touches no t-shirt.\n")
    print("wrote", path)

def write_swatches(prods):
    colors = sorted({c for p in prods for c in p["colors"]})
    path = os.path.join(OUT, "color_swatches.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["Color", "Handle", "Hex", "Used by products"])
        for c in colors:
            n = sum(1 for p in prods if c in p["colors"])
            w.writerow([c, slug(c), COLOR_HEX.get(c, ""), n])
    print("wrote", path, f"({len(colors)} colours)")

STYLE_SORT = ["Regular Fit T-Shirt", "Oversized Light-Soft", "Oversized Heavy Premium",
              "Sweatshirt", "Hoodie"]

def write_design_groups(prods):
    """design -> its garment products, in price order. Feeds the PDP style switcher
    (metafield custom.sibling_styles, type list.product_reference) and the old-URL redirects."""
    by = collections.defaultdict(list)
    for p in prods:
        by[p["design_id"]].append(p)
    path = os.path.join(OUT, "design_groups.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Design ID", "Design title", "Style", "Product handle", "Price", "Position"])
        for d, items in sorted(by.items()):
            items.sort(key=lambda x: STYLE_SORT.index(x["style"]) if x["style"] in STYLE_SORT else 99)
            for i, p in enumerate(items, 1):
                w.writerow([d, p["design_title"], p["style"], p["handle"], p["price"], i])
    # json form, ready to POST as metafields once the API key lands
    jpath = os.path.join(OUT, "design_groups.json")
    json.dump({d: [{"handle": p["handle"], "style": p["style"], "price": p["price"]}
                   for p in sorted(items, key=lambda x: STYLE_SORT.index(x["style"]) if x["style"] in STYLE_SORT else 99)]
               for d, items in by.items()}, open(jpath, "w"), indent=2)
    print("wrote", path, f"({len(by)} design groups)")
    print("wrote", jpath)

def write_report(prods, designs, junk, other, issues, groups):
    path = os.path.join(OUT, "QA_REPORT.md")
    tot_v = sum(len(p["vmap"]) for p in prods)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Mockers catalogue rebuild — QA report\n\n## Result\n\n")
        fh.write(f"- Designs processed: **{len(designs)}**\n")
        fh.write(f"- Products out: **{len(prods)}** (was {len(designs)})\n")
        fh.write(f"- Variants out: **{tot_v}**\n")
        fh.write(f"- Largest product: **{max(len(p['vmap']) for p in prods)}** variants (was 137)\n")
        fh.write(f"- Duplicate variants merged by normalising colour/size casing: **{sum(len(p['raw'])-len(p['vmap']) for p in prods)}**\n")
        fh.write(f"- Junk handles dropped: **{len(junk)}**\n")
        fh.write(f"- Non-design handles left alone: **{len(other)}** (accessories etc.)\n\n")
        fh.write("## Products per garment\n\n| Garment | Products | Variants |\n|---|---|---|\n")
        by = collections.Counter(p["style"] for p in prods)
        bv = collections.Counter()
        for p in prods: bv[p["style"]] += len(p["vmap"])
        for s, n in by.most_common(): fh.write(f"| {s} | {n} | {bv[s]} |\n")
        fh.write("\n## Data fixed automatically\n\n")
        fh.write("| Field | Before | After |\n|---|---|---|\n")
        fh.write("| Size values | 22 (`X-Lagre`, `Smalll`, `2x-Large`, `s`/`S`/`small-1`…) | 6 (`XS S M L XL 2XL`) |\n")
        fh.write("| Colour values | 29 (`black`/`Black`, `white-1`/`White`…) | %d canonical |\n" % len({c for p in prods for c in p["colors"]}))
        fh.write("| Style values | 6 (`SWEATSHIRT`, `swestshirt`…) | 5 canonical, now `product_type` |\n")
        fh.write("| Vendor | `Mockers` + `mockers-shop` | `Mockers` |\n")
        fh.write("| SKUs | none on 6,640 variants | every variant |\n")
        fh.write("| Compare-at price | mixed, some **below** price | canonical per garment |\n")
        fh.write("| Inventory | fake `1000` / stale `0` blocking sales | untracked + `continue` (POD) |\n")
        fh.write("\n## Needs a human eye\n\n")
        if not issues: fh.write("_Nothing flagged._\n")
        for k, v in sorted(issues.items()):
            fh.write(f"\n### {k.replace('_',' ')} — {len(v)}\n\n")
            for line in v[:25]: fh.write(f"- {line}\n")
            if len(v) > 25: fh.write(f"- …and {len(v)-25} more\n")
        fh.write("\n## Junk handles dropped\n\n")
        for h in sorted(junk): fh.write(f"- `{h}` ({len(groups[h])} rows)\n")
    print("wrote", path)

if __name__ == "__main__":
    main()
