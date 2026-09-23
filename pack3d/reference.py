"""Apprendimento dal render di riferimento: silhouette -> camera."""
from __future__ import annotations

import numpy as np
from PIL import Image

from .camera import preset_camera, fit_to_reference
from .folding import corners

Image.MAX_IMAGE_PIXELS = None
VISIBLE = ["FTR", "FBR", "FBL", "BBL", "BTL", "BTR"]


def silhouette_points(path, step=2, alpha_thr=224):
    """Punti di appoggio della silhouette in tutte le direzioni."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA"):
        m = np.asarray(im.convert("RGBA"))[..., 3] > alpha_thr
    else:  # fondo bianco
        g = np.asarray(im.convert("L"))
        m = g < 245
    ys, xs = np.nonzero(m)
    P = np.stack([xs, ys], 1).astype(np.float32)
    pts = []
    for deg in range(0, 360, step):
        t = np.radians(deg)
        d = np.array([np.cos(t), np.sin(t)], np.float32)
        pts.append(P[int(np.argmax(P @ d))])
    return np.array(pts), im.size


def _hull(P):
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def half(Q):
        h = []
        for q in Q:
            while len(h) >= 2 and np.cross(h[-1] - h[-2], q - h[-2]) <= 0:
                h.pop()
            h.append(q)
        return h

    return np.array(half(P)[:-1] + half(P[::-1])[:-1], float)


def _reduce_to(hull, n=6):
    """Riduce il poligono a n vertici togliendo quelli quasi allineati."""
    pts = [p for p in hull]
    while len(pts) > n:
        loss = []
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            loss.append(abs(np.cross(b - a, c - a)) / 2.0)
        pts.pop(int(np.argmin(loss)))
    return np.array(pts)


def learn_camera(ref_path, dims_mm, preset="hero-left"):
    """Ricava la camera del render di riferimento e l'errore residuo in px."""
    pts, (Wpx, Hpx) = silhouette_points(ref_path)
    size = max(Wpx, Hpx)
    cand = _reduce_to(_hull(pts), 6)

    # assegnazione dei vertici tramite una camera grossolana di partenza
    cam0 = preset_camera(preset, size=size, ref_size=size)
    C = corners(*dims_mm)
    guess = cam0.project(np.array([C[k] for k in VISIBLE], float))
    g = (guess - guess.mean(0))
    g /= np.abs(g).max() or 1.0
    c = (cand - cand.mean(0))
    c /= np.abs(c).max() or 1.0

    assign = {}
    used = set()
    for i, k in enumerate(VISIBLE):
        d = np.hypot(*(c - g[i]).T)
        for j in np.argsort(d):
            if j not in used:
                used.add(int(j))
                assign[k] = tuple(cand[j])
                break
    # l aletta laterale sporgente falsa leggermente lo spigolo posteriore basso
    cam, err, raw = fit_to_reference(dims_mm, assign, size=size,
                                     weights={"BBL": 0.25})
    return cam, err, assign, size
