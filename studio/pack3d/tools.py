"""
Gli strumenti di misura esposti a Claude.

Sono involucri sottili sulle funzioni che gia' esistono in pack3d. La regola e'
una sola: qui dentro non si stima nulla, si misura. Il modello decide, il
codice misura.
"""
from __future__ import annotations

import math
import os

import numpy as np

from . import dieline as dl
from . import flowpack as fpk
from . import cup as cupmod
from . import techink

PT2MM = dl.PT2MM
_PATHS = {}


def _plain(o):
    """numpy fuori dai risultati: json.dumps non sa serializzare np.float64."""
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


def _paths(pdf):
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
    s = dpi / 72.0
    im = dl.render_page(pdf, 0, s)
    a = np.asarray(im).astype(int)
    x0, y0 = int(x_mm / PT2MM * s), int(y_mm / PT2MM * s)
    x1, y1 = int((x_mm + w_mm) / PT2MM * s), int((y_mm + h_mm) / PT2MM * s)
    r = a[max(y0, 0):y1, max(x0, 0):x1]
    if r.size == 0:
        return {"errore": "ritaglio vuoto"}
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


# --------------------------------------------------------------------------- #
# pulizia e controllo visivo
# --------------------------------------------------------------------------- #
def _png_b64(arr, maxw=900):
    import base64, io
    from PIL import Image
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)))
    b = io.BytesIO(); im.save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


_CLEAN = {}


def clean_artwork(pdf, x_mm, y_mm, w_mm, h_mm, dt_x_mm=None, dt_y_mm=None,
                  drop=None, dpi=300):
    """Ripulisce lo steso e restituisce le metriche della pulizia.

    Tre passaggi, nell'ordine che ha funzionato sul campo: maschera del disegno
    tecnico presa dalla miniatura o dalla INSIDE VIEW; grafica messa al sicuro
    PRIMA di rimuovere; disegno tecnico ridipinto con le tinte piatte del pack,
    non riempito dal pixel vicino.
    """
    from scipy.ndimage import binary_dilation, distance_transform_edt, label, uniform_filter
    s = dpi / 72.0
    page = dl.render_page(pdf, 0, s)
    A = np.asarray(page).astype(int)

    def cut(x, y, w, h):
        return A[round(y / PT2MM * s):round((y + h) / PT2MM * s),
                 round(x / PT2MM * s):round((x + w) / PT2MM * s)]

    out = cut(x_mm, y_mm, w_mm, h_mm)
    H, W, _ = out.shape

    # maschera del disegno tecnico: la vista tecnica ha lo stesso ingombro
    dt = np.zeros((H, W), bool)
    if dt_x_mm is not None:
        from PIL import Image as _I
        inn = cut(dt_x_mm, dt_y_mm if dt_y_mm is not None else y_mm, w_mm, h_mm)
        dt = np.asarray(_I.fromarray(((inn.max(2) < 245) * 255).astype(np.uint8))
                        .resize((W, H))) > 127
        dt = binary_dilation(dt, np.ones((5, 5)))

    cleaned = out.copy()
    salvati = 0
    if drop:
        import tempfile, os as _os
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False); tmp.close()
        _strip(pdf, tmp.name, drop)
        B = np.asarray(dl.render_page(tmp.name, 0, s)).astype(int)
        strip = B[round(y_mm / PT2MM * s):round(y_mm / PT2MM * s) + H,
                  round(x_mm / PT2MM * s):round(x_mm / PT2MM * s) + W]
        perso = np.abs(out - strip).max(2) > 25
        lab, _ = label(binary_dilation(perso & (~dt), np.ones((3, 3))))
        sz = np.bincount(lab.ravel())[1:]
        keep = np.zeros((H, W), bool)
        for i, v in enumerate(sz):
            if v >= 120:
                keep |= (lab == i + 1)
        cleaned = strip.copy(); cleaned[keep] = out[keep]
        salvati = int((sz >= 120).sum())
        _os.unlink(tmp.name)

    # il disegno tecnico cade quasi sempre su tinta piatta: si ridipinge
    pal = _palette(cleaned, ~dt)
    d2 = ((cleaned[..., None, :] - pal[None, None]) ** 2).sum(-1)
    lab2, dist = d2.argmin(-1), np.sqrt(d2.min(-1))
    piatta = dist < 38
    su_img = dt & binary_dilation((~piatta) & (uniform_filter(cleaned.std(2).astype(float), 15) > 18),
                                  np.ones((9, 9)))
    valido = (~dt) & piatta
    if valido.any() and dt.any():
        _, idx = distance_transform_edt(~valido, return_indices=True)
        cls = lab2[idx[0], idx[1]]
        dip = dt & (~su_img)
        cleaned[dip] = pal[cls[dip]]
    else:
        dip = np.zeros((H, W), bool)

    _CLEAN[pdf] = dict(orig=out, clean=cleaned, dt=dt, img=su_img)
    return dict(maschera_dt_pct=round(100 * float(dt.mean()), 2),
                grafica_salvata_blocchi=salvati,
                ridipinto_pct=round(100 * float(dip.mean()), 2),
                dt_su_immagine_pct=round(100 * float(su_img.mean()), 2),
                tinte_piatte=[list(map(int, c)) for c in pal],
                nota=("dt_su_immagine_pct e' la parte che una riverniciatura "
                      "piatta non puo' risolvere: se e' alta serve il piano B"))


def _palette(img, mask, k=5):
    """Tinte piatte dominanti, quantizzando i pixel non tecnici."""
    px = img[mask]
    if len(px) > 60000:
        px = px[np.random.default_rng(0).choice(len(px), 60000, replace=False)]
    q = (px // 24 * 24)
    uq, cnt = np.unique(q, axis=0, return_counts=True)
    top = uq[np.argsort(-cnt)[:k]]
    out = []
    for c in top:
        sel = (np.abs(px - c).max(1) < 24)
        if sel.sum() > 200:
            out.append(np.median(px[sel], axis=0))
    return np.array(out if out else [[255, 255, 255]])


def _strip(src, dst, drop):
    import pypdf
    from pypdf.generic import ContentStream
    r = pypdf.PdfReader(src); w = pypdf.PdfWriter(); w.append(r)
    drop = {d.lower() for d in drop}
    page = w.pages[0]

    def bad(res):
        out = set()
        cs = res.get("/ColorSpace")
        if not cs:
            return out
        for k, v in cs.get_object().items():
            try:
                o = v.get_object()
                nm = [str(o[1])] if o[0] == "/Separation" else list(o[1]) if o[0] == "/DeviceN" else []
                nm = [str(x).lstrip("/").replace("#20", " ").lower() for x in nm]
                if nm and all(n in drop for n in nm):
                    out.add(str(k))
            except Exception:
                pass
        return out

    names = bad(page["/Resources"])
    cs = ContentStream(page.get_contents(), w)
    ncs = None; ops_out = []
    for operands, op in cs.operations:
        if op == b"cs":
            ncs = str(operands[0])
        if op in (b"f", b"F", b"f*", b"S", b"s", b"B", b"B*", b"b", b"b*") and ncs in names:
            ops_out.append(([], b"n")); continue
        ops_out.append((operands, op))
    cs.operations = ops_out
    page.replace_contents(cs)
    with open(dst, "wb") as fh:
        w.write(fh)


def visual_check(pdf):
    """GUARDA il risultato: originale e ripulito affiancati, piu' le metriche.

    E' il passo che nessuna regola sostituisce. Le regole dicono cosa togliere;
    solo l'occhio si accorge che e' sparito un pezzo di logo.
    """
    d = _CLEAN.get(pdf)
    if not d:
        return {"errore": "chiama prima clean_artwork"}
    o, c = d["orig"], d["clean"]
    H, W, _ = o.shape
    canvas = np.full((H, W * 2 + 16, 3), 255)
    canvas[:, :W] = o; canvas[:, W + 16:] = c
    perso = (np.abs(o - c).max(2) > 30) & (o.max(2) < 200)
    return {"__image__": _png_b64(canvas),
            "testo": ("A sinistra l'originale, a destra il ripulito. "
                      "Guarda se e' sparito qualcosa che e' GRAFICA: loghi, "
                      "marchi, testo di prodotto. Un logo perso e' un errore "
                      "grave, un residuo tecnico no. "
                      "Pixel scuri spariti: %.2f%%" % (100 * perso.mean()))}


TOOLS += [
    dict(name="clean_artwork",
         description="Ripulisce lo steso dal disegno tecnico: maschera dalla vista "
                     "tecnica, grafica salvata prima della rimozione, DT ridipinto "
                     "con le tinte piatte. Restituisce le metriche, fra cui la "
                     "quota di DT che cade su immagine.",
         input_schema={"type": "object",
                       "properties": {"x_mm": {"type": "number"}, "y_mm": {"type": "number"},
                                      "w_mm": {"type": "number"}, "h_mm": {"type": "number"},
                                      "dt_x_mm": {"type": "number"},
                                      "drop": {"type": "array", "items": {"type": "string"}}},
                       "required": ["x_mm", "y_mm", "w_mm", "h_mm"]}),
    dict(name="visual_check",
         description="GUARDA il confronto prima/dopo la pulizia. Da chiamare SEMPRE "
                     "dopo clean_artwork e prima di costruire: serve ad accorgersi "
                     "che e' sparita della grafica, cosa che le metriche non dicono.",
         input_schema={"type": "object", "properties": {}}),
]
_RAW.update(clean_artwork=clean_artwork, visual_check=visual_check)
RUN = {k: (lambda f: lambda *a, **kw: _plain(f(*a, **kw)))(v) for k, v in _RAW.items()}


# --------------------------------------------------------------------------- #
# piano B: ricostruzione generativa dentro la maschera
# --------------------------------------------------------------------------- #
OPENAI_IMAGE_MODEL = os.environ.get("PACK3D_IMAGE_MODEL", "gpt-image-2.5-sunburst")


def reconstruct_area(pdf, prompt=None, model=None):
    """Ricostruisce la grafica dove il disegno tecnico cade su immagine.

    E' il piano B: si usa solo quando la riverniciatura a tinta piatta non puo'
    arrivare, cioe' quando il disegno tecnico attraversa una foto.

    Due cautele, entrambe necessarie:

    1. Con GPT Image il mascheramento e' guidato dal prompt: il modello usa la
       maschera come indicazione ma puo' non seguirne la forma con precisione.
       Per questo la ricomposizione la facciamo noi, tenendo i pixel originali
       fuori dalla maschera. Cosi' logo e grafica non possono essere riscritti.
    2. Un modello generativo rigenera i pixel, quindi bordi e posizioni possono
       spostarsi: la zona trattata va tenuta la piu' piccola possibile.
    """
    import base64, io
    from PIL import Image

    d = _CLEAN.get(pdf)
    if not d:
        return {"errore": "chiama prima clean_artwork"}
    area = d["img"]
    if not area.any():
        return {"nota": "nessuna zona da ricostruire: il disegno tecnico non "
                        "cade su immagine", "ricostruito_pct": 0.0}

    try:
        from openai import OpenAI
    except ImportError:
        return {"errore": "libreria openai non installata"}
    if not os.environ.get("OPENAI_API_KEY"):
        return {"errore": "OPENAI_API_KEY non impostata"}

    base = d["clean"]
    H, W, _ = base.shape
    ys, xs = np.nonzero(area)
    pad = 24
    y0, y1 = max(0, ys.min() - pad), min(H, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(W, xs.max() + pad + 1)
    tile = base[y0:y1, x0:x1]
    hole = area[y0:y1, x0:x1]

    # la maschera va in PNG con le zone da rifare completamente trasparenti
    rgba = np.dstack([tile, np.where(hole, 0, 255)]).astype(np.uint8)
    buf_img, buf_msk = io.BytesIO(), io.BytesIO()
    Image.fromarray(tile.astype(np.uint8)).save(buf_img, "PNG")
    Image.fromarray(rgba).save(buf_msk, "PNG")
    buf_img.seek(0); buf_msk.seek(0)
    buf_img.name, buf_msk.name = "tile.png", "mask.png"

    testo = prompt or (
        "Ricostruisci la grafica di packaging nelle sole zone trasparenti, "
        "proseguendo in modo continuo il contenuto circostante. Non aggiungere "
        "testo, loghi o elementi nuovi. Non modificare nulla fuori da quelle zone.")
    try:
        cli = OpenAI()
        r = cli.images.edit(model=model or OPENAI_IMAGE_MODEL,
                            image=buf_img, mask=buf_msk, prompt=testo,
                            size="auto")
        out = np.asarray(Image.open(io.BytesIO(base64.b64decode(r.data[0].b64_json)))
                         .convert("RGB").resize((tile.shape[1], tile.shape[0]))).astype(int)
    except Exception as e:
        return {"errore": "chiamata immagine fallita: %s" % str(e)[:160]}

    # ricomposizione: dal risultato si prende SOLO cio' che sta nella maschera
    nuovo = base.copy()
    reg = nuovo[y0:y1, x0:x1]
    reg[hole] = out[hole]
    nuovo[y0:y1, x0:x1] = reg
    d["clean"] = nuovo
    return dict(modello=model or OPENAI_IMAGE_MODEL,
                ricostruito_pct=round(100 * float(area.mean()), 3),
                riquadro_px=[int(x0), int(y0), int(x1), int(y1)],
                nota="ricomposto dentro la maschera; fuori restano i pixel "
                     "originali. Chiama visual_check per guardare il risultato")


def area_riservata(pdf, x_mm, y_mm, w_mm, h_mm, dpi=36):
    """PROPONE la rimozione di un'area riservata indicata a occhio, e la MOSTRA.

    Serve per le aree riservate che il file non dichiara da nessuna parte: sul
    cartotecnico Pingui T6 e sul Kinder Bueno Dark T2 il nome sta solo nella
    legenda, non scritto sopra il riquadro, e la lettura automatica non ha
    niente da leggere. A occhio invece sono ovvie.

    Tu dici DOVE, il codice trova CHE COSA: dentro il riquadro si guarda quale
    lastra mette l'inchiostro pieno, e quella si toglie per nome. Cosi' il
    bordo esatto non lo decidi tu, e sbagliare il riquadro di qualche
    millimetro non cambia il risultato.

    Non decide per te, e non puo': un rettangolo pieno puo' essere anche il
    fondo della grafica, e i numeri non li distinguono - su Colazione la
    fascia `TEXT AREA` copre il 6,5% del foglio e `Kinder ORANGE`, che e'
    grafica, il 7,9%. Per questo torna un'IMMAGINE con in rosso tutto quello
    che quella lastra dipinge: GUARDALA. Se il rosso tocca grafica la
    proposta e' sbagliata e va lasciata cadere.
    """
    from PIL import Image
    from . import techink

    esito = techink.lastra_nel_riquadro(pdf, x_mm, y_mm, w_mm, h_mm, dpi=dpi)
    if not esito:
        return {"nota": "nessuna lastra piena dentro il riquadro: li' non c'e' "
                        "un'area riservata, oppure il riquadro e' fuori posto"}
    mappe = techink.mappe_lastre(pdf, 0, dpi)
    mappa = mappe.get(esito["lastra"])
    if mappa is None:
        return esito

    s = 1.0
    base = np.asarray(dl.render_page(pdf, 0, s).convert("RGB")).astype(np.uint8)
    H, W, _ = base.shape
    ink = np.asarray(Image.fromarray(
        ((255 - mappa.astype(int)) >= 128).astype(np.uint8) * 255).resize((W, H))) > 127
    # base in GRIGIO, lastra in rosso pieno. Evidenziare in rosso sopra i
    # colori veri non si legge: il Pingui T6 ha una fascia di grafica rossa
    # grande quanto mezzo pack, e il rosso dell'evidenziatore ci spariva
    # dentro. Cosi' invece tutto quello che e' colorato e' la lastra.
    g = base.mean(2)
    vista = np.dstack([g, g, g]).astype(np.uint8)
    vista[ink] = (255, 0, 0)
    # il riquadro chiesto, perche' si veda anche dove hai puntato
    x0, y0 = int(x_mm / PT2MM * s), int(y_mm / PT2MM * s)
    x1, y1 = int((x_mm + w_mm) / PT2MM * s), int((y_mm + h_mm) / PT2MM * s)
    for xx in range(max(0, x0), min(W, x1)):
        for yy in (y0, y1 - 1):
            if 0 <= yy < H:
                vista[yy, xx] = (0, 0, 255)
    for yy in range(max(0, y0), min(H, y1)):
        for xx in (x0, x1 - 1):
            if 0 <= xx < W:
                vista[yy, xx] = (0, 0, 255)

    esito["__image__"] = _png_b64(vista.astype(int))
    esito["testo"] = (
        "In ROSSO tutto quello che la lastra '%s' dipinge sul foglio, in BLU "
        "il riquadro che hai indicato. GUARDA il rosso: se tocca grafica - un "
        "logo, una foto, il fondo del pack - questa NON e' un'area riservata "
        "e non va dichiarata. Se il rosso sta solo su riquadri pieni con "
        "scritto dentro il nome di un'area, allora si'. La lastra copre il "
        "%.2f%% del foglio, e quel numero da solo non decide niente."
        % (esito["lastra"], esito["copertura_foglio_pct"]))
    return esito


TOOLS.append(
    dict(name="area_riservata",
         description="PROPONE di togliere un'area riservata (GDA, COVERED AREA, "
                     "TEXT AREA, BEST BEFORE AREA, BAR CODE AREA, PRINT FREE "
                     "AREA, NEUTRAL AREA) indicandola con un riquadro in mm. "
                     "Trova la lastra che la dipinge e MOSTRA in rosso tutto "
                     "quello che quella lastra copre: guarda l'immagine prima "
                     "di dichiararla. Le aree riservate non devono mai comparire "
                     "nel render.",
         input_schema={"type": "object",
                       "properties": {"x_mm": {"type": "number"},
                                      "y_mm": {"type": "number"},
                                      "w_mm": {"type": "number"},
                                      "h_mm": {"type": "number"}},
                       "required": ["x_mm", "y_mm", "w_mm", "h_mm"]}))
_RAW["area_riservata"] = area_riservata


TOOLS.append(
    dict(name="reconstruct_area",
         description="PIANO B: ricostruisce con un modello di immagine la grafica "
                     "dove il disegno tecnico cade su foto e la riverniciatura a "
                     "tinta piatta non puo' arrivare. Da usare solo se "
                     "dt_su_immagine_pct e' significativo. Il risultato viene "
                     "ricomposto dentro la maschera: fuori restano i pixel "
                     "originali, quindi loghi e grafica non vengono riscritti.",
         input_schema={"type": "object",
                       "properties": {"prompt": {"type": "string"}}}))
_RAW["reconstruct_area"] = reconstruct_area
RUN = {k: (lambda f: lambda *a, **kw: _plain(f(*a, **kw)))(v) for k, v in _RAW.items()}


def find_blocks(pdf, dpi=100, min_mm=60.0):
    """Elenca i blocchi della tavola, distinguendo lo stampato dal tecnico.

    Un disegno tecnico contiene quasi sempre piu' viste: la OUTSIDE VIEW con la
    grafica, la INSIDE VIEW o le miniature con il solo tecnico, i cartigli.
    Misurare sull'intera pagina da' quote senza senso, ed e' l'errore che fa
    uscire un pack largo quanto il foglio.

    Per ogni blocco riporta ingombro, quota di superficie colorata e quota di
    tratto sottile: il primo distingue lo stampato, il secondo il tecnico.
    """
    from scipy.ndimage import label, binary_closing, find_objects
    s = dpi / 72.0
    im = dl.render_page(pdf, 0, s)
    # int16 e non int: qui si fanno solo max, min e differenze su canali
    # 0-255, e il //32 piu' sotto tiene i valori sotto 7168. int e' int64 e
    # moltiplicava per otto la rasterizzazione di un foglio grande.
    a = np.asarray(im).astype(np.int16)
    occupato = binary_closing(a.max(2) < 248, np.ones((7, 7)))
    lab, n = label(occupato)
    out = []
    for i, sl in enumerate(find_objects(lab)):
        if sl is None:
            continue
        h = (sl[0].stop - sl[0].start) / s * PT2MM
        w = (sl[1].stop - sl[1].start) / s * PT2MM
        if min(w, h) < min_mm:
            continue
        reg = a[sl]
        m = (lab[sl] == i + 1)
        chroma = (reg.max(2) - reg.min(2))
        colore = float((chroma[m] > 30).mean()) if m.any() else 0.0
        scuro = float((reg.max(2)[m] < 200).mean()) if m.any() else 0.0
        # Quanti colori distinti porta il blocco, quantizzati a 32 livelli per
        # canale. Serve a non scambiare una lastra di separazione per
        # l'artwork: una campitura piatta di tinta e' colorata al 99% ma ha una
        # ventina di colori, mentre una grafica vera ne ha centinaia.
        q = reg[m] // 32 if m.any() else np.zeros((1, 3), int)
        colori = int(len(np.unique(q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2])))
        out.append(dict(
            x_mm=round(sl[1].start / s * PT2MM, 1), y_mm=round(sl[0].start / s * PT2MM, 1),
            w_mm=round(w, 1), h_mm=round(h, 1),
            colore_pct=round(100 * colore, 1), inchiostro_pct=round(100 * scuro, 1),
            colori_distinti=colori,
            # 83% di superficie colorata sulla vista stampata contro 13% su
            # quella tecnica: la soglia sta comoda in mezzo
            tipo="stampato" if colore > 0.35 else "tecnico"))
    # L'artwork e' il blocco piu' vario, non il piu' grande: su Kinder Country
    # le tre lastre di separazione sono piu' larghe della OUTSIDE VIEW e la
    # scaletta per ingombro metteva davanti la lastra del bianco.
    out.sort(key=lambda b: (b["tipo"] == "stampato", b["colori_distinti"],
                            b["w_mm"] * b["h_mm"]), reverse=True)
    # blocchi di pari ingombro sono viste dello stesso pack: quella tecnica
    # serve da maschera per quella stampata
    for b in out:
        gem = [c for c in out if c is not b
               and abs(c["w_mm"] - b["w_mm"]) < 8 and abs(c["h_mm"] - b["h_mm"]) < 8]
        if gem and b["tipo"] == "stampato" and any(c["tipo"] == "tecnico" for c in gem):
            t = [c for c in gem if c["tipo"] == "tecnico"][0]
            b["maschera_dt_x_mm"] = t["x_mm"]
    return dict(blocchi=out[:12],
                nota=("Scegli come area di lavoro il blocco 'stampato' che porta "
                      "l'artwork, non l'intera pagina. L'elenco parte da quello "
                      "piu' probabile: i blocchi stampati vengono per primi, "
                      "ordinati per colori_distinti, perche' una lastra di "
                      "separazione o un cartiglio sono colorati quanto una "
                      "grafica ma con pochi colori. I blocchi 'tecnico' con lo "
                      "stesso ingombro sono viste del disegno da usare come "
                      "maschera in clean_artwork."))


TOOLS.insert(1, dict(
    name="find_blocks",
    description="Elenca i blocchi della tavola con ingombro in mm, distinguendo "
                "quelli STAMPATI (con artwork) da quelli TECNICI (solo disegno). "
                "Da chiamare per PRIMA cosa: una tavola contiene quasi sempre piu' "
                "viste, e misurare sull'intera pagina da' quote senza senso. Il "
                "blocco tecnico di pari ingombro e' la maschera per clean_artwork.",
    input_schema={"type": "object", "properties": {}}))
_RAW["find_blocks"] = find_blocks
RUN = {k: (lambda f: lambda *a, **kw: _plain(f(*a, **kw)))(v) for k, v in _RAW.items()}
