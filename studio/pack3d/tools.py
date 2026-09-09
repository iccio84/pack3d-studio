"""
Gli strumenti di misura esposti a Claude.

Sono involucri sottili sulle funzioni che gia' esistono in pack3d. La regola e'
una sola: qui dentro non si stima nulla, si misura. Il modello decide, il
codice misura.
"""
from __future__ import annotations

import math
import numpy as np

from . import dieline as dl
from . import flowpack as fpk
from . import cup as cupmod
from . import techink

PT2MM = dl.PT2MM
_PATHS = {}
_PREVIEW = {}


def _plain(o):
    """numpy fuori dai risultati: json.dumps non sa serializzare np.float64."""
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


def _single_entry_cache(cache, key):
    """Tiene al piu' un pdf in cache: ogni richiesta ne usa uno diverso (file
    temporaneo), quindi accumulare le vecchie voci sarebbe solo una perdita di
    memoria per la durata del processo, non un guadagno di velocita'."""
    if set(cache) - {key}:
        cache.clear()


def _paths(pdf):
    _single_entry_cache(_PATHS, pdf)
    if pdf not in _PATHS:
        _PATHS[pdf] = cupmod.flatten_paths(pdf)
    return _PATHS[pdf]


# --------------------------------------------------------------------------- #
def classify_technical(pdf):
    """Come togliere il disegno tecnico: quale livello di certezza abbiamo."""
    c = techink.classify(pdf)
    return {k: c[k] for k in ("level", "method", "certainty", "detail")}


def list_paths(pdf, limit: int = 12):
    """Tracciati chiusi con ingombro in mm, dal piu' grande.

    Comprende i disegni tecnici in miniatura fuori dall'artwork: spesso sono
    piu' puliti del contorno tracciato sotto la grafica.
    """
    out = []
    P = _paths(pdf)
    order = sorted(range(len(P)),
                   key=lambda i: -((P[i][:, 0].max() - P[i][:, 0].min())
                                   * (P[i][:, 1].max() - P[i][:, 1].min())))
    for i in order[:limit]:
        Q = P[i]
        out.append(dict(index=i, punti=len(Q),
                        larghezza_mm=round((Q[:, 0].max() - Q[:, 0].min()) * PT2MM, 2),
                        altezza_mm=round((Q[:, 1].max() - Q[:, 1].min()) * PT2MM, 2),
                        x_mm=round(Q[:, 0].min() * PT2MM, 1),
                        y_mm=round(Q[:, 1].min() * PT2MM, 1)))
    return out


def fit_sector(pdf, path_index: int):
    """Adatta due archi concentrici a un tracciato.

    Il **residuo** dice se quel contorno e' pulito: serve a scegliere fra il
    disegno in miniatura e il contorno sotto la grafica senza doverli vedere.
    """
    P = _paths(pdf)
    if not 0 <= path_index < len(P):
        return {"errore": "indice fuori intervallo"}
    try:
        s = cupmod.fit_sector(P[path_index])
        c = cupmod.sector_to_cup(s)
    except Exception as e:
        return {"errore": str(e)[:120]}
    return dict(R_interno=round(s.R1, 2), R_esterno=round(s.R2, 2),
                apertura_gradi=round(math.degrees(s.alpha), 2),
                residuo_mm=round(s.resid_mm, 3),
                scarto_archi_gradi=round(math.degrees(s.ang_check), 3),
                d_bocca=round(c.d_mouth, 2), d_fondo=round(c.d_base, 2),
                altezza=round(c.height, 2), apotema=round(c.slant, 2))


def analyze_carton(pdf):
    """Griglia della fustella, verso di fasciatura e quote di un astuccio."""
    try:
        d = dl.analyze(pdf)
    except Exception as e:
        return {"errore": str(e)[:120]}
    if not d.panels:
        return {"errore": "pannelli non risolvibili"}
    return dict(layout=d.layout, dims_mm=list(d.dims_mm),
                pannelli={k: [round(p.w_mm, 1), round(p.h_mm, 1)]
                          for k, p in sorted(d.panels.items())},
                avvisi=dl.check(d))


def analyze_flowpack(pdf):
    """Fasce del nastro, perimetro e saldature di un flowpack."""
    try:
        fp = fpk.analyze_auto(pdf)
    except Exception as e:
        return {"errore": str(e)[:160]}
    return dict(nastro_mm=fp.web_mm, passo_mm=fp.step_mm,
                fronte=fp.W, spessore=fp.T, corpo=fp.L,
                pinna_testa=fp.end_fin, falda_longitudinale=fp.side_fin,
                perimetro=round(fp.girth, 1),
                verifica_perimetro_piu_falde=round(fp.girth + 2 * fp.side_fin, 1))


def measure_region(pdf, x_mm, y_mm, w_mm, h_mm, dpi: int = 200):
    """Misure su un ritaglio: ingombro stampato, croma media, righe verticali.

    Serve per i dati che non stanno nei tracciati: dove finisce la stampa,
    quanto e' fitta una zigrinatura, dove cade un elemento grafico.
    """
    import pypdfium2 as pdfium
    s = dpi / 72.0
    key = (pdf, dpi)
    _single_entry_cache(_PREVIEW, key)
    if key not in _PREVIEW:
        _PREVIEW[key] = pdfium.PdfDocument(pdf)[0].render(scale=s).to_pil().convert("RGB")
    im = _PREVIEW[key]
    x0, y0 = int(x_mm / PT2MM * s), int(y_mm / PT2MM * s)
    x1, y1 = int((x_mm + w_mm) / PT2MM * s), int((y_mm + h_mm) / PT2MM * s)
    # ritaglio con PIL prima di passare a numpy: l'intera pagina come intero a
    # 64 bit puo' pesare centinaia di MB, troppo sul piano free di Render.
    # A differenza dello slicing numpy di prima, Image.crop riempie di nero un
    # box che sconfina: i bordi vanno troncati a mano per lo stesso risultato.
    c = im.crop((max(x0, 0), max(y0, 0), min(x1, im.width), min(y1, im.height)))
    if c.width < 2 or c.height < 2:
        return {"errore": "ritaglio vuoto"}
    r = np.asarray(c).astype(int)
    chroma = (r.max(2) - r.min(2))
    col = chroma.mean(0)
    idx = np.nonzero(col > 25)[0]
    g = r.mean(2)
    line = g[g.shape[0] // 2]
    d = (line < line.mean()).astype(int)
    return dict(croma_media=round(float(chroma.mean()), 1),
                margine_non_stampato_sx_mm=round(float(idx[0] / s * PT2MM), 1) if len(idx) else None,
                margine_non_stampato_dx_mm=round(float((len(col) - 1 - idx[-1]) / s * PT2MM), 1) if len(idx) else None,
                righe_scure=int(np.abs(np.diff(d)).sum()) // 2)


TOOLS = [
    dict(name="classify_technical",
         description="Come rimuovere il disegno tecnico da questo PDF: Processing "
                     "Steps ISO 19593, livelli OCG, nomi delle separazioni o "
                     "euristica. Restituisce il livello di certezza.",
         input_schema={"type": "object", "properties": {}}),
    dict(name="list_paths",
         description="Tracciati chiusi del PDF con ingombro in mm, dal piu' grande. "
                     "Include i disegni tecnici in miniatura fuori dall'artwork, "
                     "che sono spesso piu' puliti del contorno sotto la grafica.",
         input_schema={"type": "object",
                       "properties": {"limit": {"type": "integer"}}}),
    dict(name="fit_sector",
         description="Adatta due archi concentrici a un tracciato e restituisce "
                     "raggi, apertura, quote della coppa e il RESIDUO in mm. "
                     "Residuo basso significa contorno pulito: usalo per scegliere "
                     "fra piu' tracciati candidati.",
         input_schema={"type": "object",
                       "properties": {"path_index": {"type": "integer"}},
                       "required": ["path_index"]}),
    dict(name="analyze_carton",
         description="Griglia della fustella, verso di fasciatura e quote L/H/P "
                     "di un astuccio, con avvisi di coerenza.",
         input_schema={"type": "object", "properties": {}}),
    dict(name="analyze_flowpack",
         description="Fasce del nastro, sezione, corpo e saldature di un flowpack. "
                     "Controlla che perimetro + 2 falde sia uguale alla larghezza "
                     "del nastro.",
         input_schema={"type": "object", "properties": {}}),
    dict(name="measure_region",
         description="Misure su un ritaglio in mm: croma media, margini non "
                     "stampati, numero di righe verticali. Per i dati che non "
                     "stanno nei tracciati.",
         input_schema={"type": "object",
                       "properties": {"x_mm": {"type": "number"},
                                      "y_mm": {"type": "number"},
                                      "w_mm": {"type": "number"},
                                      "h_mm": {"type": "number"}},
                       "required": ["x_mm", "y_mm", "w_mm", "h_mm"]}),
]

_RAW = dict(classify_technical=classify_technical, list_paths=list_paths,
            fit_sector=fit_sector, analyze_carton=analyze_carton,
            analyze_flowpack=analyze_flowpack, measure_region=measure_region)

RUN = {k: (lambda f: lambda *a, **kw: _plain(f(*a, **kw)))(v) for k, v in _RAW.items()}
