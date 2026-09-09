"""Camere: preset di studio e fitting su un render di riferimento."""
from __future__ import annotations

import numpy as np

from .raster import Camera
from .folding import corners

PRESETS = {
    # yaw, pitch, roll (gradi), distanza mm, scala px/mm a 5000 px
    "hero-left": (30.2, 13.8, 0.0, 725.0, 17.66),
    "hero-right": (-30.2, 13.8, 0.0, 725.0, 17.66),
    "front": (0.0, 0.0, 0.0, 1500.0, 17.0),
}


def preset_camera(name, size=2000, ref_size=5000, dx=0.0, dy=0.0):
    yaw, pitch, roll, dist, scale = PRESETS[name]
    r = ref_size / size
    return Camera(np.radians(yaw), np.radians(pitch), np.radians(roll),
                  scale / r, dx, dy, dist, size / 2, size / 2)


def frame(cam, dims_mm, size, margin=0.90):
    """Adatta focale e centro perche' il solido riempia l'inquadratura."""
    C = corners(*dims_mm)
    P = np.array(list(C.values()), float)
    uv = cam.project(P)
    w = uv[:, 0].max() - uv[:, 0].min()
    h = uv[:, 1].max() - uv[:, 1].min()
    k = size * margin / max(w, h)
    cam.f *= k
    uv = cam.project(P)
    cam.cx += size / 2 - (uv[:, 0].max() + uv[:, 0].min()) / 2
    cam.cy += size / 2 - (uv[:, 1].max() + uv[:, 1].min()) / 2
    return cam


def fit_to_reference(dims_mm, image_points, size=5000, weights=None):
    """Ricava la camera che riproduce un render esistente.

    `image_points`: dict con i vertici visibili della silhouette in pixel,
    chiavi fra FTR/FBR/FBL/BBL/BTL/BTR (vedi folding.corners).
    """
    from scipy.optimize import least_squares

    C = corners(*dims_mm)
    keys = list(image_points)
    OBJ = np.array([C[k] for k in keys], float)
    IMG = np.array([image_points[k] for k in keys], float)
    Wt = np.array([(weights or {}).get(k, 1.0) for k in keys])
    cx = cy = size / 2.0

    def mk(p):
        return Camera(p[0], p[1], p[2], p[3], p[4], p[5], p[6], cx, cy)

    def resid(p):
        return ((mk(p).project(OBJ) - IMG) * Wt[:, None]).ravel()

    p0 = np.array([np.radians(30), np.radians(14), 0.0,
                   size / max(dims_mm) * 0.45, 0.0, 0.0, 800.0])
    lo = [np.radians(2), np.radians(0.5), -0.35, size / 4000, -size / 5,
          -size / 5, 200.0]
    hi = [np.radians(85), np.radians(65), 0.35, size / 20, size / 5,
          size / 5, 60000.0]
    sol = least_squares(resid, p0, bounds=(lo, hi), xtol=1e-15, ftol=1e-15,
                        max_nfev=4000)
    return mk(sol.x), float(np.abs(sol.fun).max()), sol.x
