"""Render di presentazione: shading per faccia + ombra di appoggio."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .raster import Camera, render

# fattori ricavati per confronto fotometrico con il render di riferimento
SHADING = {"front": 0.94, "top": 0.97, "left": 0.73, "right": 0.73,
           "back": 0.94, "bottom": 0.70}


def ground_shadow(cam: Camera, dims_mm, size, drop=0.5,
                  blur=0.022, opacity=0.42, spread=1.06, skew=0.10):
    """Ombra di contatto: la faccia di appoggio proiettata e sfocata."""
    W, H, D = dims_mm
    hw, hh, hd = W / 2, H / 2, D / 2
    y = -hh - drop
    sx = W * skew   # la sorgente luminosa e' alta e spostata a destra
    quad = np.array([(-hw * spread - sx, y, hd * spread),
                     (hw * spread - sx, y, hd * spread),
                     (hw * spread - sx, y, -hd * spread - D * 0.6),
                     (-hw * spread - sx, y, -hd * spread - D * 0.6)])
    uv = cam.project(quad)
    lay = Image.new("L", (size, size), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(lay).polygon([tuple(p) for p in uv], fill=int(255 * opacity))
    return lay.filter(ImageFilter.GaussianBlur(max(1.0, blur * size)))


def studio_render(faces, cam: Camera, size=2000, ss=2, shading=None,
                  background=(255, 255, 255), shadow=True, dims_mm=None):
    shading = shading or SHADING
    fs = []
    for f in faces:
        tex = f["tex"]
        arr = np.asarray(tex.convert("RGB")) if not isinstance(tex, np.ndarray) else tex
        fs.append({**f, "tex": arr, "shade": shading.get(f["name"], 1.0)})

    img, alpha, ids = render(fs, cam, size, bg=background, ss=ss)

    if shadow and dims_mm is not None:
        sh = ground_shadow(cam, dims_mm, size)
        bg = Image.new("RGB", (size, size), background)
        dark = Image.new("RGB", (size, size), (120, 116, 112))
        base = Image.composite(dark, bg, sh)
        out = Image.composite(img, base, alpha)
        comb = Image.new("L", (size, size), 0)
        comb.paste(sh, (0, 0))
        comb = Image.fromarray(np.maximum(np.asarray(comb), np.asarray(alpha)))
        return out, comb
    return img, alpha
