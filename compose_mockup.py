#!/usr/bin/env python3
"""
Place an exact Canva-rendered artwork (transparent PNG) on a blank garment model.

Print size and chest position follow the owner's approved pilot (Breaking Sad):
print width = 13.55% of the model photo height, centred on the chest anchor of each
model. Tall prints are capped so their height never exceeds 1.25x that width.
Models and anchors are measured from the owner's own Canva pages.
"""
import json, os, sys
from PIL import Image

# per model: canvas size, background colour, anchor (centre x, print top y) and photo height, all in px
MODELS = {
  # sweatshirts: 2380x2380 deck pages, studio backdrop already in the blank export
  ("Sweatshirt", "BeetrootPurple"): dict(file="sw_BeetrootPurple.png", cx=1215, top=1025, H=2380),
  ("Sweatshirt", "DarkBlue"):       dict(file="sw_DarkBlue.png",       cx=1162, top=964,  H=2344),
  ("Sweatshirt", "Offwhite"):       dict(file="sw_Offwhite.png",       cx=1189, top=1048, H=2380),
  ("Sweatshirt", "DarkGreen"):      dict(file="sw_DarkGreen.png",      cx=1184, top=1055, H=2344),
  ("Sweatshirt", "Black"):          dict(file="sw_Black.png",          cx=1182, top=1006, H=2344),
  # hoodies: 1342x1096 cutouts on white
  ("Hoodie", "Black"):       dict(file="hd_Black.png",       cx=672, top=535, H=1096),
  ("Hoodie", "Offwhite"):    dict(file="hd_Offwhite.png",    cx=672, top=535, H=1096),
  ("Hoodie", "IronGrey"):    dict(file="hd_IronGrey.png",    cx=672, top=535, H=1096),
  ("Hoodie", "Purple"):      dict(file="hd_Purple.png",      cx=672, top=550, H=1096),
  ("Hoodie", "AegeanBlue"):  dict(file="hd_AegeanBlue.png",  cx=672, top=550, H=1096),
}
WIDTH_RATIO = 0.1355
TALL_CAP = 1.25

def compose(art_png, style, colour, models_dir, out_path, scale=1.0, dy=0):
    m = MODELS[(style, colour)]
    base = Image.open(os.path.join(models_dir, m["file"])).convert("RGBA")
    if style == "Hoodie":
        bg = Image.new("RGBA", base.size, (255, 255, 255, 255)); bg.alpha_composite(base); base = bg
    art = Image.open(art_png).convert("RGBA")
    art = art.crop(art.split()[-1].point(lambda v: 255 if v > 20 else 0).getbbox())
    w = WIDTH_RATIO * m["H"] * scale
    h = art.height * w / art.width
    if h > TALL_CAP * WIDTH_RATIO * m["H"] * scale:
        h = TALL_CAP * WIDTH_RATIO * m["H"] * scale; w = art.width * h / art.height
    art = art.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)
    base.alpha_composite(art, (round(m["cx"] - art.width / 2), round(m["top"] + dy)))
    base.convert("RGB").save(out_path, quality=93)
    return out_path

if __name__ == "__main__":
    art, style, colour, models, out = sys.argv[1:6]
    print(compose(art, style, colour, models, out))
