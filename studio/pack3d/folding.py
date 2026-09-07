"""
Piegatura virtuale: dai pannelli 2D della fustella alle facce 3D con UV.

Il punto delicato di un astuccio a fasciatura verticale
(RETRO - CIELO - FRONTE - FONDO) e' che la piega scavalca il cielo: sul solido
il retro e i due fianchi risultano ribaltati rispetto al piano di stampa.
Qui la cosa viene ricavata dalla catena di pieghe, non imposta a mano.
"""
from __future__ import annotations

import numpy as np
import pdfplumber
from PIL import Image, ImageDraw
import pypdfium2 as pdfium

from .dieline import _segments, _technical_pens

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


def _is_chromatic(color):
    """Vero per un colore CMYK/RGB con tinta: esclude nero, grigi e tinte
    piatte a un solo canale, che possono appartenere anche alla grafica."""
    try:
        v = eval(color) if isinstance(color, str) else color
    except Exception:
        return False
    if not isinstance(v, (list, tuple)) or len(v) < 3:
        return False
    if len(v) == 4:                      # CMYK: tinta nei primi tre canali
        return max(v[:3]) > 0.15
    return max(v) - min(v) > 0.15        # RGB


HAIRLINE = 0.8   # pt: sotto questa soglia il tratto e' disegno tecnico, non grafica


def technical_palette(page, pens):
    """Colori usati dal disegno tecnico: quelli delle penne di fustella piu'
    quelli di ogni tratto a filo di capello (retini print-free, quotature)."""
    pal = {c for lw, c in pens}
    for kind in ("lines", "rects", "curves"):
        for o in getattr(page, kind):
            if kind != "lines" and not o.get("stroke"):
                continue
            if (o.get("linewidth") or 0) <= HAIRLINE:
                pal.add(str(o.get("stroking_color")))
    pal.discard("None")
    return pal


def _technical_mask(page, pens, palette, box, scale, margin=1.2):
    """Maschera del disegno tecnico dentro un pannello: tratti di fustella,
    retini delle aree print-free, quote e diciture tecniche."""
    x0, y0, x1, y1 = box
    W = max(1, round((x1 - x0) * scale))
    H = max(1, round((y1 - y0) * scale))
    m = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(m)

    def pt(x, y):
        return ((x - x0) * scale, (y - y0) * scale)

    def stroke(pts, lw):
        w = max(2, int(round(lw * scale + 2 * margin * scale)))
        if len(pts) > 1:
            dr.line([pt(*q) for q in pts], fill=255, width=w, joint="curve")

    def is_tech_stroke(o):
        lw = o.get("linewidth") or 0
        return (lw <= HAIRLINE or
                (round(lw, 2), str(o.get("stroking_color"))) in pens)

    chroma = {c for c in palette if _is_chromatic(c)}

    for ln in page.lines:
        if is_tech_stroke(ln):
            # per un segmento obliquo il bbox non dice il verso: servono i punti
            pts = list(ln.get("pts") or [])
            if len(pts) < 2:
                pts = [(ln["x0"], ln["top"]), (ln["x1"], ln["bottom"])]
            stroke(pts, ln["linewidth"] or 0)
    for rc in page.rects:
        if rc.get("stroke") and is_tech_stroke(rc):
            a, b, c, d = rc["x0"], rc["top"], rc["x1"], rc["bottom"]
            stroke([(a, b), (c, b), (c, d), (a, d), (a, b)], rc["linewidth"] or 0)
        elif rc.get("fill") and str(rc.get("non_stroking_color")) in chroma:
            dr.rectangle([pt(rc["x0"], rc["top"]), pt(rc["x1"], rc["bottom"])], fill=255)
    for cv in page.curves:
        pts = list(cv.get("pts") or [])
        if cv.get("stroke") and is_tech_stroke(cv):
            stroke(pts, cv["linewidth"] or 0)
        elif cv.get("fill") and str(cv.get("non_stroking_color")) in chroma and pts:
            # i simboli tecnici (frecce di orientamento) sono piccoli e spesso
            # composti da piu' sottotracciati: si mascherano per ingombro
            if max(cv["x1"] - cv["x0"], cv["bottom"] - cv["top"]) < 25:
                dr.rectangle([pt(cv["x0"], cv["top"]), pt(cv["x1"], cv["bottom"])], fill=255)
            elif len(pts) > 2:
                dr.polygon([pt(*q) for q in pts], fill=255)

    # quote e diciture tecniche: solo colori con tinta del disegno tecnico
    for ch in page.chars:
        if str(ch.get("non_stroking_color")) in chroma:
            dr.rectangle([pt(ch["x0"] - 0.5, ch["top"] - 0.5),
                          pt(ch["x1"] + 0.5, ch["bottom"] + 0.5)], fill=255)
    return np.asarray(m) > 127


def _inpaint(rgb, mask):
    """Riempie le zone mascherate col pixel valido piu' vicino: adatto a tratti
    sottili e a retini, dove l'intorno e' gia' il colore di fondo."""
    from scipy.ndimage import distance_transform_edt
    if not mask.any():
        return rgb
    _, idx = distance_transform_edt(mask, return_indices=True)
    return rgb[idx[0], idx[1]]


def rasterize_panels(pdf_path: str, panels: dict, dpi: int = 300,
                     inset_px: int = 4, page_no: int = 0, clean: bool = True) -> dict:
    """Ritaglia la grafica di ogni pannello da una rasterizzazione ad alta
    risoluzione. Con `clean` il disegno tecnico viene tolto dalla texture:
    sul modello 3D deve restare solo la grafica di stampa."""
    scale = dpi / 72.0
    sheet = pdfium.PdfDocument(pdf_path)[page_no].render(scale=scale).to_pil().convert("RGB")

    pens, palette = set(), set()
    page = None
    if clean:
        pdf = pdfplumber.open(pdf_path)
        page = pdf.pages[page_no]
        pens = _technical_pens(_segments(page), page.width, page.height)
        palette = technical_palette(page, pens)

    out = {}
    for name, p in panels.items():
        box = (round(p.x0 * scale), round(p.y0 * scale),
               round(p.x1 * scale), round(p.y1 * scale))
        im = sheet.crop(box)
        if clean and pens:
            arr = np.asarray(im).copy()
            mask = _technical_mask(page, pens, palette, (p.x0, p.y0, p.x1, p.y1), scale)
            mh, mw = mask.shape
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
