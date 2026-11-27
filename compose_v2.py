#!/usr/bin/env python3
"""Place exact Canva artwork on a blank model using ratios measured from the owner's
own mockups of the same design (see measure_placement.py):
  print width = w * chest_w, print top = neck_y + top * chest_w, centre = cx + dx * chest_w"""
import os
from PIL import Image
LANDMARKS = {  # measured on the blank models (px in the model image)
 ("Sweatshirt","Black"):(799,1161,1190), ("Sweatshirt","DarkBlue"):(793,1108,1187),
 ("Sweatshirt","Offwhite"):(852,1158,1190), ("Sweatshirt","DarkGreen"):(852,1079,1179),
 ("Sweatshirt","BeetrootPurple"):(867,1169,1201),
 ("Hoodie","Black"):(382,525,680), ("Hoodie","Offwhite"):(379,535,674), ("Hoodie","IronGrey"):(395,561,675),
 ("Hoodie","Purple"):(376,598,675), ("Hoodie","AegeanBlue"):(379,589,658)}
FILES = {"Sweatshirt":"sw_{}.png","Hoodie":"hd_{}.png"}
def compose(art_png, style, colour, models_dir, out, w, top, dx=0.0):
    neck, cw, cx = LANDMARKS[(style, colour)]
    base = Image.open(os.path.join(models_dir, FILES[style].format(colour))).convert("RGBA")
    if style == "Hoodie":
        bg = Image.new("RGBA", base.size, (255,255,255,255)); bg.alpha_composite(base); base = bg
    art = Image.open(art_png).convert("RGBA")
    art = art.crop(art.split()[-1].point(lambda v: 255 if v > 20 else 0).getbbox())
    pw = w * cw; ph = art.height * pw / art.width
    art = art.resize((round(pw), round(ph)), Image.LANCZOS)
    base.alpha_composite(art, (round(cx + dx*cw - pw/2), round(neck + top*cw)))
    base.convert("RGB").save(out, quality=93); return out
