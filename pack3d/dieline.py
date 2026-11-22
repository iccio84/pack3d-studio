"""
Analisi del disegno tecnico (fustella) contenuto in un artwork PDF.

Estrae la geometria vettoriale, isola il tratto della fustella, ricostruisce la
griglia di cordonature e i pannelli, classifica la tipologia di packaging e
ricava le quote L x H x P in millimetri.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import tempfile
import threading
from collections import OrderedDict
from dataclasses import dataclass, field, asdict

import pdfplumber

from . import stato

PT2MM = 25.4 / 72.0


# --------------------------------------------------------------------------- #
# strutture dati
# --------------------------------------------------------------------------- #
@dataclass
class Panel:
    """Un pannello della fustella, in punti PDF, y misurata dall'alto."""
    x0: float
    y0: float
    x1: float
    y1: float
    role: str = "unknown"

    @property
    def w_mm(self) -> float:
        return (self.x1 - self.x0) * PT2MM

    @property
    def h_mm(self) -> float:
        return (self.y1 - self.y0) * PT2MM

    def bbox(self):
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass
class Dieline:
    page_w: float
    page_h: float
    bbox: tuple
    xs: list = field(default_factory=list)
    ys: list = field(default_factory=list)
    panels: dict = field(default_factory=dict)
    kind: str = "unknown"
    layout: str = "unknown"      # "vwrap" (fasciatura verticale) | "hwrap"
    dims_mm: tuple = (0.0, 0.0, 0.0)
    vsegs: list = field(default_factory=list)   # (x, ytop, ybot) cordonature verticali
    hsegs: list = field(default_factory=list)   # (y, xleft, xright) cordonature orizzontali
    chiuso: bool = True          # un astuccio puo' non avere retro: vedi _aperto
    finestra_mm: float = 0.0     # quanto del retro resta aperto, in altezza
    fianchi_su: str = "back"     # la fascia a cui sono agganciati i fianchi
    # I fianchi dell'altra fascia alta, quando le portano tutte e due: quali
    # sono quelli che si vedono lo dice la stampa. Vedi `solve_carton`.
    fianchi_alt: dict = field(default_factory=dict)
    # Freccia in mm del fronte curvo di un astuccio a fasciatura orizzontale
    # (il "mastello"): 0 = fronte piatto. Vedi `_fronte_curvo`.
    curva_mm: float = 0.0
    # Il fondo a tetto, a soffietto dentro la scatola: (dove sta la cresta,
    # in mm dal fronte, quanto sale), o None per il fondo piatto. Vedi `_tetto`.
    tetto: tuple | None = None
    # Come e' stato letto l'astuccio (`letture_carton`, `pack3d.strade`): la
    # forma, la strada della fustella, le correzioni alle fasce, il costo con
    # le sue voci; `dubbio` dice la seconda lettura quando e' quasi alla pari.
    forma: str = ""
    strada: str = "colore"
    correzioni: tuple = ()
    costo: float = 0.0
    voci: dict = field(default_factory=dict)
    dubbio: str = ""

    def cols_in_row(self, y0, y1, cover=0.8):
        """Cordonature verticali che attraversano davvero la fascia [y0, y1]."""
        need = (y1 - y0) * cover
        out = []
        for x in self.xs:
            span = 0.0
            for cx, a, b in self.vsegs:
                if abs(cx - x) < 2.5:
                    span += max(0.0, min(b, y1) - max(a, y0))
            if span >= need:
                out.append(x)
        return out

    def row_extent(self, y0, y1, tol=3.5):
        """Estensione orizzontale reale della fascia, dai suoi tratti di taglio."""
        lo, hi = 1e9, -1e9
        for cy, a, b in self.hsegs:
            if abs(cy - y0) < tol or abs(cy - y1) < tol:
                lo, hi = min(lo, a), max(hi, b)
        return (lo, hi) if hi > lo else (self.bbox[0], self.bbox[2])

    def rows_in_col(self, x0, x1, cover=0.8, bordo=0.5):
        """Cordonature orizzontali che attraversano davvero la colonna.

        Il bordo libero del disegno (la prima e l'ultima riga del riquadro)
        basta che la copra per `bordo`: e' il bordo di una falda di chiusura,
        interrotto dalla linguetta e dagli angoli arrotondati."""
        out = []
        for y in self.ys:
            span = 0.0
            for cy, a, b in self.hsegs:
                if abs(cy - y) < 2.5:
                    span += max(0.0, min(b, x1) - max(a, x0))
            libero = min(abs(y - self.bbox[1]), abs(y - self.bbox[3])) < 2.5
            if span >= (x1 - x0) * (bordo if libero else cover):
                out.append(y)
        return out

    def to_dict(self):
        d = asdict(self)
        d["panels"] = {k: asdict(v) for k, v in self.panels.items()}
        return d


# --------------------------------------------------------------------------- #
# estrazione della geometria
# --------------------------------------------------------------------------- #
# L'ultima pagina rasterizzata: {(file, pagina): (scala, immagine)}. Una sola,
# perche' il server costruisce un modello alla volta.
_RESA = stato.per_lavoro({})


def render_page(pdf_path, page_no: int = 0, scale: float = 1.0, livello=None):
    """Rasterizza la pagina nel telaio del MediaBox, quello di pdfplumber.

    pdfium rende il CropBox, pdfplumber misura sul MediaBox. Finche' i due
    riquadri coincidono non si vede la differenza, e su quasi tutte le tavole
    coincidono. Quando no — sul wafer T1 il CropBox e' 459 x 271 pt dentro un
    MediaBox di 1332 x 958, spostato di (419, 471) — le coordinate dei segmenti
    indicizzano un raster che comincia da un'altra parte: nessuna eccezione,
    solo misure prese nel posto sbagliato.

    `livello` e' None per la pagina com'e' - quella che serve a misurare - o
    uno dei due livelli di `strati`: la texture si prende da
    `strati.GRAFICA`, cioe' con il disegno tecnico spento oggetto per oggetto.
    """
    import pypdfium2 as pdfium
    from PIL import Image

    # Una pagina, una rasterizzazione. Il flusso ne chiedeva TRE della stessa
    # pagina a risoluzioni diverse - 100 dpi per trovare il blocco stampato,
    # 150 per l'analisi, quella della texture per la grafica - e sul wafer da colazione
    # erano 30 secondi su 40 e tre picchi di memoria sovrapposti.
    #
    # Si tiene l'ultima resa e si SCENDE soltanto: una riduzione e' una media
    # di pixel che ci sono gia', un ingrandimento sarebbe invenzione. Se
    # qualcuno chiede piu' risoluzione di quella in cassa si rasterizza di
    # nuovo e si sostituisce.
    chiave = (pdf_path, page_no, livello)
    vecchia = _RESA.get(chiave)
    if vecchia is not None and vecchia[0] >= scale - 1e-9:
        avuta, im = vecchia
        if abs(avuta - scale) < 1e-9:
            return im
        larg = max(1, int(round(im.width * scale / avuta)))
        alt = max(1, int(round(im.height * scale / avuta)))
        return im.resize((larg, alt), Image.LANCZOS)

    if livello is None:
        # la resa nativa resta su disco per la prossima costruzione (`rese`)
        import time

        import numpy as np

        from . import rese
        k = rese.chiave("dieline.render_page", pdf_path, page_no, float(scale))
        v = rese.leggi(k)
        if v is not None:
            im = Image.fromarray(v[0])
        else:
            t = time.time()
            page = pdfium.PdfDocument(pdf_path)[page_no]
            page.set_cropbox(*page.get_mediabox())
            im = page.render(scale=scale).to_pil().convert("RGB")
            if time.time() - t >= rese.SOGLIA_S:
                rese.scrivi(k, np.asarray(im))
    else:
        from . import strati
        im = strati.rendi(pdf_path, page_no, scale, livello)
    # una sola pagina in cassa: il server costruisce un modello alla volta
    _RESA.clear()
    _RESA[chiave] = (scale, im)
    return im


def scarta_resa():
    """Butta la pagina rasterizzata tenuta in cassa.

    Va chiamata appena l'ultimo che la usa ha preso la sua copia: tenerla
    viva oltre costa quanto pesa (41 MB su un foglio come il wafer da colazione) proprio
    mentre la costruzione alloca la texture.
    """
    _RESA.clear()


# Pendenza fino alla quale un tratto conta come dritto: tan 3 gradi.
QUASI_DRITTO = 0.05


def _segments(page):
    """Segmenti H/V stroked della pagina: (orient, coord, a, b, stile)."""
    segs = []

    def add(x0, y0, x1, y1, style):
        # Quasi dritto conta come dritto: i lati di una falda di chiusura si
        # stringono di un grado o due verso la punta, perche' entri senza
        # strisciare (`QUASI_DRITTO`). Scartati, la falda restava fuori dal
        # disegno e la scatola senza fondo.
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        if dy > 1.0 and (dx < 0.7 or dx <= QUASI_DRITTO * dy):
            segs.append(("V", (x0 + x1) / 2, min(y0, y1), max(y0, y1), style))
        elif dx > 1.0 and (dy < 0.7 or dy <= QUASI_DRITTO * dx):
            segs.append(("H", (y0 + y1) / 2, min(x0, x1), max(x0, x1), style))

    def style_of(o):
        return (round(o.get("linewidth") or 0, 2), str(o.get("stroking_color")))

    def rettangolo(cv):
        """Se la curva e' un rettangolo dritto chiuso: quattro lati H/V che
        tornano al punto di partenza. Un `re` disegnato sotto una matrice
        girata pdfminer non lo riconosce come rettangolo, e lo da' come
        curva: sul T10 al lampone girato di mezzo giro le sei cornici
        dell'artwork, che il foglio dritto scarta qui sotto, entravano nella
        fustella come quattro tratti ciascuna, e l'astuccio non si
        risolveva piu'."""
        pts = [tuple(p) for p in cv.get("pts") or []]
        if len(pts) == 4:
            pts.append(pts[0])
        if len(pts) != 5 or max(abs(u - v) for u, v in zip(pts[0], pts[4])) > 0.5:
            return False
        return all(min(abs(a[0] - b[0]), abs(a[1] - b[1])) < 0.5
                   for a, b in zip(pts, pts[1:]))

    for ln in page.lines:
        add(ln["x0"], ln["top"], ln["x1"], ln["bottom"], style_of(ln))
    # i riquadri dell'artwork compaiono come coppia contorno+riempimento sullo
    # stesso bbox: un tratto di fustella non e' mai anche riempito. Anche
    # quando i rettangoli arrivano come curve (`rettangolo`).
    filled = [(r["x0"], r["top"], r["x1"], r["bottom"])
              for r in page.rects if r.get("fill")]
    filled += [(c["x0"], c["top"], c["x1"], c["bottom"])
               for c in page.curves if c.get("fill") and rettangolo(c)]

    def is_artwork_frame(rc):
        b = (rc["x0"], rc["top"], rc["x1"], rc["bottom"])
        return any(all(abs(u - v) < 1.0 for u, v in zip(b, f)) for f in filled)

    for rc in page.rects:
        if not rc.get("stroke") or is_artwork_frame(rc):
            continue
        st = style_of(rc)
        x0, x1, t, b = rc["x0"], rc["x1"], rc["top"], rc["bottom"]
        add(x0, t, x1, t, st); add(x0, b, x1, b, st)
        add(x0, t, x0, b, st); add(x1, t, x1, b, st)
    for cv in page.curves:
        if not cv.get("stroke") or (rettangolo(cv) and is_artwork_frame(cv)):
            continue
        st = style_of(cv)
        pts = cv.get("pts") or []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            add(ax, ay, bx, by, st)
    return segs


# --------------------------------------------------------------------------- #
# i tratti di una pagina, letti una volta per file
# --------------------------------------------------------------------------- #
# pdfplumber, per dare i tratti di una pagina, ne interpreta tutto il
# contenuto, grafica compresa: da mezzo secondo a sette per pagina. E la stessa
# pagina la chiedevano in tanti - `extract`, il riconoscimento di vassoi,
# sportelli e plance, la fustella della punta, il ripiego del flowpack - ognuno
# riaprendo il file: sul riempimento della T1 caramel cheesecake erano 47
# letture di due PDF in una costruzione, e /api/build le rifaceva tutte dopo
# /api/analyze. Ora si leggono una volta per file e per pagina: si tengono in
# memoria (`TRATTI_MAX`) e su disco (`CACHE`), dove li trova anche l'altro
# lavoratore e chi riparte dopo una caduta.
#
# La chiave e' il CONTENUTO del file, non il nome: un PDF caricato vive in un
# file temporaneo, e lo stesso nome torna con un altro foglio. E nella chiave
# del disco c'e' la versione di questo modulo, di pdfplumber e di pdfminer,
# perche' un disco tenuto fra due versioni del codice non dia i tratti letti
# da quella vecchia.
CACHE = os.environ.get("PACK3D_CACHE",
                       os.path.join(tempfile.gettempdir(), "pack3d-cache"))
CACHE_MB = float(os.environ.get("PACK3D_CACHE_MB", "256"))
TRATTI_MAX = 12


@dataclass(frozen=True)
class Tratti:
    """I tratti di una pagina, come li da' pdfplumber."""
    larghezza: float
    altezza: float
    segmenti: tuple     # quelli di `_segments`
    oggetti: tuple      # (tipo, stile, oggetto) dei tratti a penna, nell'ordine
                        # della pagina: line, poi rect, poi curve


_TRATTI = OrderedDict()
_TRATTI_CHIAVE = threading.Lock()
_IMPRONTE = {}


def _versione_tratti():
    import pdfminer
    h = hashlib.sha256()
    with open(__file__, "rb") as fh:
        h.update(fh.read())
    h.update(("%s %s" % (pdfplumber.__version__, pdfminer.__version__)).encode())
    return h.hexdigest()[:12]


_VERSIONE_TRATTI = _versione_tratti()


def impronta_file(path):
    """sha256 del contenuto di `path`, ricordata finche' il file non cambia."""
    st = os.stat(path)
    chiave = (os.path.abspath(path), st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino)
    imp = _IMPRONTE.get(chiave)
    if imp is None:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for blocco in iter(lambda: fh.read(1 << 20), b""):
                h.update(blocco)
        imp = h.hexdigest()
        if len(_IMPRONTE) > 256:
            _IMPRONTE.clear()
        _IMPRONTE[chiave] = imp
    return imp


def _leggi_tratti(pdf_path, page_no):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_no]
        segs = _segments(page)
        oggetti = []
        for kind in ("line", "rect", "curve"):
            for o in page.objects.get(kind, []):
                if not o.get("stroke"):
                    continue
                st = (round(o.get("linewidth") or 0, 2), str(o.get("stroking_color")))
                oggetti.append((kind, st, {k: o[k] for k in ("x0", "top", "x1", "bottom",
                                                              "path", "pts") if k in o}))
        return Tratti(page.width, page.height, tuple(segs), tuple(oggetti))


def _file_tratti(chiave):
    return os.path.join(CACHE, "tratti-%s-%s-%d.json.gz" % ((_VERSIONE_TRATTI,) + chiave))


def _dal_disco(chiave):
    if not CACHE or CACHE == "0":
        return None
    f = _file_tratti(chiave)
    try:
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError, EOFError):
        return None
    try:
        os.utime(f)         # i piu' usati restano quando la cartella si sfoltisce
    except OSError:
        pass
    # JSON fa delle tuple liste: lo stile torna tupla, perche' si confronta
    # con quelli tenuti in un set
    return Tratti(d["larghezza"], d["altezza"],
                  tuple((k, c, a, b, tuple(st)) for k, c, a, b, st in d["segmenti"]),
                  tuple((k, tuple(st), o) for k, st, o in d["oggetti"]))


def _sul_disco(chiave, t):
    """Scrive i tratti su disco, e se la cartella passa `CACHE_MB` butta i
    piu' vecchi. Un disco che non si scrive non ferma niente."""
    if not CACHE or CACHE == "0":
        return
    try:
        os.makedirs(CACHE, mode=0o700, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=CACHE, suffix=".tmp")
        with os.fdopen(fd, "wb") as grezzo, gzip.open(grezzo, "wt", encoding="utf-8",
                                                      compresslevel=3) as fh:
            json.dump({"larghezza": t.larghezza, "altezza": t.altezza,
                       "segmenti": t.segmenti, "oggetti": t.oggetti}, fh,
                      separators=(",", ":"))
        # chi legge trova il file vecchio o quello intero, mai uno a meta'
        os.replace(tmp, _file_tratti(chiave))
        voci = []
        for nome in os.listdir(CACHE):
            try:
                s = os.stat(os.path.join(CACHE, nome))
            except OSError:
                continue
            # le cartelle sono d'altri: le rese (`rese`) hanno il loro tetto
            if os.path.isfile(os.path.join(CACHE, nome)):
                voci.append((s.st_mtime, s.st_size, nome))
        tot = sum(v[1] for v in voci)
        for _t, n, nome in sorted(voci):
            if tot <= CACHE_MB * 1024 * 1024:
                break
            try:
                os.remove(os.path.join(CACHE, nome))
                tot -= n
            except OSError:
                pass
    except OSError as e:
        print("cache dei tratti non scritta: %s" % e, file=sys.stderr)


def tratti(pdf_path, page_no: int = 0) -> Tratti:
    """I tratti della pagina, letti una volta per file e per pagina."""
    chiave = (impronta_file(pdf_path), page_no)
    with _TRATTI_CHIAVE:
        t = _TRATTI.get(chiave)
        if t is not None:
            _TRATTI.move_to_end(chiave)
            return t
    t = _dal_disco(chiave)
    if t is None:
        t = _leggi_tratti(pdf_path, page_no)
        _sul_disco(chiave, t)
    with _TRATTI_CHIAVE:
        _TRATTI[chiave] = t
        while len(_TRATTI) > TRATTI_MAX:
            _TRATTI.popitem(last=False)
    return t


def segmenti(pdf_path, page_no: int = 0):
    """`_segments` della pagina, letti una volta sola (`tratti`)."""
    return list(tratti(pdf_path, page_no).segmenti)


def _technical_pens(segs, page_w, page_h, min_segs=4, keep=0.15):
    """Le penne del disegno tecnico.

    Molti artwork separano taglio, cordonatura e mezzo-taglio su colori
    diversi: una penna sola non basta. Teniamo tutti i tratti sottili che
    contribuiscono abbastanza linee lunghe."""
    length, count = {}, {}
    lim = 0.05 * max(page_w, page_h)
    for kind, c, a, b, st in segs:
        if b - a < lim or st[0] > 1.2:
            continue
        length[st] = length.get(st, 0.0) + (b - a)
        count[st] = count.get(st, 0) + 1
    if not length:
        return set()
    top = max(length.values())
    return {st for st in length
            if count[st] >= min_segs and length[st] >= keep * top}


# Quanto lontano dal corpo della fustella puo' stare un pezzo e appartenerle
# ancora, in punti. Un'aletta la tocca; un cartiglio sta molto piu' in la'.
ATTACCATO = 50.0


def _gruppi(segs, gap=25.0):
    """I gruppi di segmenti spazialmente connessi: `[[(segmento, riquadro)]]`.

    Due segmenti stanno nello stesso gruppo se i loro riquadri distano meno
    di `gap` punti. Un DT e le sue copie tecniche, la legenda, il cartiglio
    e le miniature vengono fuori come gruppi separati.
    """
    if not segs:
        return []
    boxes = []
    for kind, c, a, b, st in segs:
        boxes.append((c - 1, a, c + 1, b) if kind == "V" else (a, c - 1, b, c + 1))
    parent = list(range(len(boxes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def near(p, q):
        return not (p[2] + gap < q[0] or q[2] + gap < p[0] or
                    p[3] + gap < q[1] or q[3] + gap < p[1])

    order = sorted(range(len(boxes)), key=lambda i: boxes[i][0])
    for ii, i in enumerate(order):
        for j in order[ii + 1:]:
            if boxes[j][0] > boxes[i][2] + gap:
                break
            if near(boxes[i], boxes[j]):
                a_, b_ = find(i), find(j)
                if a_ != b_:
                    parent[a_] = b_
    groups = {}
    for i, sg in enumerate(segs):
        groups.setdefault(find(i), []).append((sg, boxes[i]))
    return list(groups.values())


# Un secondo disegno lungo almeno cosi' e' l'altra vista della stessa
# fustella (OUTSIDE / INSIDE): come `prisma.DOPPIO`.
ALTRA_VISTA = 0.8


def _senza_quote(segs, numeri):
    """`segs` senza le linee di quota e i loro richiami.

    Una quota porta scritto accanto il numero della sua lunghezza
    (`flowpack._quote_estese`, la linea piu' vicina fra quelle lunghe
    quanto lui). I richiami sono i tratti perpendicolari che passano per i
    suoi capi. Vedi `_largest_cluster`."""
    from .flowpack import _quote_estese
    quote = _quote_estese(segs, numeri)
    if not quote:
        return segs
    tol = 3.0

    def di_quota(s):
        k, c, a, b, st = s
        for (kq, cq), (_v, qa, qb) in quote.items():
            if k == kq and abs(c - cq) <= tol and a >= qa - tol and b <= qb + tol:
                return True
            # un richiamo: perpendicolare, su un capo, attraversa la quota
            if (k != kq and min(abs(c - qa), abs(c - qb)) <= tol
                    and a - tol <= cq <= b + tol):
                return True
        return False
    return [s for s in segs if not di_quota(s)]


# Quanto puo' essere lungo un richiamo di una quota fuori dal disegno, oltre
# la distanza fra il disegno e la quota, in mm: un richiamo parte vicino al
# disegno e passa la quota di poco. Una linea del disegno che arriva fin li'
# e' molto piu' lunga.
RICHIAMO_OLTRE_MM = 6.0


def _quote_fuori(segs, numeri, tol=3.0):
    """Gli indici, in `segs`, delle linee di quota che stanno fuori dal
    disegno e dei loro richiami.

    Una quota disegnata nella penna della fustella, coi richiami a un
    millimetro dagli angoli, finisce nel gruppo della fustella stessa: e
    `_senza_quote` pulisce solo gli altri gruppi. Le sue righe diventavano
    pieghe del foglio: sulla scatola a punta T6 con le quote del passo e del
    giro la riga della quota sotto lo steso era l'ultima fascia, il retro
    non era piu' alto come il fronte e la scatola non si riconosceva. Una
    quota si toglie se, tolte lei e le altre quote, sta fuori dal riquadro
    del resto del disegno: dentro, una piega con la sua misura scritta
    accanto resta piega. Dei richiami si tolgono quelli corti, che dal
    disegno arrivano alla quota (`RICHIAMO_OLTRE_MM`)."""
    from .flowpack import _quote_estese
    quote = _quote_estese(segs, numeri)
    if not quote:
        return set()

    def linea(s, kq, cq, qa, qb):
        k, c, a, b, _st = s
        return k == kq and abs(c - cq) <= tol and a >= qa - tol and b <= qb + tol

    def richiamo(s, kq, cq, qa, qb):
        k, c, a, b, _st = s
        return (k != kq and min(abs(c - qa), abs(c - qb)) <= tol
                and a - tol <= cq <= b + tol)
    di_quote = {i for i, s in enumerate(segs)
                if any(linea(s, kq, cq, qa, qb) or richiamo(s, kq, cq, qa, qb)
                       for (kq, cq), (_v, qa, qb) in quote.items())}
    resto = [s for i, s in enumerate(segs) if i not in di_quote]
    if not resto:
        return set()
    xs = [v for k, c, a, b, _st in resto for v in ((c,) if k == "V" else (a, b))]
    ys = [v for k, c, a, b, _st in resto for v in ((c,) if k == "H" else (a, b))]
    via = set()
    for (kq, cq), (_v, qa, qb) in quote.items():
        lo, hi = (min(ys), max(ys)) if kq == "H" else (min(xs), max(xs))
        if lo - tol <= cq <= hi + tol:
            continue
        lontano = lo - cq if cq < lo else cq - hi
        for i, s in enumerate(segs):
            if linea(s, kq, cq, qa, qb):
                via.add(i)
            elif (richiamo(s, kq, cq, qa, qb)
                  and s[3] - s[2] <= lontano + RICHIAMO_OLTRE_MM / PT2MM):
                via.add(i)
    return via


# Quanto e' lungo al piu' un segno di stampa, in mm: i crocini di taglio e i
# bracci dei crocini di registro sono di pochi millimetri. Una linea della
# fustella con tutti e due i capi liberi e fuori dal resto del disegno - il
# lato in cima di un'aletta coi fianchi obliqui, che i tratti dritti non
# vedono attaccata - e' piu' lunga.
SEGNO_MAX_MM = 12.0


def _segni_fuori(segs, tol=3.0, riquadro=None):
    """Gli indici, in `segs`, dei segni di stampa attaccati alla fustella.

    I crocini di taglio e di registro, nella penna del taglio come li mette il
    CAD della fustella, stanno a tre millimetri dalla stampa: finiscono nel
    gruppo della fustella, e il suo riquadro si allargava fino a loro. I suoi
    lati diventavano pieghe: sul display a vassoio T1x40 la griglia aveva
    cinque fasce invece di tre. Un segno e' corto (`SEGNO_MAX_MM`), ha tutti
    e due i capi liberi - non tocca nessun altro tratto - e sta tutto fuori
    dal riquadro del resto del disegno. Una linea della fustella e' attaccata
    al disegno almeno da un capo, o ci sta dentro.

    Un segno puo' essere fatto di piu' tratti corti che si toccano fra loro:
    il crocino di registro ha i due bracci incrociati, e ognuno toccava
    l'altro - nessuno dei due era libero, e restavano nella fustella.
    Sul coperchio del display T1x36 coi segni di stampa i crocini sotto lo
    steso tiravano dentro anche la quota della larghezza, e la parete sud
    veniva 182 mm invece di 146 (`prove/parco.py varianti`, 15 novembre
    2026). Allora conta il GRUPPO: tratti corti che si toccano solo fra loro,
    non piu' grandi tutti insieme di `SEGNO_MAX_MM`, e nessuno attaccato a un
    tratto lungo.

    Con `riquadro` (x0, y0, x1, y1) il segno deve stare fuori da lui invece
    che dal riquadro del resto dei tratti dati."""
    import numpy as np
    n = len(segs)
    if n < 2:
        return set()
    A = np.array([(a, c, b, c) if k == "H" else (c, a, c, b)
                  for k, c, a, b, _st in segs], float)
    xa, xb = np.minimum(A[:, 0], A[:, 2]), np.maximum(A[:, 0], A[:, 2])
    ya, yb = np.minimum(A[:, 1], A[:, 3]), np.maximum(A[:, 1], A[:, 3])
    corti = np.hypot(A[:, 2] - A[:, 0], A[:, 3] - A[:, 1]) <= SEGNO_MAX_MM / PT2MM
    if not corti.any():
        return set()

    lunghi = ~corti

    def attaccato(i, px, py, a_chi):
        d = np.hypot(px - np.clip(px, xa, xb), py - np.clip(py, ya, yb))
        d[i] = np.inf
        return bool((d[a_chi] <= tol).any())
    # i gruppi di tratti corti che si toccano (i riquadri a `tol`)
    ic = [int(i) for i in np.flatnonzero(corti)]
    padre = {i: i for i in ic}

    def radice(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i
    for k, i in enumerate(ic):
        for j in ic[k + 1:]:
            if (xa[j] <= xb[i] + tol and xa[i] <= xb[j] + tol
                    and ya[j] <= yb[i] + tol and ya[i] <= yb[j] + tol):
                padre[radice(i)] = radice(j)
    gruppi = {}
    for i in ic:
        gruppi.setdefault(radice(i), []).append(i)
    liberi = []
    lato = SEGNO_MAX_MM / PT2MM
    for g in gruppi.values():
        if (xb[g].max() - xa[g].min() > lato + 1e-6
                or yb[g].max() - ya[g].min() > lato + 1e-6):
            continue
        if any(attaccato(i, A[i, 0], A[i, 1], lunghi)
               or attaccato(i, A[i, 2], A[i, 3], lunghi) for i in g):
            continue
        liberi.extend(g)
    if not liberi:
        return set()
    if riquadro is not None:
        x0, y0, x1, y1 = riquadro
        x0, y0, x1, y1 = x0 - tol, y0 - tol, x1 + tol, y1 + tol
    else:
        resto = np.ones(n, bool)
        resto[liberi] = False
        if not resto.any():
            return set()
        x0, x1 = xa[resto].min() - tol, xb[resto].max() + tol
        y0, y1 = ya[resto].min() - tol, yb[resto].max() + tol
    return {int(i) for i in liberi
            if xb[i] < x0 or xa[i] > x1 or yb[i] < y0 or ya[i] > y1}


# Quante lettere fanno una legenda: "LEGENDA", "taglio", "cordonatura" ne
# hanno molte di piu'; una sigla sola su un'aletta non arriva qui
LEGENDA_LETTERE = 4


def lettere(pdf_path, page_no=0):
    """I centri dei caratteri di testo vivo della pagina, in punti, nel telaio
    dei tratti (x da sinistra, y dall'alto): un array `(n, 2)`."""
    import numpy as np
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[page_no]
        mx0, _my0, _mx1, my1 = page.get_mediabox()
        tp = page.get_textpage()
        out = []
        for i in range(tp.count_chars()):
            try:
                l, b, r, t = tp.get_charbox(i)
            except Exception:
                continue
            if r - l <= 0 and t - b <= 0:
                continue
            out.append(((l + r) / 2.0 - mx0, my1 - (b + t) / 2.0))
        tp.close()
    finally:
        doc.close()
    return np.array(out, float).reshape(-1, 2)


def _dentro_il_riquadro(s, kf, a, b, lo_n, hi_n, tol):
    """Se il tratto `s` sta dentro il riquadro (a, b lungo la linea lontana
    `kf`, lo_n, hi_n attraverso), lontano almeno `tol` dai suoi lati."""
    k, c, sa, sb, _st = s
    if k == kf:
        return lo_n + tol < c < hi_n - tol and sb > a + tol and sa < b - tol
    return a + tol < c < b - tol and sb > lo_n + tol and sa < hi_n - tol


def _attaccato_oltre(s, kf, c, a, b, sg, tol):
    """Se il tratto `s` parte dalla linea lontana (quota `c`, da `a` a `b`,
    nel verso `kf`) e va oltre, dalla parte `sg`."""
    k, sc, sa, sb, _st = s
    if k == kf:
        return False
    if not a - tol <= sc <= b + tol:
        return False
    vicino, lontano = (sa, sb) if sg > 0 else (sb, sa)
    return abs(vicino - c) <= tol and (lontano - c) * sg > tol


def _legenda_attaccata(segs, lettere, gap=25.0, tol=3.0):
    """Gli indici, in `segs`, del riquadro di una legenda attaccato a un lato
    della fustella, o un insieme vuoto.

    Una legenda disegnata nella penna del taglio e appoggiata al bordo dello
    steso - due lati che partono dal bordo e il fondo che li chiude, con le
    scritte dentro - e' nel gruppo della fustella: il suo fondo diventava una
    riga della griglia. Sul coperchio del display T1x36 la parete sud veniva
    182 mm invece di 146, e la legenda tirava dentro anche la quota della
    larghezza disegnata sotto (`prove/parco.py varianti`, 15 novembre 2026).

    Il riquadro si riconosce cosi': una linea lontana, due tratti
    perpendicolari che partono dai suoi capi e arrivano allo stesso punto
    verso il disegno, almeno `LEGENDA_LETTERE` caratteri di testo vivo dentro,
    e tolti quei tre tratti il gruppo piu' lungo che resta non va oltre il
    punto di partenza dei lati. E dentro non c'e' nessun altro tratto, e
    oltre la linea lontana non e' attaccato niente: il pannello del fronte
    di un astuccio, con le scritte della grafica, la sua finestra dentro e
    l'aletta del cielo attaccata oltre, non e' una legenda - senza queste due
    condizioni l'astuccio T8 del parco non si risolveva piu'."""
    import numpy as np
    n = len(segs)
    if n < 4 or lettere is None or not len(lettere):
        return set()
    lettere = np.asarray(lettere, float)
    for kf, ks, sg in (("H", "V", 1), ("H", "V", -1), ("V", "H", 1), ("V", "H", -1)):
        lati = [j for j in range(n) if segs[j][0] == ks]
        for i in range(n):
            k, c, a, b, _st = segs[i]
            if k != kf:
                continue

            def lato(x):
                for j in lati:
                    _kj, cj, aj, bj, _sj = segs[j]
                    lontano, vicino = (bj, aj) if sg > 0 else (aj, bj)
                    if (abs(cj - x) <= tol and abs(lontano - c) <= tol
                            and (c - vicino) * sg > 5 * tol):
                        return j, vicino
                return None
            l1, l2 = lato(a), lato(b)
            if not l1 or not l2 or l1[0] == l2[0] or abs(l1[1] - l2[1]) > tol:
                continue
            vicino = (l1[1] + l2[1]) / 2.0
            lo_n, hi_n = sorted((vicino, c))
            riquadro = {i, l1[0], l2[0]}
            # dentro non c'e' disegno: un pannello della fustella ha le sue
            # righe (una finestra, una cordonatura), la legenda solo scritte
            if any(_dentro_il_riquadro(segs[j], kf, a, b, lo_n, hi_n, tol)
                   for j in range(n) if j not in riquadro):
                continue
            # e oltre la linea lontana non c'e' niente attaccato: al pannello
            # del fronte di un astuccio e' attaccata l'aletta del cielo
            if any(_attaccato_oltre(segs[j], kf, c, a, b, sg, tol)
                   for j in range(n) if j not in riquadro):
                continue
            if kf == "H":
                X, Y = lettere[:, 0], lettere[:, 1]
            else:
                X, Y = lettere[:, 1], lettere[:, 0]
            dentro = int(((X >= a) & (X <= b) & (Y >= lo_n) & (Y <= hi_n)).sum())
            if dentro < LEGENDA_LETTERE:
                continue
            resto = [segs[j] for j in range(n) if j not in riquadro]
            gruppi = _gruppi(resto, gap)
            if not gruppi:
                continue
            g = max(gruppi, key=lambda g: sum(x[0][3] - x[0][2] for x in g))
            estremi = [(cj, cj) if kj == kf else (aj, bj)
                       for (kj, cj, aj, bj, _sj), _b in g]
            oltre = (max(e[1] for e in estremi) if sg > 0
                     else min(e[0] for e in estremi))
            if (oltre - vicino) * sg <= tol:
                return riquadro
    return set()


def _largest_cluster(segs, gap=25.0, dettaglio=None, numeri=(), lettere=None):
    """Isola il gruppo di segmenti spazialmente connesso piu' esteso: scarta
    cartigli, legende e disegni di riepilogo posti a lato della fustella.

    Con `dettaglio(riquadro) -> float`: se un altro gruppo e' lungo almeno
    `ALTRA_VISTA` del piu' lungo, sono la vista di fuori e quella di dentro
    affiancate, e si tiene quella con piu' grafica sotto. La vista di dentro
    ha spesso PIU' tratti (i contorni delle zone segnaposto, nella stessa
    penna) ed e' piu' lunga: per lunghezza vinceva lei.

    Due viste stanno una accanto all'altra, mai una dentro l'altra: un gruppo
    che racchiude il piu' lungo e' la cornice della tavola, non l'altra
    vista. Sul display a vassoio T1x40 con una cornice a dieci millimetri,
    nella penna del taglio, la cornice era lunga l'80,04% della fustella:
    passava per l'altra vista, aveva piu' grafica sotto - tutta - e la
    griglia prendeva i suoi lati per pieghe."""
    if not segs:
        return segs
    groups = {id(g): g for g in _gruppi(segs, gap)}

    def lung(g):
        return sum(x[0][3] - x[0][2] for x in g)

    def riq(g):
        return (min(b[0] for _, b in g), min(b[1] for _, b in g),
                max(b[2] for _, b in g), max(b[3] for _, b in g))

    def racchiude(g, h, t=4.0):
        r, q = riq(g), riq(h)
        return (r[0] <= q[0] + t and r[1] <= q[1] + t
                and r[2] >= q[2] - t and r[3] >= q[3] - t)
    main = max(groups.values(), key=lung)
    if dettaglio is not None:
        viste = [g for g in groups.values() if lung(g) >= ALTRA_VISTA * lung(main)
                 and (g is main or not racchiude(g, main))]
        if len(viste) > 1:
            main = max(viste, key=lambda g: dettaglio(riq(g)))
    principale = main
    if numeri:
        # le quote attaccate alla fustella, fuori dal disegno (`_quote_fuori`)
        via = _quote_fuori([sg for sg, _ in main], numeri)
        if via:
            main = [x for i, x in enumerate(main) if i not in via]
    # i segni di stampa attaccati alla fustella (`_segni_fuori`)
    via = _segni_fuori([sg for sg, _ in main])
    if via:
        main = [x for i, x in enumerate(main) if i not in via]
    # la legenda attaccata a un lato (`_legenda_attaccata`): tolta lei, quello
    # che teneva attaccato al gruppo - una quota sotto - torna un gruppo a se',
    # e lo giudica `inside` come gli altri
    staccati = []
    via = _legenda_attaccata([sg for sg, _ in main], lettere, gap)
    if via:
        resto = [sg for i, (sg, _) in enumerate(main) if i not in via]
        parti = _gruppi(resto, gap)
        main = max(parti, key=lung)
        staccati = [g for g in parti if g is not main]
    mx0 = min(b[0] for _, b in main); my0 = min(b[1] for _, b in main)
    mx1 = max(b[2] for _, b in main); my1 = max(b[3] for _, b in main)

    def inside(g):
        """Se questo gruppo fa parte della fustella o e' roba di fianco.

        Le alette con fianchi obliqui non toccano il corpo con tratti H/V:
        restano gruppi a se', sporgono dall'ingombro da un lato e sono
        contenute nell'altro. Per quelle il test su un asse solo va bene.

        Contenuto in un asse pero' NON basta, ed e' quello che rompeva gli
        astucci con due viste sul foglio. Sul T6 aperto la pagina porta
        INSIDE VIEW e OUTSIDE VIEW affiancate piu' il cartiglio: il cartiglio
        sta 90 mm a destra della fustella, non la tocca in nessun punto, ma e'
        contenuto nella sua ALTEZZA - e tanto bastava a tirarlo dentro. Il
        riquadro usciva 679 mm invece di 262, la griglia di colonne veniva
        assurda e solve_carton non trovava piu' i fianchi: KeyError 'left'.

        Quindi: contenuto in un asse E attaccato al corpo nell'altro. Un'aletta
        e' attaccata per definizione, un cartiglio a 90 mm no.
        """
        x0 = min(b[0] for _, b in g); y0 = min(b[1] for _, b in g)
        x1 = max(b[2] for _, b in g); y1 = max(b[3] for _, b in g)
        t = 4.0
        dentro_x = mx0 - t <= x0 and x1 <= mx1 + t
        dentro_y = my0 - t <= y0 and y1 <= my1 + t
        attaccato_x = x0 <= mx1 + ATTACCATO and x1 >= mx0 - ATTACCATO
        attaccato_y = y0 <= my1 + ATTACCATO and y1 >= my0 - ATTACCATO
        return ((dentro_x and attaccato_y) or (dentro_y and attaccato_x))

    # Fuori dal corpo le quote non sono fustella. Una quota lunga quanto la
    # fustella, coi richiami a un millimetro dagli angoli, univa le alette a
    # fianchi obliqui - gruppi a se' - in un gruppo piu' largo del corpo su
    # tutti e due gli assi, che `inside` non teneva piu': sul T3 di biscotti
    # con le quote il fronte curvo, che si riconosce dalle alette, spariva.
    # Le linee del corpo non si toccano: una piega con la sua misura scritta
    # accanto resta piega.
    altri = [g for g in groups.values() if g is not principale] + staccati
    if numeri and altri:
        resto = _senza_quote([sg for g in altri for sg, _ in g], numeri)
        altri = _gruppi(resto, gap)
    # I segni di stampa fuori dal corpo, prima di raggrupparli: un crocino di
    # registro sotto lo steso faceva da ponte fra il corpo e la quota della
    # larghezza, piu' in la', e `inside` tirava dentro tutte e due
    # (`_segni_fuori` col riquadro del corpo).
    if altri:
        corpo = [sg for sg, _ in main]
        fuori = [sg for g in altri for sg, _ in g]
        via = _segni_fuori(corpo + fuori, riquadro=(mx0, my0, mx1, my1))
        via = {i - len(corpo) for i in via if i >= len(corpo)}
        if via:
            altri = _gruppi([sg for i, sg in enumerate(fuori) if i not in via], gap)
    out = [sg for sg, _ in main]
    for g in altri:
        if inside(g):
            out.extend(sg for sg, _ in g)
    # i segni di stampa che `inside` rimette dentro: un crocino accanto a un
    # lato e' contenuto in un asse e attaccato nell'altro, come un'aletta
    via = _segni_fuori(out)
    if via:
        out = [sg for i, sg in enumerate(out) if i not in via]
    return out


# Quanto deve valere una penna, in frazione della migliore, per contare come
# fustella. Misurato: su tutti gli artwork del parco la penna di fustella e'
# una sola e sta a 1,00; sul T6 aperto ce n'e' una seconda a 0,14 - un
# rettangolo nero CMYK da 0,76 pt, quattro segmenti in tutto, che non e'
# fustella e sballava la griglia. Il divario e' largo e la soglia sta in mezzo.
FUSTELLA_KEEP = float(os.environ.get("PACK3D_FUSTELLA_KEEP", "0.25"))


def _punteggi_penna(segs, page_w, page_h):
    """Quanto ogni penna "sa" di fustella: {penna: punteggio}.

    Non basta la lunghezza. Una fustella ha molte **cordonature distinte**,
    non solo tratto lungo, quindi la lunghezza si pesa per il numero di quote
    di piega riconoscibili. E' quello che distingue una fustella da un
    rettangolo grande disegnato con un filo sottile.
    """
    length, coords = {}, {}
    lim = 0.05 * max(page_w, page_h)
    for kind, c, a, b, st in segs:
        if b - a < lim:
            continue
        length[st] = length.get(st, 0.0) + (b - a)
        coords.setdefault(st, {"H": [], "V": []})[kind].append(c)
    fuori = {}
    for st, L in length.items():
        n = sum(len(_cluster([(v, 1.0) for v in coords[st][k]])) for k in ("H", "V"))
        fuori[st] = L * max(n, 1)
    return fuori


def penne_di_fustella(segs, page_w, page_h, keep=None):
    """Le penne che disegnano la fustella, fra quelle tecniche.

    `_technical_pens` tiene tutti i tratti sottili che contribuiscono linee
    lunghe, e fa bene: molti artwork separano taglio, cordonatura e mezzo
    taglio su colori diversi, e una penna sola non basterebbe. Ma la' dentro
    finisce anche chi non e' fustella affatto, e per la GRIGLIA - le righe e
    le colonne da cui si ricavano i pannelli - un intruso e' fatale: una sola
    riga in piu' e i ruoli cadono tutti sul pannello sbagliato.

    Una penna di cordonatura vera passa la soglia perche' porta molti tratti
    su molte quote. Un rettangolo solo non la passa.
    """
    p = _punteggi_penna(segs, page_w, page_h)
    if not p:
        return set()
    top = max(p.values())
    lim = FUSTELLA_KEEP if keep is None else keep
    return {st for st, v in p.items() if v >= lim * top}


def _dieline_pen(segs, page_w, page_h):
    """La penna che sa di fustella piu' di tutte, o None."""
    p = _punteggi_penna(segs, page_w, page_h)
    return max(p, key=p.get) if p else None


def _cluster(vals, tol=2.0):
    out = []
    for v, w in sorted(vals):
        if out and abs(v - out[-1][0]) <= tol:
            c, ww = out[-1]
            out[-1] = ((c * ww + v * w) / (ww + w), ww + w)
        else:
            out.append((v, w))
    return out


def _outline_bbox(page, segs):
    """Contorno esterno della fustella: il rettangolo stroked di area massima,
    altrimenti l'estensione dei segmenti."""
    best, area = None, 0.0
    for rc in page.rects:
        if not rc.get("stroke"):
            continue
        a = (rc["x1"] - rc["x0"]) * (rc["bottom"] - rc["top"])
        if a > area:
            area, best = a, (rc["x0"], rc["top"], rc["x1"], rc["bottom"])
    if best is not None:
        return best
    xs = [c for k, c, a, b, st in segs if k == "V"]
    ys = [c for k, c, a, b, st in segs if k == "H"]
    return (min(xs), min(ys), max(xs), max(ys))


def _colori(pdf_path, riq, page_no=0, dpi=50.0):
    """Quanta grafica c'e' sotto un riquadro in punti: i colori distinti non
    bianchi, contati come in `tools.dt_della_tavola`. Una vista di dentro o
    una copia tecnica e' bianca con qualche campitura piatta."""
    import numpy as np
    try:
        im = np.asarray(render_page(pdf_path, page_no, dpi / 72.0)
                        .convert("RGB")).astype(np.int16)
    except Exception:
        return 0
    s = dpi / 72.0
    reg = im[max(0, int(riq[1] * s)):int(riq[3] * s) + 1,
             max(0, int(riq[0] * s)):int(riq[2] * s) + 1]
    m = reg.max(2) < 248 if reg.size else None
    if m is None or not m.any():
        return 0
    q = reg[m] // 32
    return int(len(np.unique(q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2])))


# Una linea tratteggiata, per contare come una piega sola: almeno tanti
# trattini, tutti lunghi uguali (a meno di TRATTINO_UGUALE), ciascuno lungo
# almeno TRATTINO_MIN_MM e almeno TRATTINO_SU_SALTO volte il salto, e i salti
# veri (non tratti contigui) e uguali. Una perforazione - denti da 2,5 mm con
# salti da 1,5 - non lo e', e nemmeno una linea spezzata in pezzi contigui.
TRATTINI_MIN = 3
TRATTINO_MIN_MM = 8.0
TRATTINO_SU_SALTO = 5.0
TRATTINO_UGUALE = 0.1
SALTO_MIN_MM = 0.5


def _tratteggio(pezzi, salto_mm):
    """Se i pezzi `[(a, b)]`, ordinati, sono i trattini di una linea
    tratteggiata regolare (vedi `TRATTINI_MIN` e seguenti)."""
    if len(pezzi) < TRATTINI_MIN:
        return False
    lunghi = [(b - a) * PT2MM for a, b in pezzi]
    salti = [(pezzi[i + 1][0] - pezzi[i][1]) * PT2MM for i in range(len(pezzi) - 1)]
    # i due capi possono essere mozzati dal bordo della fascia
    interni = lunghi[1:-1] or lunghi
    lt = max(interni)
    return (min(interni) >= (1 - TRATTINO_UGUALE) * lt
            and lt >= TRATTINO_MIN_MM
            and max(lunghi) <= (1 + TRATTINO_UGUALE) * lt
            and min(salti) >= SALTO_MIN_MM and max(salti) <= salto_mm
            and max(salti) - min(salti) <= 0.5
            and lt >= TRATTINO_SU_SALTO * max(salti))


def _tratteggi_uniti(segs, salto_mm=3.0):
    """I tratti allineati di una linea tratteggiata, uniti in un tratto solo.

    Una cordonatura disegnata a trattini e' una piega come una continua: sul
    display T2x25 i trattini erano da 20 mm su una fascia larga 271, sotto il
    5% del foglio, e le due pieghe del retro non entravano nelle righe: retro
    e cielo si leggevano come una fascia sola da 194 mm. Qui si uniscono i
    trattini della stessa penna, sulla stessa retta, con un salto fino a
    `salto_mm`, solo se sono un tratteggio regolare (`_tratteggio`): una
    perforazione o una linea spezzata in pezzi contigui restano com'erano, e
    gli altri casi del parco si leggono come prima. Solo per misurare la
    lunghezza delle righe, i segmenti restano quelli del disegno."""
    salto = salto_mm / PT2MM
    gruppi = {}
    for kind, c, a, b, st in segs:
        gruppi.setdefault((kind, round(c * 2) / 2, st), []).append((a, b, c))
    out = []
    for (kind, _, st), tr in gruppi.items():
        tr.sort()
        corse = [[tr[0]]]
        for t in tr[1:]:
            if t[0] - max(x[1] for x in corse[-1]) <= salto:
                corse[-1].append(t)
            else:
                corse.append([t])
        for corsa in corse:
            if _tratteggio([(a, b) for a, b, _c in corsa], salto_mm):
                out.append((kind, corsa[0][2], corsa[0][0],
                            max(b for _a, b, _c in corsa), st))
            else:
                out.extend((kind, c, a, b, st) for a, b, c in corsa)
    return out


# Una catena di quote sulla stessa retta - fianco, corpo, fianco - e' spezzata
# dai suoi numeri, scritti sulla linea: fra un pezzo e l'altro al piu' tanto,
# in mm.
QUOTA_SALTO_MM = 25.0
# Una penna e' di quote se almeno questa frazione della sua lunghezza sono
# linee di quota e richiami (`_penne_di_quote`).
PENNA_DI_QUOTE = 0.8
# Quanto vicino a una linea deve finire un tratto per toccarla, in mm.
TOCCA_MM = 1.0


def _quote_a_catena(segs, numeri, tol_mm=1.5):
    """Le quote, anche quelle a catena: `[(kind, c, a, b)]`.

    `flowpack._quote_estese` unisce tutti i tratti di una retta in una linea
    sola: una catena di quote - 89,5 + 271 + 89,5 sulla stessa riga, o le
    fasce del corpo una sotto l'altra - diventa una linea lunga quanto la
    somma, e nessun numero la misura. Qui per ogni numero si cerca, fra i
    tratti della stessa penna sulla retta accanto, una corsa di pezzi
    consecutivi (salti fino a `QUOTA_SALTO_MM`, dove sta scritto il numero)
    lunga quanto lui e che lo contiene."""
    from .flowpack import QUOTA_ACCANTO_MM
    righe = {}
    for k, c, a, b, st in segs:
        righe.setdefault((k, round(c / 3.0), st), []).append((a, b, c))
    salto = QUOTA_SALTO_MM / PT2MM
    out = set()
    for x, y, v in numeri:
        meglio = None
        for (k, _q, _st), tr in righe.items():
            tr = sorted(tr)
            c = sum(t[2] for t in tr) / len(tr)
            su, lungo = (y, x) if k == "H" else (x, y)
            dd = abs(su - c)
            if dd > QUOTA_ACCANTO_MM / PT2MM or (meglio and dd >= meglio[0]):
                continue
            for i in range(len(tr)):
                a, b = tr[i][0], tr[i][1]
                for j in range(i, len(tr)):
                    if j > i:
                        if tr[j][0] - b > salto:
                            break
                        b = max(b, tr[j][1])
                    if a <= lungo <= b and abs(v - (b - a) * PT2MM) <= tol_mm:
                        meglio = (dd, k, c, a, b)
                        break
                if meglio and meglio[0] == dd:
                    break
        if meglio:
            out.add(meglio[1:])
    return sorted(out)


def _penne_di_quote(segs, numeri, tol=3.0, quota=None):
    """Le penne che disegnano solo quote: linee misurate da un numero scritto
    accanto (`_quote_a_catena`) e i loro richiami, per almeno `PENNA_DI_QUOTE`
    della loro lunghezza.

    Chi mette le quote in una penna sua le mette anche DENTRO il disegno: sul
    T2x25 la catena delle fasce del corpo correva in verticale a 18 mm dal
    fianco destro, spezzata dai numeri, e la griglia la prendeva per una
    colonna (il corpo largo 256 invece di 271); le quote fuori, coi richiami
    lunghi fino al disegno, allargavano il riquadro. `_quote_fuori` toglie
    solo quelle fuori, e solo coi richiami corti: qui si toglie la penna."""
    quote = _quote_a_catena(segs, numeri)
    if not quote:
        return set()
    tot, di_q = {}, {}
    for k, c, a, b, st in segs:
        tot[st] = tot.get(st, 0.0) + (b - a)
        if any((k == kq and abs(c - cq) <= tol and a >= qa - tol and b <= qb + tol)
               or (k != kq and min(abs(c - qa), abs(c - qb)) <= tol
                   and a - tol <= cq <= b + tol)
               for kq, cq, qa, qb in quote):
            di_q[st] = di_q.get(st, 0.0) + (b - a)
    soglia = PENNA_DI_QUOTE if quota is None else quota
    return {st for st, L in tot.items()
            if L > 0 and di_q.get(st, 0.0) >= soglia * L}


def _capi(s):
    k, c, a, b, _st = s
    return ((c, a), (c, b)) if k == "V" else ((a, c), (b, c))


def _distanza(p, s):
    k, c, a, b, _st = s
    lungo, su = (p[1], p[0]) if k == "V" else (p[0], p[1])
    return ((su - c) ** 2 + max(a - lungo, 0.0, lungo - b) ** 2) ** 0.5


def _quanto_tocca(segs, penna, altre, tol_mm=TOCCA_MM):
    """La frazione dei capi dei tratti di `penna` che finiscono su un tratto
    (diverso da loro) di una delle penne `altre`."""
    tol = tol_mm / PT2MM
    mie = [s for s in segs if s[4] == penna]
    loro = [s for s in segs if s[4] in altre]
    capi = [(p, m) for m in mie for p in _capi(m)]
    if not capi:
        return 0.0
    n = sum(1 for p, m in capi
            if any(s is not m and _distanza(p, s) <= tol for s in loro))
    return n / len(capi)


def _riquadro_segs(segs):
    xs = [v for k, c, a, b, _ in segs for v in ((c,) if k == "V" else (a, b))]
    ys = [v for k, c, a, b, _ in segs for v in ((c,) if k == "H" else (a, b))]
    return min(xs), min(ys), max(xs), max(ys)


def _penne_di_riquadri(segs, fustella, tol=3.0):
    """Le penne della fustella che disegnano solo riquadri dentro i pannelli:
    aree di stampa, di colla, di riserva.

    Una cordonatura va da un taglio all'altro, e un taglio incontra le pieghe:
    le penne della fustella si toccano. Un riquadro rientrato di qualche
    millimetro in un pannello non tocca nessun'altra penna (nemmeno un capo su
    cento), e' chiuso su se stesso (almeno meta' dei capi sui suoi stessi
    tratti) e sta tutto dentro il riquadro delle altre. Sul T2x25 la penna
    grigia delle aree di stampa era la piu' lunga di tutte e alzava la soglia
    di `penne_di_fustella`."""
    via = set()
    if len(fustella) < 2:
        return via
    # con due penne sole il confronto si fa con tutte le penne tecniche: sul
    # T2x12 la fustella era la penna verde delle pieghe e quella grigia delle
    # aree di stampa, e il taglio nero, a tratti corti su una pagina larga un
    # metro, restava sotto la soglia
    confronto = fustella if len(fustella) >= 3 else {s[4] for s in segs}
    for st in fustella:
        mie = [s for s in segs if s[4] == st]
        altre = [s for s in segs if s[4] in confronto and s[4] != st]
        if not mie or not altre:
            continue
        a, b = _riquadro_segs(mie), _riquadro_segs(altre)
        dentro = (a[0] >= b[0] - tol and a[1] >= b[1] - tol
                  and a[2] <= b[2] + tol and a[3] <= b[3] + tol)
        if (dentro and _quanto_tocca(segs, st, confronto - {st}) < 0.02
                and _quanto_tocca(segs, st, {st}) >= 0.5):
            via.add(st)
    return via


def _penne_fustella_pulite(segs, numeri, page_w, page_h, tutti=None):
    """`penne_di_fustella`, senza le penne di quote (`_penne_di_quote`) e di
    riquadri (`_penne_di_riquadri`), se ce ne sono.

    Tolte quelle, la soglia si rifa' sulle altre; e una penna che resta sotto
    soglia ma i cui tratti finiscono TUTTI su tratti della fustella e' una
    cordonatura corta (i fianchi e le alette di un astuccio su una penna sua),
    e si tiene. Senza penne da togliere il risultato e' quello di
    `penne_di_fustella`."""
    fustella = penne_di_fustella(segs, page_w, page_h)
    if not fustella:
        return fustella
    via = (_penne_di_quote([s for s in segs if s[4] in fustella], numeri)
           if numeri else set())
    if numeri and tutti:
        # una penna che per meta' e' quote misurate, contata su TUTTI i suoi
        # tratti della pagina e non solo su quelli del gruppo: sul T2x12 con
        # la finestra la catena dentro il disegno ha un 90 rimasto da un altro
        # formato, e nel gruppo le quote vere (271, 272, 432) non c'erano
        for st in fustella - via:
            if _penne_di_quote([x for x in tutti if x[4] == st], numeri, quota=0.5):
                via.add(st)
    via |= _penne_di_riquadri(segs, fustella - via)
    if not via or not fustella - via:
        return fustella
    resto = [s for s in segs if s[4] not in via]
    nuove = penne_di_fustella(resto, page_w, page_h) - via
    for st in {s[4] for s in resto} - nuove:
        if _quanto_tocca(resto, st, nuove) >= 0.95:
            nuove.add(st)
    # il taglio: la penna che sta fuori dalle pieghe da tutti e due i lati
    # (a sinistra e a destra, o sopra e sotto) e le copre per almeno meta'
    # nell'altro verso: i fianchi e le alette. Sul T2x12 il contorno nero, a
    # tratti corti su una pagina larga un metro, non passava la soglia, e
    # senza di lui l'astuccio perdeva i fianchi; le quote sporgono da un
    # lato solo
    if nuove:
        p0, q0, p1, q1 = _riquadro_segs([s for s in resto if s[4] in nuove])
        tol = 3.0 / PT2MM
        # le quote no: sopra e sotto il DT sporgono anche loro. Si
        # riconoscono su tutti i loro tratti, anche fuori dal gruppo (sul
        # T2x12 la catena dentro il disegno ha un 90 rimasto da un altro
        # formato, ma il 271, il 272 e il 432 fuori misurano le loro linee)
        di_quote = set()
        for st in {s[4] for s in resto} - nuove:
            loro = [x for x in (tutti or resto) if x[4] == st]
            if numeri and _penne_di_quote(loro, numeri, quota=0.5):
                di_quote.add(st)
        for st in {s[4] for s in resto} - nuove - di_quote:
            r = _riquadro_segs([s for s in resto if s[4] == st])
            fuori_x = r[0] < p0 - tol and r[2] > p1 + tol
            fuori_y = r[1] < q0 - tol and r[3] > q1 + tol
            copre_x = min(r[2], p1) - max(r[0], p0) >= 0.5 * (p1 - p0)
            copre_y = min(r[3], q1) - max(r[1], q0) >= 0.5 * (q1 - q0)
            if (fuori_x and copre_y) or (fuori_y and copre_x):
                nuove.add(st)
        # e le pieghe corte su una penna loro, anche se non sono fra le
        # penne tecniche (`tutti`, tutti i tratti della pagina): una penna
        # sottile coi tratti che finiscono tutti sulla fustella. Sul T2x12
        # le pieghe rosse dei fianchi, quattro tratti sotto i 52 mm che la
        # soglia della pagina non vedeva: senza, i fianchi del retro non
        # c'erano e fronte e retro si scambiavano
        for st in {x[4] for x in (tutti or ())} - nuove - via:
            if st[0] <= 1.2 and _quanto_tocca(tutti, st, nuove) >= 0.95:
                nuove.add(st)
    return nuove


def testo_del_disegno(pdf_path, page_no=0):
    """`(numeri, lettere)` della pagina, per riconoscere quote e legenda: i
    numeri in punti come li vuole `_largest_cluster`, le lettere come le da'
    `lettere`. Vuoti se il testo non si legge."""
    try:
        from .quote import numeri as _numeri
        numeri = [((x if asse == 0 else q) / PT2MM, (q if asse == 0 else x) / PT2MM, v)
                  for v, x, q, asse in _numeri(pdf_path, page_no)]
    except Exception:
        numeri = []
    try:
        caratteri = lettere(pdf_path, page_no)
    except Exception:
        caratteri = None
    return numeri, caratteri


def fustella_per_colore(all_segs, page_w, page_h, numeri=(), caratteri=None,
                        dettaglio=None):
    """I tratti della fustella scelti per PENNA, la lettura di sempre: le
    penne tecniche, il gruppo connesso piu' esteso, poi via le penne che non
    sono fustella, di quote e di riquadri. E' la prima strada di
    `pack3d.strade`; le altre le danno tratti diversi."""
    pens = _technical_pens(all_segs, page_w, page_h)
    segs = [s for s in all_segs if s[4] in pens] or all_segs
    segs = _largest_cluster(segs, dettaglio=dettaglio, numeri=numeri,
                            lettere=caratteri)
    # Fra le penne tecniche tenute qui sopra ce ne puo' essere una che non
    # e' fustella: si scarta adesso, dopo il raggruppamento spaziale, cioe'
    # guardando solo quello che sta sulla fustella.
    # Anche le penne di quote e di riquadri: `_penne_fustella_pulite`.
    fustella = _penne_fustella_pulite(segs, numeri, page_w, page_h,
                                      tutti=all_segs)
    if fustella:
        gia = {s[4] for s in segs}
        segs = ([s for s in segs if s[4] in fustella]
                + [s for s in all_segs if s[4] in fustella and s[4] not in gia]) or segs
    return segs


def extract(pdf_path: str, page_no: int = 0) -> Dieline:
    t = tratti(pdf_path, page_no)
    numeri, caratteri = testo_del_disegno(pdf_path, page_no)
    segs = fustella_per_colore(list(t.segmenti), t.larghezza, t.altezza,
                               numeri, caratteri,
                               dettaglio=lambda r: _colori(pdf_path, r, page_no))
    return griglia(segs, t.larghezza, t.altezza)


def griglia(segs, page_w, page_h) -> Dieline:
    """La griglia di righe e colonne dai tratti della fustella: il riquadro,
    le cordonature lunghe raggruppate, i tratti tenuti. Vale per tutte le
    strade (`pack3d.strade`)."""
    bx0 = by0 = 1e9
    bx1 = by1 = -1e9
    for kind, c, a, b, st in segs:
        lo_x, hi_x = (c, c) if kind == "V" else (a, b)
        lo_y, hi_y = (a, b) if kind == "V" else (c, c)
        bx0, bx1 = min(bx0, lo_x), max(bx1, hi_x)
        by0, by1 = min(by0, lo_y), max(by1, hi_y)
    tol = 3.0
    # scarta quote, frecce e riferimenti esterni al contorno
    segs = [(k, c, a, b, st) for k, c, a, b, st in segs
            if bx0 - tol <= (c if k == "V" else a) and (c if k == "V" else b) <= bx1 + tol
            and by0 - tol <= (c if k == "H" else a) and (c if k == "H" else b) <= by1 + tol]

    bbox = (bx0, by0, bx1, by1)
    Wb, Hb = bx1 - bx0, by1 - by0

    vlong, hlong = [], []
    for kind, c, a, b, st in _tratteggi_uniti(segs):
        L = b - a
        if kind == "V" and L > Hb * 0.05:
            vlong.append((c, L))
        if kind == "H" and L > Wb * 0.05:
            hlong.append((c, L))

    xs = [c for c, w in _cluster(vlong, 3.5) if w > Hb * 0.12]
    ys = [c for c, w in _cluster(hlong, 3.5) if w > Wb * 0.12]
    for v in (bx0, bx1):
        if not any(abs(v - x) < 2.5 for x in xs):
            xs.append(v)
    for v in (by0, by1):
        if not any(abs(v - y) < 2.5 for y in ys):
            ys.append(v)
    xs.sort(); ys.sort()
    d = Dieline(page_w, page_h, bbox, xs, ys)
    d.vsegs = [(c, a, b) for k, c, a, b, st in segs if k == "V"]
    d.hsegs = [(c, a, b) for k, c, a, b, st in segs if k == "H"]
    return d


# --------------------------------------------------------------------------- #
# classificazione e assegnazione dei ruoli
# --------------------------------------------------------------------------- #
def classify(d: Dieline) -> str:
    nx, ny = len(d.xs) - 1, len(d.ys) - 1
    w = (d.bbox[2] - d.bbox[0]) * PT2MM
    h = (d.bbox[3] - d.bbox[1]) * PT2MM
    if nx >= 3 and ny >= 4:
        return "carton"
    if nx <= 2 and ny <= 2 and max(w, h) / max(min(w, h), 1) > 2.2:
        return "flowpack"
    if nx >= 3 and ny == 3:
        return "tray"
    return "unknown"


def _fasce_del_corpo(d, riquadri=True):
    """Le fasce della fasciatura, lette sulla colonna del corpo.

    Le `ys` del foglio sono l'unione di TUTTE le cordonature, e ci finisce
    anche quello che non piega il corpo. Sul T6 aperto una linea a 27 mm
    dal fondo - dove le alette laterali cambiano profilo - spezzava la faccia
    da 125 in 98 + 27, e il fronte spariva dalla lettura. Una cordonatura che
    separa due fasce della fasciatura deve attraversare la colonna del corpo:
    quelle che non lo fanno appartengono alle alette.
    """
    xs = d.xs
    ci = max(range(len(xs) - 1), key=lambda i: xs[i + 1] - xs[i])
    ys = d.rows_in_col(xs[ci], xs[ci + 1])
    if len(ys) < 3:
        ys = d.ys
    if not riquadri:
        ys = _senza_riquadri(d, ys, xs[ci], xs[ci + 1])
    return [(ys[i], ys[i + 1], ys[i + 1] - ys[i]) for i in range(len(ys) - 1)]


def _senza_riquadri(d, ys, x0, x1, rientro_mm=1.5, tol=2.5):
    """Le cordonature che chiudono un riquadro DENTRO una faccia non la piegano.

    Sul retro di un astuccio a linguetta c'e' una striscia a strappo: due
    tratti orizzontali che si fermano 3 mm prima dei bordi del corpo e due
    verticali che li chiudono ai capi, con la fessura della linguetta in
    mezzo. Coprono il 97% della colonna e passavano per cordonature: il retro
    da 138,5 mm si spezzava in 111,3 + 24,2 + 3, e il solutore non trovava
    piu' due fasce alte uguali. Una riga che si ferma prima dei due bordi,
    insieme a un'altra cosi', con due verticali che le uniscono agli stessi
    capi, e' un riquadro della faccia, non il confine di una fascia.
    """
    r = rientro_mm / PT2MM

    def capi(y):
        segs = [(a, b) for cy, a, b in d.hsegs
                if abs(cy - y) < tol and b > x0 and a < x1]
        if not segs:
            return None
        a, b = min(s[0] for s in segs), max(s[1] for s in segs)
        if a - x0 < r or x1 - b < r:
            return None
        return a, b

    def chiusa(x, ya, yb):
        span = sum(max(0.0, min(b, yb) - max(a, ya))
                   for cx, a, b in d.vsegs if abs(cx - x) < tol)
        return span >= 0.9 * (yb - ya)

    via = set()
    interni = ys[1:-1]
    for i, ya in enumerate(interni):
        ca = capi(ya)
        if ca is None:
            continue
        for yb in interni[i + 1:]:
            cb = capi(yb)
            if (cb and abs(ca[0] - cb[0]) < tol and abs(ca[1] - cb[1]) < tol
                    and chiusa(ca[0], ya, yb) and chiusa(ca[1], ya, yb)):
                via.update((ya, yb))
    return [y for y in ys if y not in via] if via else ys


def _ha_fianchi(d, riga, minimo_mm=3.0):
    """Se la fascia porta i fianchi: una colonna per parte accanto a quella
    del corpo, attraversata da cordonature che tagliano davvero la fascia."""
    xs = d.cols_in_row(riga[0], riga[1])
    if len(xs) < 4:
        return False
    larghe = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    c = max(range(len(larghe)), key=lambda i: larghe[i])
    return (c >= 1 and c + 1 < len(larghe)
            and larghe[c - 1] * PT2MM >= minimo_mm
            and larghe[c + 1] * PT2MM >= minimo_mm)


def _chiuso(rows, tol=3.0, fianchi=None):
    """Ruoli di [aletta] RETRO - CIELO - FRONTE - FONDO, per indice di fascia.

    Retro e fronte sono la stessa faccia vista da due parti, e hanno la STESSA
    altezza: se le due fasce piu' alte non l'hanno, questa non e' la lettura
    giusta. Su un T6 aperto il solutore prendeva 40,5 e 125 e ne faceva
    la media, 82,8, che non e' l'altezza di niente.

    Quale delle due e' il retro lo dice la fustella: **i fianchi stanno sul
    retro**. Di solito e' quella in alto, ma l'astuccio T8 e'
    montato al contrario - CIELO - FRONTE - FONDO - RETRO - colla - e le
    chiusure di testa sono attaccate alla faccia bassa. Leggendolo alla solita
    maniera il bambino finiva sul retro, il fronte era il pannello bianco, il
    fondo la linguetta della colla e il cielo col nome del prodotto spariva.
    `fianchi(i)` dice se la fascia `i` porta i fianchi; se li porta solo la
    faccia bassa, il retro e' lei. Cielo e fondo restano quello che sono per
    il fronte, sopra e sotto di lui: sono loro, non il retro, a dire da che
    parte sta la grafica.
    """
    if len(rows) < 3:
        return None
    order = sorted(range(len(rows)), key=lambda i: -rows[i][2])
    alta, bassa = sorted(order[:2])
    ha, hb = rows[alta][2] * PT2MM, rows[bassa][2] * PT2MM
    if abs(ha - hb) > max(tol, 0.08 * max(ha, hb)):
        return None
    if fianchi is not None and fianchi(bassa) and not fianchi(alta):
        # CIELO - FRONTE - FONDO - RETRO [- colla]
        r = {"back": bassa, "front": alta, "fianchi": bassa}
        if bassa - alta > 1:
            r["bottom"] = max(range(alta + 1, bassa), key=lambda i: rows[i][2])
            fondo = rows[r["bottom"]][2] * PT2MM
            cielo = rows[alta - 1][2] * PT2MM if alta >= 1 else 0.0
            # il cielo e' la fascia sopra il fronte, se e' profonda come il
            # fondo: sopra potrebbe esserci un'aletta, e un'aletta non e' una
            # faccia della scatola
            if cielo > 0 and abs(cielo - fondo) <= max(tol, 0.25 * fondo):
                r["top"] = alta - 1
        return r
    if (fianchi is not None and fianchi(alta) and alta >= 1
            and bassa - alta > 1 and bassa + 1 < len(rows)):
        # CIELO - FRONTE - FONDO - RETRO - alette, coi fianchi sul FRONTE:
        # la scatola a linguetta che chiude sul retro. Letta come RETRO -
        # CIELO - FRONTE - FONDO, il "fondo" sarebbe l'aletta da 6 mm dopo la
        # fascia bassa e il "cielo" il fondo vero: sul T10 a linguetta ne
        # usciva una scatola profonda 56,5 col fondo stirato dell'842%. Un
        # fondo e' una faccia, profondo quasi come il cielo; se la fascia
        # dopo la bassa e' un'aletta e sopra l'alta c'e' una fascia profonda
        # come quella in mezzo, il fronte e' l'alta, fra il cielo e il fondo.
        mezzo = max(range(alta + 1, bassa), key=lambda i: rows[i][2])
        hm = rows[mezzo][2] * PT2MM
        dopo = rows[bassa + 1][2] * PT2MM
        cielo = rows[alta - 1][2] * PT2MM
        if dopo < 0.3 * hm and abs(cielo - hm) <= max(tol, 0.25 * hm):
            return {"back": bassa, "front": alta, "fianchi": alta,
                    "bottom": mezzo, "top": alta - 1}
    back_i, front_i = alta, bassa
    r = {"back": back_i, "front": front_i, "fianchi": back_i}
    if front_i - back_i > 1:
        r["top"] = max(range(back_i + 1, front_i), key=lambda i: rows[i][2])
    if front_i + 1 < len(rows):
        r["bottom"] = front_i + 1
    elif back_i >= 1 and "top" in r:
        # FONDO - RETRO - CIELO - FRONTE: la fasciatura parte dal fondo, e
        # oltre il fronte non c'e' niente. Il fondo e' la fascia prima del
        # retro, se e' profonda come il cielo: sull'astuccio della ciambella, letto nel
        # verso della grafica, e' la fascia marrone che continua l'onda del
        # retro, e senza questa lettura la faccia sotto restava bianca.
        cielo = rows[r["top"]][2] * PT2MM
        fondo = rows[back_i - 1][2] * PT2MM
        if abs(cielo - fondo) <= max(tol, 0.25 * cielo):
            r["bottom"] = back_i - 1
    return r


def _aperto(rows, tol=1.5):
    """Ruoli di un astuccio che non si chiude: CIELO - FRONTE - FONDO.

    Un astuccio non e' obbligato ad avere il retro. Un vassoio non ce l'ha per
    definizione; un pack con finestra ce l'ha a meta', chiuso da due falde che
    lasciano un'apertura in mezzo da cui si vede il prodotto - il T6 aperto
    e' cosi'. La firma in fustella e' una faccia grande sola, con cielo e
    fondo UGUALI sopra e sotto, e i fianchi agganciati al FRONTE e non al retro
    che non c'e'.

    Le due fasce oltre il cielo e il fondo, se ci sono, sono le falde del retro.
    """
    if len(rows) < 3:
        return None
    f = max(range(len(rows)), key=lambda i: rows[i][2])
    if f == 0 or f == len(rows) - 1:
        return None
    ht, hb = rows[f - 1][2] * PT2MM, rows[f + 1][2] * PT2MM
    if min(ht, hb) <= 0 or abs(ht - hb) > max(tol, 0.10 * max(ht, hb)):
        return None
    r = {"front": f, "top": f - 1, "bottom": f + 1, "fianchi": f}
    if f - 2 >= 0:
        r["back_top"] = f - 2
    if f + 2 < len(rows):
        r["back_bottom"] = f + 2
    return r


# Il fondo a tetto: le due falde uguali a meno di tanto, e insieme piu' lunghe
# della profondita' di almeno tanto (a filo, piatte, sarebbero un fondo solo)
TETTO_FALDE_TOL = 0.08
TETTO_LUNGHE = 1.05


def _tetto(rows, fianchi, tol=3.0):
    """CIELO - FRONTE - FALDA - FALDA - RETRO, col fondo a tetto: `(ruoli,
    rows)`, con le fasce del retro unite, o None.

    Fra il fronte e il retro, al posto del fondo, due fasce uguali, ognuna
    piu' corta della profondita' e insieme piu' lunghe: piatte non ci stanno,
    e si chiudono a tetto dentro la scatola - il pane ripieno T15, "la base
    che ripiega a triangolo dentro la scatola, tipo soffietto": due falde da
    49 mm per una scatola profonda 72,7, e la cresta sale di 33. La
    profondita' e' il cielo sopra il fronte, e i fianchi stanno sul fronte.
    Il retro e' quello che viene dopo le falde, alto come il fronte: se una
    riga lo spezza (109 + 29 sul T15, la fessura della linguetta in cima),
    le fasce che insieme tornano col fronte sono il retro intero.
    """
    if fianchi is None or len(rows) < 5:
        return None
    for f in range(1, len(rows) - 3):
        if not fianchi(f):
            continue
        H = rows[f][2] * PT2MM
        D = rows[f - 1][2] * PT2MM
        a, b = rows[f + 1][2] * PT2MM, rows[f + 2][2] * PT2MM
        if not (D > 0 and abs(a - b) <= max(tol, TETTO_FALDE_TOL * max(a, b))
                and max(a, b) < D and a + b >= TETTO_LUNGHE * D):
            continue
        somma = 0.0
        for k in range(f + 3, len(rows)):
            somma += rows[k][2] * PT2MM
            if abs(somma - H) <= max(tol, 0.03 * H):
                retro = (rows[f + 3][0], rows[k][1], rows[k][1] - rows[f + 3][0])
                unite = list(rows[:f + 3]) + [retro] + list(rows[k + 1:])
                return ({"front": f, "top": f - 1, "bottom": f + 1,
                         "tetto": f + 2, "back": f + 3, "fianchi": f}, unite)
            if somma > H + tol:
                break
    return None


def cresta(D, a, b):
    """Dove sta la cresta del fondo a tetto, in mm dal fronte, e quanto sale:
    il triangolo che le due falde `a` (dal fronte) e `b` (dal retro) fanno
    con la profondita' `D`."""
    import math
    x = (D * D + a * a - b * b) / (2.0 * D)
    return x, math.sqrt(max(a * a - x * x, 0.0))


# --------------------------------------------------------------------------- #
# le letture candidate di un astuccio, e il loro costo
# --------------------------------------------------------------------------- #
# Il 20 novembre 2026 il proprietario: il deterministico deve fallire il meno
# possibile, anche a costo di tempo (regole/astucci.md, *Le letture a
# punteggio*). Fino ad allora `solve_carton` confrontava le fasce con poche
# sequenze fisse e vinceva la prima che passava; due ripieghi, uno per caso -
# il riquadro a strappo del pane ripieno T10, il fondo a tetto del T15 - si
# provavano in fila. Adesso si fanno tutte le letture, le serie di fasce
# candidate per tutte le forme, ognuna col suo costo, e vince la migliore; la
# lettura di prima, se c'e', vince a pari merito (`PRECEDENZA`). Le altre
# strade della fustella e il resto del punteggio - quote e grafica - stanno in
# `pack3d.strade`.

# Quanto costa una correzione delle fasce: poco, cosi' a pari misure vince la
# lettura piu' vicina al disegno.
COSTO_CORREZIONE = 0.1
# Quanto deve costare meno un'altra lettura per battere quella di prima.
PRECEDENZA = 0.3
# Oltre questo costo una lettura che non e' quella di prima non vale: e'
# un astuccio che non torna. Sulla scatola a punta T6 le unioni davano un
# fondo a tetto coi fianchi larghi il 41% piu' della profondita' (costo 4,2):
# la punta non e' un astuccio, e deve leggerla `pack3d.punta`.
COSTO_MAX = 2.0
# Una voce sola non conta piu' di tanto: una lettura sbagliata in una cosa
# sola non deve sembrare peggio di una sbagliata in tutto.
VOCE_MAX = 5.0
# Le tolleranze di sempre diventano l'unita' del costo: uno scarto pari alla
# tolleranza costa 1.
TOL_ALTI = 0.08          # fronte e retro alti uguali (`_chiuso`)
TOL_PROFONDI = 0.25      # cielo e fondo di un chiuso (il fondo di `_chiuso`)
TOL_APERTO = 0.10        # cielo e fondo di un aperto (`_aperto`)
TOL_FIANCHI = 0.08       # i fianchi larghi quanto la profondita'
TOL_LARGHI = 0.03        # fronte e retro larghi uguali, fasciatura orizzontale
TOL_ALETTE = 0.06        # le alette di testa profonde come la scatola (`check`)
# Una faccia che manca; un'aletta presa per faccia, o una falda del retro
# alta quasi come il fronte, che e' un retro.
COSTO_FACCIA = 2.0
COSTO_ALETTA = 3.0
# Sotto i sei decimi dell'altra, il cielo o il fondo e' un'aletta: girata di
# 180 gradi la punta T6 dava un "fondo" da 3,4 mm.
ALETTA = 0.6
FALDA_RETRO = 0.85
# Le voci del costo che vengono da fuori del disegno (`pack3d.strade`).
EVIDENZE = ("grafica", "quote", "copertura")
# Le facce come le chiamano gli errori.
NOMI_FACCE = {"top": "il cielo", "bottom": "il fondo", "back": "il retro",
              "front": "il fronte", "left": "il fianco sinistro",
              "right": "il fianco destro"}


@dataclass
class Lettura:
    """Una lettura candidata dell'astuccio: la forma, le fasce usate, i ruoli
    e le correzioni che l'hanno data; `d` l'astuccio risolto - una copia
    della fustella coi pannelli - oppure `scartata` col motivo. `prima` e' la
    lettura che si faceva prima del 21 novembre 2026, quella che vince a pari
    merito. Strada, giro e voti li aggiunge `pack3d.strade`."""
    forma: str
    rows: list
    ruoli: dict
    correzioni: tuple = ()
    d: object = None
    voci: dict = field(default_factory=dict)
    costo: float = 0.0
    scartata: str = ""
    prima: bool = False
    strada: str = "colore"
    giro: int = 0
    pdf: object = None
    voti: dict = field(default_factory=dict)

    @property
    def valida(self):
        return self.d is not None and not self.scartata

    @property
    def geometrico(self):
        """Il costo che dice il disegno da solo - le misure e le correzioni -
        senza le prove di fuori (quote, grafica, copertura): e' quello che
        decide se una lettura e' plausibile (`plausibili`)."""
        return round(sum(v for k, v in self.voci.items() if k not in EVIDENZE), 3)

    def descrivi(self):
        """La lettura in una riga: misure, forma, strada e correzioni."""
        d = self.d
        cosa = ("%.1f x %.1f x %.1f mm" % d.dims_mm) if d is not None else "-"
        come = [self.forma or "astuccio"]
        if self.strada != "colore":
            come.append(self.strada)
        come += list(self.correzioni)
        if self.giro:
            come.append("foglio girato di %d gradi" % self.giro)
        return "%s (%s)" % (cosa, "; ".join(come))


def stesso_modello(a, b, tol=1.5, rel=0.02):
    """Se due letture danno lo stesso astuccio, anche arrivandoci da strade
    diverse: stessa forma, stesse facce, stesso giro, misure entro `tol` mm o
    `rel` della misura. Un millimetro e mezzo su un retro da 138 (la seconda
    lettura del pane ripieno T10, con la fascia da 3 mm fuori) non e' un
    altro astuccio; 252 contro 271 di larghezza si'."""
    da, db = a.d, b.d

    def vicine(x, y):
        return abs(x - y) <= max(tol, rel * max(x, y))
    return (da.layout == db.layout and da.chiuso == db.chiuso
            and a.giro == b.giro and set(da.panels) == set(db.panels)
            and all(vicine(x, y) for x, y in zip(da.dims_mm, db.dims_mm))
            and vicine(da.finestra_mm, db.finestra_mm))


def _pannelli(d, rows, ruoli):
    """L'astuccio di una lettura: una copia di `d` coi pannelli, le misure e
    i controlli che il disegno impone, o ValueError col motivo."""
    import copy
    d = copy.copy(d)

    def fasce():
        """Le fasce misurate, per gli errori: senza numeri non si diagnostica."""
        return [round(r[2] * PT2MM, 1) for r in rows]

    # I fianchi si cercano sulla griglia valida per la fascia a cui sono
    # agganciati: le alette di presa del cielo non attraversano quella fascia.
    riga = rows[ruoli["fianchi"]]
    row_xs = d.cols_in_row(riga[0], riga[1]) or d.xs
    cols = [(row_xs[i], row_xs[i + 1], row_xs[i + 1] - row_xs[i])
            for i in range(len(row_xs) - 1)]
    cmain = max(range(len(cols)), key=lambda i: cols[i][2])

    def mk(ci, ri, role):
        return Panel(cols[ci][0], rows[ri][0], cols[ci][1], rows[ri][1], role)

    P = {k: mk(cmain, v, k) for k, v in ruoli.items() if k != "fianchi"}
    if cmain - 1 >= 0:
        P["left"] = mk(cmain - 1, ruoli["fianchi"], "left")
    if cmain + 1 < len(cols):
        P["right"] = mk(cmain + 1, ruoli["fianchi"], "right")
    d.fianchi_su = "front" if ruoli["fianchi"] == ruoli["front"] else "back"

    # Se anche l'altra fascia alta porta i fianchi, quali si vedono non lo
    # dice la fustella: una coppia e' stampata, l'altra sono alette di colla
    # che finiscono dentro. Sull'astuccio della ciambella i fianchi del retro sono
    # tratteggiati e quelli del fronte portano il nome del prodotto: la scelta la
    # fa la stampa, in `artwork.texture_astuccio`. Qui si preparano tutte e due.
    altra = {"back": ruoli.get("front"), "front": ruoli.get("back")}[d.fianchi_su]
    d.fianchi_alt = {}
    if altra is not None and _ha_fianchi(d, rows[altra]):
        riga2 = rows[altra]
        xs2 = d.cols_in_row(riga2[0], riga2[1])
        c2 = [(xs2[i], xs2[i + 1]) for i in range(len(xs2) - 1)]
        m2 = max(range(len(c2)), key=lambda i: c2[i][1] - c2[i][0])
        if m2 >= 1 and m2 + 1 < len(c2):
            d.fianchi_alt = {
                "left": Panel(c2[m2 - 1][0], riga2[0], c2[m2 - 1][1], riga2[1], "left"),
                "right": Panel(c2[m2 + 1][0], riga2[0], c2[m2 + 1][1], riga2[1], "right"),
            }

    # Prima di dare le quote, i controlli che il disegno stesso impone. Non
    # sono cinture di sicurezza: sono la differenza fra dire "non lo so
    # risolvere" e consegnare un astuccio sbagliato.
    if "top" not in P and "left" not in P:
        raise ValueError(
            "astuccio: non si trova ne' il cielo ne' un fianco, quindi la "
            "profondita' non e' ricavabile. Fasce (mm): %s" % fasce())

    d.chiuso = "back" in P
    if d.chiuso:
        H = (P["back"].h_mm + P["front"].h_mm) / 2.0
        D = P["top"].h_mm if "top" in P else P["left"].w_mm
    else:
        # Su un astuccio aperto i fianchi SONO la profondita', e devono
        # tornare con cielo e fondo. Senza questo controllo ci casca dentro
        # qualunque flowpack steso: sul wafer da colazione la fascia grande e' il nastro,
        # cielo e fondo sono le due falde da 5 mm uguali, e ne uscirebbe un
        # astuccio profondo cinque millimetri. I fianchi da 7 lo smentiscono.
        if "left" not in P or "right" not in P:
            raise ValueError(
                "astuccio aperto: senza fianchi accanto al fronte la "
                "profondita' non e' ricavabile. Fasce (mm): %s" % fasce())
        H = P["front"].h_mm
        D = (P["top"].h_mm + P["bottom"].h_mm) / 2.0
        wl, wr = P["left"].w_mm, P["right"].w_mm
        if (abs(wl - wr) > max(1.5, 0.08 * max(wl, wr))
                or abs((wl + wr) / 2.0 - D) > max(1.5, 0.08 * max(D, 1.0))):
            raise ValueError(
                "astuccio aperto: i fianchi (%.1f e %.1f mm) non tornano con "
                "la profondita' di cielo e fondo (%.1f mm), quindi questa non "
                "e' una fasciatura ad astuccio. Fasce (mm): %s"
                % (wl, wr, D, fasce()))
        # La finestra e' quello che le falde del retro non coprono.
        d.finestra_mm = round(
            H - sum(P[k].h_mm for k in ("back_top", "back_bottom") if k in P), 1)

    if "tetto" in P:
        x, h = cresta(D, P["bottom"].h_mm, P["tetto"].h_mm)
        d.tetto = (round(x, 2), round(h, 2))
    W = P["front"].w_mm
    d.panels = P
    d.kind = "carton"
    d.dims_mm = (round(W, 1), round(H, 1), round(D, 1))
    return d


def _scarto(a, b):
    return abs(a - b) / max(a, b, 1e-9)


def costo_misure(d):
    """Le voci del costo di un astuccio risolto che il disegno dice da solo:
    quanto non tornano fra loro le misure delle facce. Nessuna voce e' un
    astuccio che torna in tutto.

    - fronte e retro alti uguali, sono la stessa faccia vista da due parti;
    - cielo e fondo profondi uguali (non sul fondo a tetto: le falde sono
      piu' corte apposta); sotto i sei decimi uno dei due e' un'aletta;
    - **i fianchi larghi quanto la profondita'**: sull'astuccio chiuso prima
      non si guardava, ed e' quello che smentisce una colonna in piu' (la
      catena delle quote del T2x12, quando i numeri non si leggono, faceva un
      fianco di 18,6 mm su una scatola profonda 45);
    - le facce che mancano;
    - su un aperto, una falda del retro alta quasi come il fronte e' un retro.
    """
    P = d.panels
    W, H, D = d.dims_mm
    voci = {}

    def voce(nome, v):
        if v > 1e-6:
            voci[nome] = round(min(v, VOCE_MAX), 3)

    if d.layout == "hwrap":
        voce("fronte e retro", _scarto(P["front"].w_mm, P["back"].w_mm) / TOL_LARGHI)
        voce("fianchi", _scarto(P["left"].w_mm, P["right"].w_mm) / TOL_FIANCHI)
        for k in ("top", "bottom"):
            if k in P:
                voce("aletta di testa",
                     abs(P[k].h_mm - D - d.curva_mm) / max(D, 1.0) / TOL_ALETTE)
            else:
                voce("manca " + NOMI_FACCE[k], COSTO_FACCIA)
        return voci
    if "front" in P and "back" in P:
        voce("fronte e retro", _scarto(P["front"].h_mm, P["back"].h_mm) / TOL_ALTI)
    if "top" in P and "bottom" in P and not d.tetto:
        a, b = P["top"].h_mm, P["bottom"].h_mm
        voce("cielo e fondo", _scarto(a, b) / (TOL_PROFONDI if d.chiuso else TOL_APERTO))
        if min(a, b) < ALETTA * max(a, b):
            voce("aletta presa per faccia", COSTO_ALETTA)
    for k in ("top", "bottom"):
        if k not in P:
            voce("manca " + NOMI_FACCE[k], COSTO_FACCIA)
    fianchi = [P[k].w_mm for k in ("left", "right") if k in P]
    if not fianchi:
        voce("mancano i fianchi", COSTO_FACCIA)
    else:
        voce("fianchi", sum(_scarto(w, D) for w in fianchi) / len(fianchi) / TOL_FIANCHI)
        if len(fianchi) == 1:
            voce("un fianco solo", COSTO_FACCIA / 2.0)
    if not d.chiuso:
        alta = max((P[k].h_mm for k in ("back_top", "back_bottom") if k in P),
                   default=0.0)
        if alta >= FALDA_RETRO * H:
            voce("falda alta come il fronte", COSTO_ALETTA)
    return voci


def riga_debole(d, y, x0, x1, rientro_mm=1.5, copre=0.9, salto_mm=3.0):
    """Se la riga `y` della colonna [x0, x1] puo' non essere una piega della
    fasciatura: non la attraversa tutta (copre meno di `copre`, coi salti di
    un tratteggio fino a `salto_mm` chiusi), oppure si ferma prima di tutti e
    due i bordi, come i lati di un riquadro dentro una faccia (il riquadro a
    strappo del pane ripieno T10 rientra di 3,2 mm per parte, quello della
    falda del T15 di 7,9). Una piega vera va da bordo a bordo: la cresta del
    fondo a tetto del T15 copre la colonna intera, e le due falde non si
    uniscono."""
    tr = sorted((max(a, x0), min(b, x1)) for c, a, b in d.hsegs
                if abs(c - y) < 2.5 and b > x0 and a < x1)
    if not tr:
        return True
    salto = salto_mm / PT2MM
    pezzi = [list(tr[0])]
    for a, b in tr[1:]:
        if a - pezzi[-1][1] <= salto:
            pezzi[-1][1] = max(pezzi[-1][1], b)
        else:
            pezzi.append([a, b])
    coperto = sum(b - a for a, b in pezzi) / max(x1 - x0, 1e-9)
    r = rientro_mm / PT2MM
    return coperto < copre or (pezzi[0][0] - x0 >= r and x1 - pezzi[-1][1] >= r)


def _gemelle(rows, tol=3.0, rel=0.03, minima=0.2, volte=2, debole=None):
    """Le serie con due o tre fasce vicine unite, quando insieme tornano con
    un'altra fascia della serie - la faccia gemella - e le righe fra loro sono
    deboli (`debole(y)`, di serie `riga_debole`). Sul pane ripieno T10 il
    riquadro a strappo spezza il retro in 111,3 + 24,2 + 3, che insieme
    tornano col fronte da 139,2; sul T15 il riquadro della prima falda la
    spezza in 10 + 16,1 + 23, gemella dell'altra da 49. La gemella deve essere
    una faccia, non un'aletta: almeno `minima` della fascia piu' alta. Al piu'
    `volte` unioni per serie: le candidate restano qualche decina.
    `[(fasce, (perche', ...))]`."""
    def una(rows):
        hs = [r[2] * PT2MM for r in rows]
        alto = max(hs) if hs else 0.0
        out = []
        for i in range(len(rows)):
            for n in (2, 3):
                j = i + n
                if j > len(rows):
                    break
                if debole is not None and not all(debole(rows[m][0])
                                                  for m in range(i + 1, j)):
                    continue
                s = sum(hs[i:j])
                for k, h in enumerate(hs):
                    if i <= k < j or h < minima * alto:
                        continue
                    if abs(s - h) <= max(tol, rel * h):
                        unita = (rows[i][0], rows[j - 1][1], rows[j - 1][1] - rows[i][0])
                        out.append((list(rows[:i]) + [unita] + list(rows[j:]),
                                    "unite %s come la fascia da %.1f mm"
                                    % (" + ".join("%.1f" % v for v in hs[i:j]), h)))
                        break
        return out

    fuori = []

    def avanti(rows, fatte, quante):
        for r, perche in una(rows):
            fuori.append((r, fatte + (perche,)))
            if quante > 1:
                avanti(r, fatte + (perche,), quante - 1)
    avanti(list(rows), (), volte)
    return fuori


SENZA_RIQUADRI = "senza i riquadri dentro le facce"


def serie_candidate(d, rows=None):
    """Le serie di fasce da provare, col perche' di ognuna: quella di serie
    (`_fasce_del_corpo`), senza i riquadri dentro le facce
    (`_senza_riquadri`), e su tutte e due le facce gemelle unite (`_gemelle`).
    `[(fasce, correzioni)]`, la serie di sempre per prima."""
    rows = _fasce_del_corpo(d) if rows is None else rows
    out, viste = [], set()

    def metti(r, corr):
        k = tuple(round(x[0], 1) for x in r) + ((round(r[-1][1], 1),) if r else ())
        if k not in viste:
            viste.add(k)
            out.append((list(r), corr))
    metti(rows, ())
    metti(_fasce_del_corpo(d, riquadri=False), (SENZA_RIQUADRI,))
    xs = d.xs
    ci = max(range(len(xs) - 1), key=lambda i: xs[i + 1] - xs[i])
    deboli = {}

    def debole(y):
        k = round(y, 2)
        if k not in deboli:
            deboli[k] = riga_debole(d, y, xs[ci], xs[ci + 1])
        return deboli[k]
    for base, corr in list(out):
        for r, perche in _gemelle(base, debole=debole):
            metti(r, corr + perche)
    return out


def forme(d, rows, fianchi=None):
    """Le forme d'astuccio che questa serie di fasce puo' essere, tutte e non
    la prima che passa: `[(forma, ruoli, fasce)]`. Chiuso (nelle sue tre
    letture, che decidono i fianchi: `_chiuso`), aperto (`_aperto`), a tetto
    (`_tetto`, con le fasce del retro unite)."""
    if fianchi is None:
        def fianchi(i):
            return _ha_fianchi(d, rows[i])
    out = []
    r = _chiuso(rows, fianchi=fianchi)
    if r is not None:
        out.append(("chiuso", r, rows))
    r = _aperto(rows)
    if r is not None:
        out.append(("aperto", r, rows))
    t = _tetto(rows, fianchi)
    if t is not None:
        out.append(("tetto", t[0], t[1]))
    return out


def _non_intera(d):
    """Perche' l'astuccio di una lettura con le fasce corrette non vale, o
    "": una correzione vale solo se ne esce una scatola intera, retro,
    fronte, cielo e fondo (su un aperto i fianchi al posto del retro), e cielo
    e fondo facce tutte e due. Sulla scatola a punta il riquadro a strappo,
    tolto, ne faceva un astuccio senza fondo."""
    P = d.panels
    servono = (("back", "front", "top", "bottom") if d.chiuso
               else ("front", "top", "bottom", "left", "right"))
    manca = [NOMI_FACCE[k] for k in servono if k not in P]
    if manca:
        return "scatola non intera: manca %s" % ", ".join(manca)
    if not d.tetto:
        a, b = P["top"].h_mm, P["bottom"].h_mm
        if min(a, b) < ALETTA * max(a, b):
            return ("cielo da %.1f e fondo da %.1f mm: uno dei due e' un'aletta"
                    % (a, b))
    return ""


def letture_carton(d):
    """Tutte le letture candidate dell'astuccio a fasciatura verticale `d`:
    le serie di fasce (`serie_candidate`) per le forme (`forme`), ognuna
    risolta (`_pannelli`) e col suo costo (`costo_misure`, piu'
    `COSTO_CORREZIONE` per ogni correzione). Una lettura con le fasce
    corrette vale solo se la scatola e' intera (`_non_intera`). `prima` e'
    quella che si faceva prima (`_segna_la_prima`)."""
    sa = {}

    def ha_fianchi(riga):
        k = (round(riga[0], 2), round(riga[1], 2))
        if k not in sa:
            sa[k] = _ha_fianchi(d, riga)
        return sa[k]

    out = []
    for serie, corr in serie_candidate(d):
        for forma, ruoli, usate in forme(d, serie,
                                          lambda i, s=serie: ha_fianchi(s[i])):
            l = Lettura(forma, usate, ruoli, corr)
            try:
                l.d = _pannelli(d, usate, ruoli)
            except ValueError as e:
                l.scartata = str(e)
                out.append(l)
                continue
            if corr:
                l.scartata = _non_intera(l.d)
            l.voci = costo_misure(l.d)
            if corr:
                l.voci["correzioni"] = round(COSTO_CORREZIONE * len(corr), 3)
            l.costo = round(sum(l.voci.values()), 3)
            out.append(l)
    _segna_la_prima(out)
    return out


def _segna_la_prima(letture):
    """Quale lettura si faceva prima del 21 novembre 2026, quando vinceva la
    prima che passava: la serie di sempre, chiuso o aperto; se non c'era,
    senza i riquadri, ma solo un chiuso intero; se no il fondo a tetto, coi
    riquadri e senza. Se quella c'era ma il disegno la smentiva, prima si
    fermava: allora nessuna e' `prima`, e vince la migliore."""
    serie = [l for l in letture if not l.correzioni]
    senza = [l for l in letture if l.correzioni == (SENZA_RIQUADRI,)]
    primo = next((l for l in serie if l.forma in ("chiuso", "aperto")), None)
    if primo is not None:
        primo.prima = primo.valida
        return
    primo = next((l for l in senza if l.forma in ("chiuso", "aperto")), None)
    if primo is not None and primo.forma == "chiuso" and primo.valida:
        primo.prima = True
        return
    for gruppo in (serie, senza):
        for l in gruppo:
            if l.forma == "tetto":
                l.prima = l.valida
                return


def plausibili(letture, costo_max=None):
    """Le letture che possono vincere: quella di prima se vale, come prima;
    le altre se valgono e il loro costo geometrico (`Lettura.geometrico`) e'
    al piu' `costo_max` (di serie `COSTO_MAX`, o la soglia larga di un
    tentativo dopo il primo: `pack3d.tentativi.costo_max`)."""
    if costo_max is None:
        from . import tentativi
        costo_max = tentativi.costo_max(COSTO_MAX)
    return [l for l in letture
            if l.valida and (l.prima or l.geometrico <= costo_max)]


def migliore(letture, precedenza=PRECEDENZA):
    """La lettura che vince fra le plausibili (`plausibili`): il costo piu'
    basso, ma quella di prima (`prima`), se c'e', a meno di `precedenza`.
    None se nessuna vale."""
    valide = plausibili(letture)
    if not valide:
        return None
    best = min(valide, key=lambda l: l.costo)
    prima = next((l for l in valide if l.prima), None)
    if prima is not None and prima.costo <= best.costo + precedenza:
        return prima
    return best


def perche_no(d, letture):
    """L'errore quando nessuna lettura vale: quello di prima - la condizione
    mancata della lettura che si faceva, o la sequenza delle fasce che non e'
    nessuna forma - e dopo quante se ne sono provate, con la piu' vicina e il
    motivo per cui e' scartata."""
    fasce = [round(r[2] * PT2MM, 1) for r in _fasce_del_corpo(d)]
    serie = [l for l in letture if not l.correzioni]
    primo = next((l for l in serie if l.forma in ("chiuso", "aperto")), None)
    if primo is not None:
        msg = primo.scartata
    else:
        msg = ("astuccio: la sequenza delle fasce non e' ne' quella di un "
               "astuccio chiuso (retro e fronte alti uguali) ne' quella di uno "
               "aperto (cielo e fondo uguali attorno a una faccia sola). "
               "Fasce (mm): %s" % fasce)
    for l in letture:
        if l.valida and not l.prima and l.geometrico > COSTO_MAX:
            l.scartata = ("non torna: costo %.1f oltre %.1f (%s)" % (
                l.geometrico, COSTO_MAX, ", ".join("%s %.1f" % kv for kv in
                                                   sorted(l.voci.items(),
                                                          key=lambda kv: -kv[1])[:3])))
    altre = [l for l in letture if l is not primo and l.scartata]
    if altre:
        con_costo = [l for l in altre if l.d is not None]
        vicina = (min(con_costo, key=lambda l: l.costo) if con_costo
                  else altre[0])
        msg += (" Provate %d letture, nessuna vale; la piu' vicina, %s %s, "
                "e' scartata: %s" % (len(letture), vicina.forma,
                                     "(%s)" % "; ".join(vicina.correzioni)
                                     if vicina.correzioni else "di serie",
                                     vicina.scartata[:160]))
    return msg


def _applica(l):
    """L'astuccio della lettura scelta, con scritto come e' stato letto."""
    d = l.d
    d.forma, d.correzioni = l.forma, tuple(l.correzioni)
    d.costo, d.voci, d.strada = l.costo, dict(l.voci), l.strada
    return d


def solve_carton(d: Dieline) -> Dieline:
    """Ruoli dei pannelli di un astuccio a fasciatura verticale: la lettura
    migliore fra le candidate (`letture_carton`, `migliore`).

    Due famiglie, e la fustella dice quale: chiuso, con retro e fronte della
    stessa altezza, oppure aperto, con una faccia grande sola; e il fondo a
    tetto. Vedi `_chiuso`, `_aperto` e `_tetto`. Se nessuna lettura vale,
    l'errore dice le fasce e la lettura piu' vicina (`perche_no`).
    """
    letture = letture_carton(d)
    l = migliore(letture)
    if l is None:
        raise ValueError(perche_no(d, letture))
    return _applica(l)


def _alternating_run(widths, tol=0.06, contrast=0.12):
    """Cerca W D W D: due larghe uguali alternate a due strette uguali."""
    for i in range(len(widths) - 3):
        a, b, c, e = widths[i:i + 4]
        if max(a, c) == 0 or max(b, e) == 0:
            continue
        if (abs(a - c) / max(a, c) < tol and abs(b - e) / max(b, e) < tol
                and abs(a - b) / max(a, b) > contrast):
            return i
    return None


def detect_layout(d: Dieline):
    """Verso di fasciatura, dedotto dalla struttura e non imposto a priori.

    hwrap: la fascia piu' alta contiene FRONTE-FIANCO-RETRO-FIANCO in fila.
    vwrap: i pannelli principali sono impilati e i fianchi stanno ai lati.
    """
    rows = [(d.ys[i], d.ys[i + 1], d.ys[i + 1] - d.ys[i])
            for i in range(len(d.ys) - 1)]
    body = max(rows, key=lambda r: r[2])
    lo, hi = d.row_extent(body[0], body[1])
    cols = d.cols_in_row(body[0], body[1], cover=0.96)
    for v in (lo, hi):
        if not any(abs(v - x) < 3.5 for x in cols):
            cols.append(v)
    cols.sort()
    widths = [cols[i + 1] - cols[i] for i in range(len(cols) - 1)]
    start = _alternating_run(widths)
    if start is not None:
        return "hwrap", {"row": body, "cols": cols, "start": start}
    return "vwrap", {}


_PREVIEW = stato.per_lavoro({})


def _ink(pdf_path, box, page_no=0, dpi=72):
    """Densita' di grafica di una zona, misurata come croma media.

    Non si puo' usare la semplice copertura: i tratteggi tecnici delle zone
    print-free coprono molta superficie ma sono quasi acromatici, mentre la
    grafica vera e' satura."""
    import numpy as np
    sc = dpi / 72.0
    key = (pdf_path, page_no, dpi)
    if key not in _PREVIEW:
        _PREVIEW[key] = render_page(pdf_path, page_no, sc)
    im = _PREVIEW[key]
    c = im.crop(tuple(round(v * sc) for v in box))
    if c.width < 2 or c.height < 2:
        return 0.0
    a = np.asarray(c).astype(int)
    return float((a.max(2) - a.min(2)).mean())


def solve_carton_h(d: Dieline, pdf_path=None) -> Dieline:
    """Astuccio a fasciatura orizzontale: FRONTE-FIANCO-RETRO-FIANCO in fila,
    patta di incollaggio a un'estremita', alette sopra e sotto."""
    _, info = detect_layout(d)
    body, cols, i = info["row"], info["cols"], info["start"]
    y0, y1 = body[0], body[1]
    quad = [(cols[i + k], cols[i + k + 1]) for k in range(4)]

    # Profondita': la media dei due pannelli stretti, dovunque stiano.
    Dpt = min((quad[0][1] - quad[0][0]) + (quad[2][1] - quad[2][0]),
              (quad[1][1] - quad[1][0]) + (quad[3][1] - quad[3][0])) / 2.0

    def flap(x0, x1, side):
        """Aletta di chiusura: si prende il bordo piu' esterno compatibile con
        la profondita' della scatola, non la prima riga incontrata."""
        rs = d.rows_in_col(x0, x1)
        cand = [y for y in rs if (y < y0 - 3.5 if side == "top" else y > y1 + 3.5)]
        cand = [y for y in cand
                if abs((y0 - y) if side == "top" else (y - y1)) <= Dpt * 1.3]
        if not cand:
            return None
        return min(cand) if side == "top" else max(cand)

    # Dei due pannelli larghi, il fronte e' quello la cui aletta superiore e'
    # stampata: e' quella che diventa il cielo visibile della scatola.
    # La fila puo' cominciare da un fianco (FIANCO-RETRO-FIANCO-FRONTE): i
    # pannelli larghi sono allora il secondo e il quarto, e il giro dei nomi
    # parte da li'. Fronte e retro sono sempre i due larghi.
    w0 = quad[0][1] - quad[0][0]
    w1 = quad[1][1] - quad[1][0]
    s = 1 if w0 < w1 else 0
    order = [s, s + 1, (s + 2) % 4, (s + 3) % 4]
    if pdf_path:
        def flap_ink(k):
            x0, x1 = quad[k]
            y = flap(x0, x1, "top")
            return -1.0 if y is None else _ink(pdf_path, (x0, y, x1, y0))
        ka, kb = order[0], order[2]
        a, b = flap_ink(ka), flap_ink(kb)
        if max(a, b) < 3.0:                      # entrambe le alette neutre
            x0, x1 = quad[ka]; a = _ink(pdf_path, (x0, y0, x1, y1))
            x0, x1 = quad[kb]; b = _ink(pdf_path, (x0, y0, x1, y1))
        if b > a * 1.25 and b > a + 4.0:
            order = order[2:] + order[:2]
    names = ["front", "right", "back", "left"]
    P = {}
    for name, k in zip(names, order):
        x0, x1 = quad[k]
        P[name] = Panel(x0, y0, x1, y1, name)

    fx0, fx1 = quad[order[0]]
    yt, yb = flap(fx0, fx1, "top"), flap(fx0, fx1, "bottom")
    if yt is None and yb is None:
        bx0, bx1 = quad[order[2]]
        curvo = _fronte_curvo(d, (fx0, fx1), (bx0, bx1), y0, y1, Dpt)
        if curvo:
            yt, yb, d.curva_mm = curvo
    if yt is not None:
        P["top"] = Panel(fx0, yt, fx1, y0, "top")
    if yb is not None:
        P["bottom"] = Panel(fx0, y1, fx1, yb, "bottom")

    d.panels = P
    d.kind = "carton"
    d.layout = "hwrap"
    W = (P["front"].w_mm + P["back"].w_mm) / 2
    D = (P["left"].w_mm + P["right"].w_mm) / 2
    d.dims_mm = (round(W, 1), round(P["front"].h_mm, 1), round(D, 1))
    return d


def _fronte_curvo(d: Dieline, fronte, retro, y0, y1, Dpt):
    """Il fronte curvo (il "mastello"): `(y aletta alta, y aletta bassa,
    freccia mm)`, o None.

    Su un astuccio a fronte curvo il fronte si incurva verso fuori, i fianchi
    restano piani e il cielo e il fondo sono a D: profondi quanto la scatola
    ai lati e di piu' in mezzo. Le alette del fronte che li chiudono sono
    allora piu' lunghe della profondita' - quanto la freccia - e nessuna
    piega a D le divide. Lo si riconosce da due misure indipendenti che
    devono tornare insieme:

    - le alette alta e bassa del fronte sono lunghe uguali, piu' di 1,3 e
      meno di 2,5 volte la profondita': la freccia e' quello che avanza;
    - il fronte e' piu' largo del retro di quanto un arco con quella freccia
      e' piu' lungo della sua corda (8 f^2 / 3 c), entro un millimetro.
    """
    fx0, fx1 = fronte
    rs = d.rows_in_col(fx0, fx1)
    alto = [y for y in rs if Dpt * 1.3 < (y0 - y) <= Dpt * 2.5]
    basso = [y for y in rs if Dpt * 1.3 < (y - y1) <= Dpt * 2.5]
    if not alto or not basso:
        return None
    yt, yb = max(alto), min(basso)          # la piu' vicina al fronte
    lt, lb = (y0 - yt) * PT2MM, (yb - y1) * PT2MM
    if abs(lt - lb) > 0.1 * max(lt, lb):
        return None
    D = Dpt * PT2MM
    freccia = (lt + lb) / 2.0 - D
    corda = (retro[1] - retro[0]) * PT2MM
    largo = (fx1 - fx0) * PT2MM
    arco = corda + 8.0 * freccia ** 2 / (3.0 * corda)
    if largo - corda < 0.5 or abs(largo - arco) > 1.0:
        return None
    return yt, yb, round(freccia, 1)


def dichiara_apertura(d: Dieline):
    """Come e' aperto il retro, se e' aperto.

    Non e' un difetto, e' una dichiarazione: chi guarda il modello deve sapere
    che il retro e' aperto per costruzione e non per errore.
    """
    if d.chiuso:
        return None
    falde = [k for k in ("back_top", "back_bottom") if k in d.panels]
    if not falde:
        return "astuccio senza retro: aperto sul dietro, tipo vassoio"
    return ("retro aperto: lo chiudono %d falde (%s mm) e in mezzo resta una "
            "finestra alta %.1f mm"
            % (len(falde),
               " + ".join("%.1f" % d.panels[k].h_mm for k in falde),
               d.finestra_mm))


def check(d: Dieline):
    """Controlli di coerenza: se qualcosa non torna e' meglio saperlo."""
    msgs = []
    W, H, D = d.dims_mm
    P = d.panels
    if "front" in P and "back" in P:
        e = abs(P["front"].w_mm - P["back"].w_mm)
        if e > 2.0:
            msgs.append(f"fronte e retro differiscono di {e:.1f} mm")
    if "left" in P and "right" in P:
        e = abs(P["left"].w_mm - P["right"].w_mm)
        if e > 2.0:
            msgs.append(f"i due fianchi differiscono di {e:.1f} mm")
    for k in ("top", "bottom"):
        if k == "bottom" and d.tetto:
            # le falde del fondo a tetto sono piu' corte della profondita'
            # apposta: vanno su per la cresta, non stese (`_tetto`)
            continue
        if k in P:
            depth = P[k].h_mm if d.layout != "vwrap" else P[k].h_mm
            # col fronte curvo l'aletta e' lunga quanto il cielo in mezzo
            if abs(depth - D - d.curva_mm) / max(D, 1) > 0.06:
                msgs.append(f"aletta '{k}' profonda {depth:.1f} mm contro "
                            f"{D:.1f} mm di scatola: texture riscalata")
    for k in ("front", "back", "left", "right"):
        if k in P and abs(P[k].h_mm - H) / max(H, 1) > 0.03:
            msgs.append(f"'{k}' alto {P[k].h_mm:.1f} mm contro {H:.1f} mm")
    apertura = dichiara_apertura(d)
    if apertura:
        msgs.append(apertura)
    return msgs


def analyze(pdf_path: str, kind: str | None = None) -> Dieline:
    d = extract(pdf_path)
    d.kind = kind or classify(d)
    if d.kind in ("carton", "unknown"):
        layout, _ = detect_layout(d)
        if layout == "hwrap":
            d = solve_carton_h(d, pdf_path)
        else:
            d = solve_carton(d)
            d.layout = "vwrap"
    return d
