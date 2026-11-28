#!/usr/bin/env python3
"""
Measure where a print sits on a garment photo, relative to the garment itself.

landmarks(img) finds the garment by colour, then returns:
  cx       horizontal centre of the torso
  neck_y   top of the garment on the centre line (bottom of the collar / hood V)
  chest_w  garment width across the shoulders, just below the neckline
  print    bounding box of the print (holes inside the garment), if any
Ratios (print size / chest width, offset below neckline / chest width) can then be
copied from the owner's own mockups onto a blank model.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

def _lab(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def landmarks(img, seed=(0.5, 0.66), tol=16):
    im = img.convert("RGB")
    s = 900 / max(im.size)
    im = im.resize((round(im.width * s), round(im.height * s)))
    a = np.array(im).astype(float); H, W = a.shape[:2]; lab = _lab(a)
    sy, sx = int(H * seed[1]), int(W * seed[0])
    patches = [lab[sy - 8:sy + 8, x - 8:x + 8].reshape(-1, 3) for x in (sx - int(W * .13), sx, sx + int(W * .13))]
    meds = [np.median(p, 0) for p in patches]
    g = sorted(meds, key=lambda m: sum(np.linalg.norm(m - n) for n in meds))[0]
    d = np.linalg.norm((lab - g) * [0.5, 1, 1], axis=-1)
    mask = d < tol
    mask = ndi.binary_opening(mask, iterations=2)
    lbl, _ = ndi.label(mask)
    comp = lbl == lbl[sy, sx] if lbl[sy, sx] else lbl == np.bincount(lbl.ravel())[1:].argmax() + 1
    filled = ndi.binary_fill_holes(ndi.binary_closing(comp, iterations=6))
    cols = np.where(filled[sy])[0]
    cx = int(np.median(cols[(cols > sx - W * .3) & (cols < sx + W * .3)])) if len(cols) else sx
    y = sy
    while y > 0 and filled[y - 1, cx]:
        y -= 1
    neck_y = y
    yc = min(H - 1, neck_y + int(H * 0.06))
    row = filled[yc]; l = r = cx
    while l > 0 and row[l - 1]: l -= 1
    while r < W - 1 and row[r + 1]: r += 1
    chest_w = r - l
    holes = filled & ~comp
    holes[:neck_y + 3] = False; holes[min(H, neck_y + int(H * 0.45)):] = False
    holes[:, :int(cx - chest_w * 0.32)] = False; holes[:, int(cx + chest_w * 0.32):] = False
    hl, n = ndi.label(holes)
    pb = None
    if n:
        sizes = ndi.sum(holes, hl, range(1, n + 1))
        keep = [i + 1 for i, sz in enumerate(sizes) if sz > H * W * 0.0002]
        if keep:
            ys, xs = np.where(np.isin(hl, keep))
            pb = (xs.min() / s, ys.min() / s, xs.max() / s, ys.max() / s)
    return dict(cx=cx / s, neck_y=neck_y / s, chest_w=chest_w / s, chest_l=l / s, chest_y=yc / s, print=pb, size=img.size)

def ratios(L):
    if not L["print"]: return None
    x0, y0, x1, y1 = L["print"]
    return dict(w=(x1 - x0) / L["chest_w"], top=(y0 - L["neck_y"]) / L["chest_w"],
                dx=((x0 + x1) / 2 - L["cx"]) / L["chest_w"], aspect=(y1 - y0) / max(1, (x1 - x0)))

def debug(img, L, out):
    im = img.convert("RGB").copy(); d = ImageDraw.Draw(im); w = max(2, im.width // 300)
    d.line([(0, L["neck_y"]), (im.width, L["neck_y"])], fill="red", width=w)
    d.line([(L["chest_l"], L["chest_y"]), (L["chest_l"] + L["chest_w"], L["chest_y"])], fill="cyan", width=w)
    d.line([(L["cx"], 0), (L["cx"], im.height)], fill="yellow", width=w)
    if L["print"]: d.rectangle(L["print"], outline="lime", width=w)
    im.thumbnail((500, 500)); im.save(out)

def plausible(r):
    """Lessons from owner feedback (28 Nov 2026). Reject a measured reference when the
    detector probably locked onto something else (hand, phone, background, pocket):
    print off-centre, glued to the neckline, too low, or too big for a small/medium chest print."""
    return (r and abs(r["dx"]) <= 0.06 and 0.12 <= r["top"] <= 0.27
            and r["w"] <= 0.45 and r["w"] ** 2 * r["aspect"] <= 0.075)
