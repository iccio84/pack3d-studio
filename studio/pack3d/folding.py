"""
Piegatura virtuale: dai pannelli 2D della fustella alle facce 3D con UV.

Il punto delicato di un astuccio a fasciatura verticale
(RETRO - CIELO - FRONTE - FONDO) e' che la piega scavalca il cielo: sul solido
il retro e i due fianchi risultano ribaltati rispetto al piano di stampa.
Qui la cosa viene ricavata dalla catena di pieghe, non imposta a mano.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from . import dieline, tracciati
from .dieline import _technical_pens, render_page

Image.MAX_IMAGE_PIXELS = None


def corners(W: float, H: float, D: float) -> dict:
    """Gli otto vertici del solido, centrato nell'origine. Fronte a z = +D/2."""
    hw, hh, hd = W / 2.0, H / 2.0, D / 2.0
    return {
        "FTL": (-hw,  hh,  hd), "FTR": ( hw,  hh,  hd),
        "FBR": ( hw, -hh,  hd), "FBL": (-hw, -hh,  hd),
        "BTL": (-hw,  hh, -hd), "BTR": ( hw,  hh, -hd),
        "BBR": ( hw, -hh, -hd), "BBL": (-hw, -hh, -hd),
    }


# Per ogni faccia: i quattro vertici corrispondenti agli angoli della texture
# nell'ordine (0,0) - (w,0) - (w,h) - (0,h), cioe' alto-sx, alto-dx, basso-dx,
# basso-sx del ritaglio piano.
#
#  - fronte  : orientamento naturale
#  - cielo   : la riga alta del ritaglio confina col retro, quindi va sul dietro
#  - fondo   : la riga alta confina col fronte, quindi va sul davanti
#  - retro   : oltre il cielo la fasciatura si ribalta -> alto piano = basso solido
#  - fianchi : agganciati al retro, ereditano lo stesso ribaltamento
FOLD_V = {
    "front":  ("FTL", "FTR", "FBR", "FBL"),
    "top":    ("BTL", "BTR", "FTR", "FTL"),
    "bottom": ("FBL", "FBR", "BBR", "BBL"),
    "back":   ("BBL", "BBR", "BTR", "BTL"),
    "left":   ("FBL", "BBL", "BTL", "FTL"),
    "right":  ("BBR", "FBR", "FTR", "BTR"),
}


# Fasciatura orizzontale: tutte le pieghe sono attorno a cordonature verticali,
# quindi l'orientamento verticale non si ribalta mai; la direzione orizzontale
# gira attorno alla scatola FRONTE -> FIANCO DX -> RETRO -> FIANCO SX.
FOLD_H = {
    "front":  ("FTL", "FTR", "FBR", "FBL"),
    "right":  ("FTR", "BTR", "BBR", "FBR"),
    "back":   ("BTR", "BTL", "BBL", "BBR"),
    "left":   ("BTL", "FTL", "FBL", "BBL"),
    "top":    ("BTL", "BTR", "FTR", "FTL"),
    "bottom": ("FBL", "FBR", "BBR", "BBL"),
}

FOLDS = {"vwrap": FOLD_V, "hwrap": FOLD_H}


def disegno_tecnico(pdf_path, page_no=0):
    """Gli elementi da togliere dalla texture, in due passate leggere.

    La prima passata trova le penne della fustella e i colori dei tratti a
    filo di capello; la seconda, sapendo gia' cosa cercare, si tiene solo
    quello che serve. Su uno steso curvo (coppe, settori) non ci sono
    segmenti dritti lunghi da cui dedurre la penna: resta valida la regola
    del filo di capello, che vale anche quando di penne non se ne trova
    nessuna.
    """
    colori = set()
    segs, larghezza, altezza = tracciati.segmenti(pdf_path, page_no,
                                                  tavolozza=colori)
    penne = _technical_pens(segs, larghezza, altezza)
    tinte = tracciati.tinte(colori | {c for _, c in penne})
    tinte -= tracciati.piatte(pdf_path, page_no)
    return tracciati.tecnici(pdf_path, page_no, penne, tinte)


def _technical_mask(dt, box, scale, margin=1.2):
    """Maschera del disegno tecnico dentro un pannello: tratti di fustella,
    retini delle aree print-free, quote e diciture tecniche."""
    tratti, pieni, scritte = dt
    x0, y0, x1, y1 = box
    W = max(1, round((x1 - x0) * scale))
    H = max(1, round((y1 - y0) * scale))
    m = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(m)

    def pt(x, y):
        return ((x - x0) * scale, (y - y0) * scale)

    for punti, lw in tratti:
        dr.line([pt(*q) for q in punti], fill=255, joint="curve",
                width=max(2, int(round(lw * scale + 2 * margin * scale))))
    for (a, b, c, d), punti in pieni:
        if punti is None:
            dr.rectangle([pt(a, b), pt(c, d)], fill=255)
        else:
            dr.polygon([pt(*q) for q in punti], fill=255)
    for a, b, c, d in scritte:
        dr.rectangle([pt(a - 0.5, b - 0.5), pt(c + 0.5, d + 0.5)], fill=255)
    return np.asarray(m) > 127


def _inpaint(rgb, mask):
    """Riempie le zone mascherate col pixel valido piu' vicino: adatto a tratti
    sottili e a retini, dove l'intorno e' gia' il colore di fondo."""
    from scipy.ndimage import distance_transform_edt
    if not mask.any():
        return rgb
    # Le distanze non ci servono, servono solo gli indici del pixel valido
    # piu' vicino. Chiederle comunque costa un array float64 grande quanto
    # l'immagine: su un foglio come quello del Brioss sono decine di MB
    # calcolati e buttati.
    idx = distance_transform_edt(mask, return_distances=False,
                                 return_indices=True)
    return rgb[idx[0], idx[1]]


def rasterize_panels(pdf_path: str, panels: dict, dpi: int = 300,
                     inset_px: int = 4, page_no: int = 0, clean: bool = True) -> dict:
    """Ritaglia la grafica di ogni pannello da una rasterizzazione ad alta
    risoluzione. Con `clean` il disegno tecnico viene tolto dalla texture:
    sul modello 3D deve restare solo la grafica di stampa."""
    scale = dpi / 72.0
    sheet = render_page(pdf_path, page_no, scale)
    # Preso il foglio, la pagina in cassa non serve piu' a nessuno: da qui in
    # giu' si alloca la maschera e la texture, e tenerla viva vorrebbe dire
    # sommare due rasterizzazioni nel momento peggiore.
    dieline.scarta_resa()

    dt = disegno_tecnico(pdf_path, page_no) if clean else None

    out = {}
    for name, p in panels.items():
        box = (round(p.x0 * scale), round(p.y0 * scale),
               round(p.x1 * scale), round(p.y1 * scale))
        im = sheet.crop(box)
        if clean:
            arr = np.asarray(im).copy()
            mask = _technical_mask(dt, (p.x0, p.y0, p.x1, p.y1), scale)
            mask = mask[:arr.shape[0], :arr.shape[1]]
            if mask.shape != arr.shape[:2]:
                pad = np.zeros(arr.shape[:2], bool)
                pad[:mask.shape[0], :mask.shape[1]] = mask
                mask = pad
            im = Image.fromarray(_inpaint(arr, mask))
        w, h = im.size
        if inset_px and w > 4 * inset_px and h > 4 * inset_px:
            im = im.crop((inset_px, inset_px, w - inset_px, h - inset_px))
            im = im.resize((w, h), Image.LANCZOS)
        out[name] = im
    return out


def build_faces(dims_mm, textures: dict, layout: str = "vwrap") -> list:
    """Facce pronte per rasterizzatore ed export: quad 3D + texture + UV."""
    W, H, D = dims_mm
    C = corners(W, H, D)
    faces = []
    for name, keys in FOLDS[layout].items():
        if name not in textures:
            continue
        faces.append({
            "name": name,
            "quad": [C[k] for k in keys],
            "uv": [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
            "tex": textures[name],
        })
    return faces
