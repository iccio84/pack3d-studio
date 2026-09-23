"""
Analisi del disegno tecnico (fustella) contenuto in un artwork PDF.

Estrae la geometria vettoriale, isola il tratto della fustella, ricostruisce la
griglia di cordonature e i pannelli, classifica la tipologia di packaging e
ricava le quote L x H x P in millimetri.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict

import pdfplumber

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

    def rows_in_col(self, x0, x1, cover=0.8):
        """Cordonature orizzontali che attraversano davvero la colonna."""
        need = (x1 - x0) * cover
        out = []
        for y in self.ys:
            span = 0.0
            for cy, a, b in self.hsegs:
                if abs(cy - y) < 2.5:
                    span += max(0.0, min(b, x1) - max(a, x0))
            if span >= need:
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
_RESA = {}


def render_page(pdf_path, page_no: int = 0, scale: float = 1.0):
    """Rasterizza la pagina nel telaio del MediaBox, quello di pdfplumber.

    pdfium rende il CropBox, pdfplumber misura sul MediaBox. Finche' i due
    riquadri coincidono non si vede la differenza, e su quasi tutte le tavole
    coincidono. Quando no — su K Tronky il CropBox e' 459 x 271 pt dentro un
    MediaBox di 1332 x 958, spostato di (419, 471) — le coordinate dei segmenti
    indicizzano un raster che comincia da un'altra parte: nessuna eccezione,
    solo misure prese nel posto sbagliato.
    """
    import pypdfium2 as pdfium
    from PIL import Image

    # Una pagina, una rasterizzazione. Il flusso ne chiedeva TRE della stessa
    # pagina a risoluzioni diverse - 100 dpi per trovare il blocco stampato,
    # 150 per l'analisi, quella della texture per la grafica - e su Colazione
    # erano 30 secondi su 40 e tre picchi di memoria sovrapposti.
    #
    # Si tiene l'ultima resa e si SCENDE soltanto: una riduzione e' una media
    # di pixel che ci sono gia', un ingrandimento sarebbe invenzione. Se
    # qualcuno chiede piu' risoluzione di quella in cassa si rasterizza di
    # nuovo e si sostituisce.
    chiave = (pdf_path, page_no)
    vecchia = _RESA.get(chiave)
    if vecchia is not None and vecchia[0] >= scale - 1e-9:
        avuta, im = vecchia
        if abs(avuta - scale) < 1e-9:
            return im
        larg = max(1, int(round(im.width * scale / avuta)))
        alt = max(1, int(round(im.height * scale / avuta)))
        return im.resize((larg, alt), Image.LANCZOS)

    page = pdfium.PdfDocument(pdf_path)[page_no]
    page.set_cropbox(*page.get_mediabox())
    im = page.render(scale=scale).to_pil().convert("RGB")
    # una sola pagina in cassa: il server costruisce un modello alla volta
    _RESA.clear()
    _RESA[chiave] = (scale, im)
    return im


def scarta_resa():
    """Butta la pagina rasterizzata tenuta in cassa.

    Va chiamata appena l'ultimo che la usa ha preso la sua copia: tenerla
    viva oltre costa quanto pesa (41 MB su un foglio come Colazione) proprio
    mentre la costruzione alloca la texture.
    """
    _RESA.clear()


def _segments(page):
    """Segmenti H/V stroked della pagina: (orient, coord, a, b, stile)."""
    segs = []

    def add(x0, y0, x1, y1, style):
        if abs(x1 - x0) < 0.7 and abs(y1 - y0) > 1.0:
            segs.append(("V", (x0 + x1) / 2, min(y0, y1), max(y0, y1), style))
        elif abs(y1 - y0) < 0.7 and abs(x1 - x0) > 1.0:
            segs.append(("H", (y0 + y1) / 2, min(x0, x1), max(x0, x1), style))

    def style_of(o):
        return (round(o.get("linewidth") or 0, 2), str(o.get("stroking_color")))

    for ln in page.lines:
        add(ln["x0"], ln["top"], ln["x1"], ln["bottom"], style_of(ln))
    # i riquadri dell'artwork compaiono come coppia contorno+riempimento sullo
    # stesso bbox: un tratto di fustella non e' mai anche riempito.
    filled = [(r["x0"], r["top"], r["x1"], r["bottom"])
              for r in page.rects if r.get("fill")]

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
        if not cv.get("stroke"):
            continue
        st = style_of(cv)
        pts = cv.get("pts") or []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            add(ax, ay, bx, by, st)
    return segs


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


def _largest_cluster(segs, gap=25.0):
    """Isola il gruppo di segmenti spazialmente connesso piu' esteso: scarta
    cartigli, legende e disegni di riepilogo posti a lato della fustella."""
    if not segs:
        return segs
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
    main = max(groups.values(), key=lambda g: sum(x[0][3] - x[0][2] for x in g))
    mx0 = min(b[0] for _, b in main); my0 = min(b[1] for _, b in main)
    mx1 = max(b[2] for _, b in main); my1 = max(b[3] for _, b in main)

    def inside(g):
        """Se questo gruppo fa parte della fustella o e' roba di fianco.

        Le alette con fianchi obliqui non toccano il corpo con tratti H/V:
        restano gruppi a se', sporgono dall'ingombro da un lato e sono
        contenute nell'altro. Per quelle il test su un asse solo va bene.

        Contenuto in un asse pero' NON basta, ed e' quello che rompeva gli
        astucci con due viste sul foglio. Sul Kinder Pingui T6 la pagina porta
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

    out = []
    for g in groups.values():
        if g is main or inside(g):
            out.extend(sg for sg, _ in g)
    return out


# Quanto deve valere una penna, in frazione della migliore, per contare come
# fustella. Misurato: su tutti gli artwork del parco la penna di fustella e'
# una sola e sta a 1,00; sul Kinder Pingui T6 ce n'e' una seconda a 0,14 - un
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


def extract(pdf_path: str, page_no: int = 0) -> Dieline:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_no]
        all_segs = _segments(page)
        pens = _technical_pens(all_segs, page.width, page.height)
        segs = [s for s in all_segs if s[4] in pens] or all_segs
        segs = _largest_cluster(segs)
        # Fra le penne tecniche tenute qui sopra ce ne puo' essere una che non
        # e' fustella: si scarta adesso, dopo il raggruppamento spaziale, cioe'
        # guardando solo quello che sta sulla fustella.
        fustella = penne_di_fustella(segs, page.width, page.height)
        if fustella:
            segs = [s for s in segs if s[4] in fustella] or segs

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
        for kind, c, a, b, st in segs:
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
        d = Dieline(page.width, page.height, bbox, xs, ys)
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


def _fasce_del_corpo(d):
    """Le fasce della fasciatura, lette sulla colonna del corpo.

    Le `ys` del foglio sono l'unione di TUTTE le cordonature, e ci finisce
    anche quello che non piega il corpo. Sul Kinder Pingui T6 una linea a 27 mm
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
    return [(ys[i], ys[i + 1], ys[i + 1] - ys[i]) for i in range(len(ys) - 1)]


def _chiuso(rows, tol=3.0):
    """Ruoli di [aletta] RETRO - CIELO - FRONTE - FONDO, per indice di fascia.

    Retro e fronte sono la stessa faccia vista da due parti, e hanno la STESSA
    altezza: se le due fasce piu' alte non l'hanno, questa non e' la lettura
    giusta. Su un Kinder Pingui T6 il solutore prendeva 40,5 e 125 e ne faceva
    la media, 82,8, che non e' l'altezza di niente.
    """
    if len(rows) < 3:
        return None
    order = sorted(range(len(rows)), key=lambda i: -rows[i][2])
    back_i, front_i = sorted(order[:2])
    hb, hf = rows[back_i][2] * PT2MM, rows[front_i][2] * PT2MM
    if abs(hb - hf) > max(tol, 0.08 * max(hb, hf)):
        return None
    r = {"back": back_i, "front": front_i, "fianchi": back_i}
    if front_i - back_i > 1:
        r["top"] = max(range(back_i + 1, front_i), key=lambda i: rows[i][2])
    if front_i + 1 < len(rows):
        r["bottom"] = front_i + 1
    return r


def _aperto(rows, tol=1.5):
    """Ruoli di un astuccio che non si chiude: CIELO - FRONTE - FONDO.

    Un astuccio non e' obbligato ad avere il retro. Un vassoio non ce l'ha per
    definizione; un pack con finestra ce l'ha a meta', chiuso da due falde che
    lasciano un'apertura in mezzo da cui si vede il prodotto - il Kinder Pingui
    T6 e' cosi'. La firma in fustella e' una faccia grande sola, con cielo e
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


def solve_carton(d: Dieline) -> Dieline:
    """Ruoli dei pannelli di un astuccio a fasciatura verticale.

    Due famiglie, e la fustella dice quale: chiuso, con retro e fronte della
    stessa altezza, oppure aperto, con una faccia grande sola. Vedi `_chiuso` e
    `_aperto`.
    """
    rows = _fasce_del_corpo(d)
    ruoli = _chiuso(rows) or _aperto(rows)

    def fasce():
        """Le fasce misurate, per gli errori: senza numeri non si diagnostica."""
        return [round(r[2] * PT2MM, 1) for r in rows]

    if ruoli is None:
        raise ValueError(
            "astuccio: la sequenza delle fasce non e' ne' quella di un "
            "astuccio chiuso (retro e fronte alti uguali) ne' quella di uno "
            "aperto (cielo e fondo uguali attorno a una faccia sola). "
            "Fasce (mm): %s" % fasce())

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
        # qualunque flowpack steso: su Colazione la fascia grande e' il nastro,
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

    W = P["front"].w_mm
    d.panels = P
    d.kind = "carton"
    d.dims_mm = (round(W, 1), round(H, 1), round(D, 1))
    return d


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


_PREVIEW = {}


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

    # Dei due pannelli larghi, il fronte e' quello la cui aletta superiore e'
    # stampata: e' quella che diventa il cielo visibile della scatola.
    Dpt = ((quad[1][1] - quad[1][0]) + (quad[3][1] - quad[3][0])) / 2.0

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
    order = [0, 1, 2, 3]
    if pdf_path:
        def flap_ink(k):
            x0, x1 = quad[k]
            y = flap(x0, x1, "top")
            return -1.0 if y is None else _ink(pdf_path, (x0, y, x1, y0))
        a, b = flap_ink(0), flap_ink(2)
        if max(a, b) < 3.0:                      # entrambe le alette neutre
            x0, x1 = quad[0]; a = _ink(pdf_path, (x0, y0, x1, y1))
            x0, x1 = quad[2]; b = _ink(pdf_path, (x0, y0, x1, y1))
        if b > a * 1.25 and b > a + 4.0:
            order = [2, 3, 0, 1]
    names = ["front", "right", "back", "left"]
    P = {}
    for name, k in zip(names, order):
        x0, x1 = quad[k]
        P[name] = Panel(x0, y0, x1, y1, name)

    fx0, fx1 = quad[order[0]]
    yt, yb = flap(fx0, fx1, "top"), flap(fx0, fx1, "bottom")
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
        if k in P:
            depth = P[k].h_mm if d.layout != "vwrap" else P[k].h_mm
            if abs(depth - D) / max(D, 1) > 0.06:
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
