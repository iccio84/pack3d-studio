"""
La coppa di carta col tappo: sleeve conico, fondo, e tappo a corpo e anello.

E' la coppa da gelato dei Nutella POT, e arriva in DUE PDF: il contenitore
(sleeve e fondo) e il tappo (corpo e anello). Ognuno ha il suo disegno
tecnico in grande - lo steso, con la grafica sopra - e una miniatura del
disegno Ferrero con la vista MONTATA.

Le due cose dicono cose diverse, e servono tutte e due:

- lo **steso** dice dove sta la grafica. Lo sleeve e' un settore anulare
  (`cup.fit_sector`); la piega del fondo e' l'arco concentrico del DT piu'
  vicino al taglio di sotto; i lati di taglio sono due rette. Il corpo del
  tappo e' un cerchio con le sue cordonature, l'anello un rettangolo;
- la **vista montata** dice la forma: altezza, bocca, fondo, bordo arrotolato
  e rientro del fondo della coppa, e la sezione del tappo. E' in miniatura e
  le sue quote sono vettorializzate - le legge solo un occhio - ma i tratti
  no: quelli si misurano. La scala viene dai cerchi del fondo (o del corpo
  del tappo), che il foglio disegna in grande e in miniatura: il rapporto
  fra i due e' la scala, e torna su ogni anello.

La coppa e' il solido di rivoluzione del profilo misurato, e la grafica ci
si posa sopra SENZA STIRARLA: ogni altezza della parete prende l'arco dello
steso che sta alla stessa distanza dalla piega, e lungo quell'arco tanta
carta quanta e' la circonferenza della coppa li', a partire dal lato di
taglio sinistro. Quello che avanza e' il sormonto incollato sotto il lembo:
non si impone, si misura - e deve tornare con la riga che il DT gli
disegna. Sul Nutella POT avanzano 8,6 mm al fondo e 7,7 alla bocca, e il DT
ha la riga a 8,05.
"""
from __future__ import annotations

import ctypes
import math
import threading
from dataclasses import dataclass, field

import numpy as np

from . import cup as cupmod
from . import tracciati as tr

PT2MM = 25.4 / 72.0

# Lo spessore del cartoncino: 260 g/m2 piu' 15 micron di PE, dal cartiglio
# del DT. Le quote della vista montata sono ESTERNE: la carta sta mezzo
# spessore piu' dentro, ed e' su quella linea che la circonferenza si misura.
CARTA = 0.35
# Il rovescio e le zone neutre: carta bianca col PE, non stampata.
BIANCO = (242, 240, 235)
NERO = "(0, 0, 0)"
ROSSO = "(255, 0, 0)"

# Quanti lati ha la coppa attorno all'asse. A 256 la corda piu' lunga, alla
# bocca, sta 0,03 mm dentro l'arco: non si vede, e la grafica non ne risente
# perche' le UV si calcolano vertice per vertice sull'arco vero.
LATI = 256


# --------------------------------------------------------------------------- #
# i tracciati della pagina, anche dentro i form
# --------------------------------------------------------------------------- #
@dataclass
class Traccia:
    P: np.ndarray            # punti in pt, telaio di misura (y dall'alto)
    tratto: tuple | None     # (spessore, colore) del tratto, o None
    pieno: str | None        # colore del riempimento, o None

    @property
    def colore(self):
        return self.tratto[1] if self.tratto else self.pieno


def _bezier(p0, p1, p2, p3, n=12):
    t = np.linspace(0.0, 1.0, n + 1)[1:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return list(map(tuple, (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
                    + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3))


# Le ultime pagine lette: chi riconosce il PDF e chi lo costruisce lo
# leggono tutti e due, e sullo sleeve del Nutella POT sono 3,5 secondi. Due
# bastano - lo sleeve e il tappo - e piu' di due restano in memoria per niente.
_LETTE = {}
_LETTE_MAX = 2
_LETTE_CHIAVE = threading.Lock()


def tracce(pdf, page_no=0):
    """`_tracce` con memoria: la stessa pagina dello stesso file non si
    rilegge. La chiave porta dimensione e data del file, perche' un file
    temporaneo puo' riprendere il nome di uno cancellato."""
    import os
    try:
        st = os.stat(pdf)
        chiave = (pdf, page_no, st.st_mtime_ns, st.st_size)
    except OSError:
        return _tracce(pdf, page_no)
    with _LETTE_CHIAVE:
        T = _LETTE.get(chiave)
    if T is None:
        T = _tracce(pdf, page_no)
        with _LETTE_CHIAVE:
            while len(_LETTE) >= _LETTE_MAX:
                _LETTE.pop(next(iter(_LETTE)))
            _LETTE[chiave] = T
    return T


def _tracce(pdf, page_no=0):
    """Ogni sottotracciato della pagina, appiattito, con tratto e pieno.

    Le miniature dei disegni Ferrero stanno spesso dentro un form, e
    `cup.flatten_paths` legge solo il flusso della pagina: qui si scende
    nei form componendo le matrici, come fa `tracciati`. Le bezier si
    appiattiscono in 12 tratti: sui cerchi della miniatura il raggio torna
    al millesimo di punto.
    """
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    doc = pdfium.PdfDocument(pdf)
    out = []
    x, y = ctypes.c_float(), ctypes.c_float()
    try:
        page = doc[page_no]

        def visita(o, t, m):
            if t != raw.FPDF_PAGEOBJ_PATH:
                return
            n = raw.FPDFPath_CountSegments(o)
            if not n:
                return
            fill, stroke = ctypes.c_int(), ctypes.c_int()
            raw.FPDFPath_GetDrawMode(o, ctypes.byref(fill), ctypes.byref(stroke))
            if not fill.value and not stroke.value:
                return
            tratto = tr._stile(o) if stroke.value else None
            pieno = (tr._colore(o, raw.FPDFPageObj_GetFillColor)
                     if fill.value else None)
            a, b, c, d, e, f = tr._componi(m, tr._matrice(o))
            cur, curva = [], []
            for k in range(n):
                seg = raw.FPDFPath_GetPathSegment(o, k)
                if not seg:
                    continue
                tipo = raw.FPDFPathSegment_GetType(seg)
                raw.FPDFPathSegment_GetPoint(seg, ctypes.byref(x), ctypes.byref(y))
                p = (a * x.value + c * y.value + e, b * x.value + d * y.value + f)
                if tipo == raw.FPDF_SEGMENT_MOVETO:
                    if len(cur) >= 2:
                        out.append(Traccia(np.array(cur), tratto, pieno))
                    cur, curva = [p], []
                elif tipo == raw.FPDF_SEGMENT_BEZIERTO:
                    curva.append(p)
                    if len(curva) == 3 and cur:
                        cur.extend(_bezier(cur[-1], *curva))
                        curva = []
                else:
                    cur.append(p)
                if raw.FPDFPathSegment_GetClose(seg) and cur:
                    cur.append(cur[0])
            if len(cur) >= 2:
                out.append(Traccia(np.array(cur), tratto, pieno))

        tr._pagina(page, visita)
    finally:
        doc.close()
    return out


# --------------------------------------------------------------------------- #
# cerchi, anelli concentrici e la scala della miniatura
# --------------------------------------------------------------------------- #
def _cerchio(P):
    """(cx, cy, r, scarto massimo) del cerchio che passa meglio per i punti."""
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    sol = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
    cx, cy = sol[0], sol[1]
    r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
    return cx, cy, r, float(np.abs(np.hypot(x - cx, y - cy) - r).max())


def cerchi(T, minimo=2.0):
    """I tracciati chiusi che sono cerchi: [(cx, cy, r, colore)] in pt."""
    out = []
    for t in T:
        P = t.P
        if len(P) < 16:
            continue
        lato = max(np.ptp(P[:, 0]), np.ptp(P[:, 1]))
        if np.hypot(*(P[0] - P[-1])) > 0.02 * lato:
            continue
        cx, cy, r, s = _cerchio(P)
        if r < minimo or s > 0.003 * r + 0.005:
            continue
        ang = np.sort(np.arctan2(P[:, 1] - cy, P[:, 0] - cx))
        if np.max(np.diff(np.r_[ang, ang[0] + 2 * np.pi])) > math.radians(40):
            continue
        out.append((cx, cy, r, t.colore))
    return out


def anelli(C):
    """I cerchi raggruppati per centro: [[cx, cy, [r decrescenti], [colori]]]."""
    gruppi = []
    for cx, cy, r, col in sorted(C, key=lambda c: -c[2]):
        for g in gruppi:
            if math.hypot(g[0] - cx, g[1] - cy) <= max(0.5, 0.01 * g[2][0]):
                if all(abs(r - q) > 0.05 for q in g[2]):
                    g[2].append(r)
                    g[3].append(col)
                break
        else:
            gruppi.append([cx, cy, [r], [col]])
    return gruppi


def gemello(gruppi, tolleranza=0.004):
    """Il disegno grande e la sua miniatura: `(grande, piccolo, scala)`.

    Il grande e' il gruppo di anelli col cerchio piu' grande della pagina -
    il fondo della coppa, il corpo del tappo. Il gemello e' il gruppo piu'
    piccolo che ne ripete le PROPORZIONI: ogni anello del grande, diviso per
    il suo esterno, deve ritrovarsi nel piccolo entro lo 0,4%. Sul Nutella
    POT il fondo da' 87,5 / 72,5 / 67,2 mm e la miniatura gli stessi tre a
    1:8,169 (piu' il cerchio del Best Before, che in grande non e' un
    cerchio). `scala` e' in mm di pezzo per punto di miniatura. None se il
    gemello non c'e'.
    """
    if not gruppi:
        return None
    gruppi = sorted(gruppi, key=lambda g: -g[2][0])
    G = gruppi[0]
    rel = [r / G[2][0] for r in G[2]]
    meglio = None
    for g in gruppi[1:]:
        if g[2][0] > 0.6 * G[2][0]:
            continue
        rg = [r / g[2][0] for r in g[2]]
        presi = sum(1 for q in rel if any(abs(q - p) <= tolleranza for p in rg))
        if presi >= min(2, len(rel)) and (meglio is None or presi > meglio[0]):
            meglio = (presi, g)
    if meglio is None:
        return None
    g = meglio[1]
    return G, g, G[2][0] / g[2][0] * PT2MM


def _dritto(P):
    """`(a, b, scarto)`: gli estremi del tratto se e' una retta, in pt."""
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c, full_matrices=False)
    d = vt[0]
    t = (P - c) @ d
    scarto = float(np.abs((P - c) @ np.array([-d[1], d[0]])).max())
    return c + t.min() * d, c + t.max() * d, scarto


# --------------------------------------------------------------------------- #
# lo steso dello sleeve
# --------------------------------------------------------------------------- #
@dataclass
class Steso:
    cx: float                 # centro dei due archi, pt
    cy: float
    R1: float                 # raggio del taglio di sotto, mm
    R2: float                 # raggio del taglio della bocca, mm
    sx: tuple                 # lato di taglio sinistro: (punto, direzione) pt
    dx: tuple                 # lato di taglio destro
    piega: float              # mm: l'arco della piega del fondo
    archi: list               # mm: tutti gli archi concentrici del DT
    riquadro: tuple           # pt: il taglio
    resid: float              # mm: scarto del settore sul taglio
    note: list = field(default_factory=list)

    def fi(self, rho, lato):
        """L'angolo (rad) del lato di taglio sull'arco di raggio `rho` mm."""
        p, d = self.sx if lato == "sx" else self.dx
        q = np.asarray(p, float) - (self.cx, self.cy)
        d = np.asarray(d, float)
        R = rho / PT2MM
        b = float(np.dot(d, q))
        radice = math.sqrt(max(b * b - (float(np.dot(q, q)) - R * R), 0.0))
        # delle due intersezioni della retta col cerchio, quella vicina al
        # tratto misurato
        t = min((-b + radice, -b - radice), key=abs)
        P = q + t * d
        return math.atan2(P[1], P[0])

    def arco(self, rho):
        """La carta fra i due lati di taglio sull'arco di raggio `rho`, mm."""
        return rho * ((self.fi(rho, "dx") - self.fi(rho, "sx")) % (2 * math.pi))


def leggi_steso(T):
    """Lo steso dello sleeve, o None se sulla pagina non c'e' un settore.

    Il taglio e' il tracciato chiuso piu' grande che si adatta a un settore
    anulare con i due archi coerenti: `cup.fit_sector` restituisce due
    numeri, e quelli che i tratteggi del DT gli fanno passare con residuo
    0,02 mm hanno 9 gradi di scarto fra gli archi (REGOLE, *Coppe e
    contenitori conici*). Si guarda lo scarto prima del residuo.
    """
    candidati = []
    for t in T:
        P = t.P
        if t.tratto is None or len(P) < 40:
            continue
        lato = max(np.ptp(P[:, 0]), np.ptp(P[:, 1]))
        if lato < 100 or np.hypot(*(P[0] - P[-1])) > 0.01 * lato:
            continue
        candidati.append((np.ptp(P[:, 0]) * np.ptp(P[:, 1]), t))
    for _area, t in sorted(candidati, key=lambda c: -c[0])[:8]:
        try:
            s = cupmod.fit_sector(t.P)
        except Exception:
            continue
        if (s.ang_check > math.radians(2.0) or s.resid_mm > 1.5
                or not math.radians(5) < s.alpha < math.radians(200)
                or s.R2 - s.R1 < 20):
            continue
        return _completa_steso(T, t.P, s)
    return None


def _fitto(P, passo=1.0):
    """Il tracciato con un punto ogni `passo` pt: un lato dritto e' due punti
    soli, e senza i punti di mezzo non si misura."""
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(int(np.hypot(*(b - a)) / passo), 1)
        out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
    return np.concatenate(out)


def _completa_steso(T, P, s):
    P = _fitto(P)
    rho = np.hypot(P[:, 0] - s.cx, P[:, 1] - s.cy) * PT2MM
    fi = np.arctan2(P[:, 1] - s.cy, P[:, 0] - s.cx)
    # l'angolo del centro dello steso, e i lati misurati lontano dagli spigoli
    # arrotondati
    medio = math.atan2(np.sin(fi).mean(), np.cos(fi).mean())
    dfi = np.angle(np.exp(1j * (fi - medio)))
    banda = s.R2 - s.R1
    fianco = (rho > s.R1 + 0.2 * banda) & (rho < s.R2 - 0.2 * banda)
    lati = {}
    for nome, sel in (("sx", fianco & (dfi < 0)), ("dx", fianco & (dfi > 0))):
        Q = P[sel]
        if len(Q) < 2:
            raise ValueError("sleeve: il lato di taglio %s non si legge" % nome)
        a, b, _scarto = _dritto(Q)
        d = (b - a) / np.linalg.norm(b - a)
        lati[nome] = (tuple(a), tuple(d))
    # gli archi concentrici del DT: i tratti tutti alla stessa distanza dal
    # centro, lunghi almeno meta' dell'apertura
    archi = []
    for t in T:
        Q = t.P
        if t.tratto is None or len(Q) < 3:
            continue
        d = np.hypot(Q[:, 0] - s.cx, Q[:, 1] - s.cy) * PT2MM
        if d.std() > 0.03 or not s.R1 - 1 < d.mean() < s.R2 + 1:
            continue
        a = np.arctan2(Q[:, 1] - s.cy, Q[:, 0] - s.cx)
        if np.ptp(np.unwrap(a)) < 0.5 * s.alpha:
            continue
        r = float(d.mean())
        if all(abs(r - q) > 0.05 for q in archi):
            archi.append(r)
    archi.sort()
    note = []
    sotto = [r for r in archi if s.R1 + 0.5 < r < s.R1 + 0.25 * banda]
    if sotto:
        piega = sotto[0]
    else:
        # senza la cordonatura del fondo la piega si mette dove finisce la
        # carta di sotto: e' il caso peggiore, e si dichiara
        piega = s.R1
        note.append("SLEEVE SENZA PIEGA DEL FONDO NEL DT: la parete parte dal "
                    "taglio di sotto, la grafica puo' stare piu' in basso del "
                    "vero")
    x0, y0 = P.min(0)
    x1, y1 = P.max(0)
    return Steso(s.cx, s.cy, s.R1, s.R2, lati["sx"], lati["dx"], piega, archi,
                 (float(x0), float(y0), float(x1), float(y1)), s.resid_mm,
                 note)


# --------------------------------------------------------------------------- #
# la vista montata della coppa, dalla miniatura
# --------------------------------------------------------------------------- #
@dataclass
class Montata:
    altezza: float     # mm, dal fondo esterno al sommo del bordo
    r_fondo: float     # mm, raggio esterno alla base
    r_parete: float    # mm, raggio esterno in cima alla parete, sotto il bordo
    r_bordo: float     # mm, raggio esterno del bordo arrotolato
    ricciolo: float    # mm, altezza del bordo arrotolato
    rientro: float     # mm, dal fondo esterno al piano del fondo
    scala: float       # mm di pezzo per punto di miniatura
    pendenza: float    # rad, l'inclinazione della parete misurata

    @property
    def y_parete(self):
        return self.altezza - self.ricciolo

    def r(self, y):
        """Il raggio esterno della parete all'altezza `y`."""
        return self.r_fondo + (self.r_parete - self.r_fondo) * y / self.y_parete


def _neri(T, finestra):
    x0, y0, x1, y1 = finestra
    out = []
    for t in T:
        if t.tratto is None or t.tratto[1] != NERO:
            continue
        P = t.P
        if (P[:, 0].min() >= x0 and P[:, 0].max() <= x1
                and P[:, 1].min() >= y0 and P[:, 1].max() <= y1):
            out.append(t)
    return out


def leggi_montata(T, piccolo, scala, beta):
    """La coppa montata, dai tratti neri della vista accanto alla miniatura.

    Le pareti sono due rette nere inclinate di `beta` - l'angolo del cono che
    lo steso impone - e simmetriche: e' quello che le distingue dal resto
    della miniatura. Fra le due si leggono il sommo del bordo (il nero piu'
    alto), la riga sotto il ricciolo, il fondo esterno e il piano del fondo.
    None se la vista non si trova.
    """
    cx, cy, rr = piccolo[0], piccolo[1], piccolo[2][0]
    fin = (cx - 12 * rr, cy - 8 * rr, cx + 12 * rr, cy + 8 * rr)
    neri = _neri(T, fin)
    rette = []
    for t in neri:
        if len(t.P) < 2:
            continue
        a, b, scarto = _dritto(t.P)
        L = float(np.hypot(*(b - a)))
        if scarto > 0.05 or L * scala < 40.0:
            continue
        if a[1] > b[1]:
            a, b = b, a                    # a in alto
        inc = math.atan2(b[0] - a[0], b[1] - a[1])   # >0: scende verso destra
        rette.append((a, b, inc))
    sx = [r for r in rette if abs(r[2] - beta) < math.radians(1.5)]
    dx = [r for r in rette if abs(r[2] + beta) < math.radians(1.5)]
    coppie = []
    for a1, b1, i1 in sx:
        for a2, b2, i2 in dx:
            if abs(b1[1] - b2[1]) > 1.0 or abs(a1[1] - a2[1]) > 2.0:
                continue
            m_su = (a1[0] + a2[0]) / 2
            m_giu = (b1[0] + b2[0]) / 2
            if abs(m_su - m_giu) > 0.5 or a2[0] <= a1[0]:
                continue
            coppie.append((b2[0] - b1[0], (a1, b1, i1), (a2, b2, i2)))
    if not coppie:
        return None
    _w, (a1, b1, i1), (a2, b2, i2) = max(coppie, key=lambda c: c[0])
    xm = (a1[0] + a2[0] + b1[0] + b2[0]) / 4
    y_base = max(b1[1], b2[1])
    y_su = max(a1[1], a2[1])               # dove ci sono tutte e due le pareti
    largo_su = (a2[0] - a1[0]) / 2
    # i punti neri della coppa: fra le pareti allargate di un quarto
    pts = np.concatenate([t.P for t in neri])
    dentro = ((np.abs(pts[:, 0] - xm) <= largo_su * 1.25)
              & (pts[:, 1] >= y_su - 0.12 * (y_base - y_su))
              & (pts[:, 1] <= y_base + 0.5))
    pts = pts[dentro]
    y_sommo = float(pts[:, 1].min())
    # la riga sotto il ricciolo: l'orizzontale nera piu' bassa fra il sommo e
    # la cima delle pareti
    orizz = []
    for t in neri:
        P = t.P
        if np.ptp(P[:, 1]) > 0.05 or np.ptp(P[:, 0]) < 0.25 * largo_su:
            continue
        if np.abs(P[:, 0] - xm).max() > largo_su * 1.25:
            continue
        orizz.append((float(P[:, 1].mean()), float(P[:, 0].min()),
                      float(P[:, 0].max())))
    sotto_ricciolo = [y for y, _a, _b in orizz if y_sommo < y <= y_su + 0.3]
    y_ricciolo = max(sotto_ricciolo) if sotto_ricciolo else y_sommo
    bordo = pts[pts[:, 1] <= y_ricciolo + 0.05]
    r_bordo = float(np.abs(bordo[:, 0] - xm).max())
    # il piano del fondo: l'orizzontale (nera o rossa) piu' alta del gruppo
    # vicino alla base, fra le pareti
    piani = [y for y, a, b in orizz
             if y_base - 0.3 * (y_base - y_sommo) < y < y_base - 0.3]
    for t in T:
        if t.tratto is None or t.tratto[1] != ROSSO:
            continue
        P = t.P
        if (np.abs(P[:, 0] - xm).max() <= largo_su * 1.25
                and y_base - 0.3 * (y_base - y_sommo) < P[:, 1].min() < y_base - 0.3):
            piani.append(float(P[:, 1].min()))
    if piani:
        vicini = [y for y in piani if y >= max(piani) - 0.5]
        y_piano = min(vicini)
    else:
        y_piano = y_base

    def largo(y):
        """Mezza larghezza fra le pareti esterne all'altezza y."""
        def x(a, b):
            return a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1])
        return (x(a2, b2) - x(a1, b1)) / 2

    k = scala
    return Montata(altezza=(y_base - y_sommo) * k,
                   r_fondo=largo(y_base) * k,
                   r_parete=largo(y_ricciolo) * k,
                   r_bordo=r_bordo * k,
                   ricciolo=(y_ricciolo - y_sommo) * k,
                   rientro=(y_base - y_piano) * k,
                   scala=k,
                   pendenza=(i1 - i2) / 2)


# --------------------------------------------------------------------------- #
# il tappo
# --------------------------------------------------------------------------- #
@dataclass
class Tappo:
    centro: tuple          # centro del corpo sul foglio, pt
    r_taglio: float        # mm
    anelli: list           # mm: i raggi del corpo, decrescenti
    anello: tuple          # pt: il riquadro di stampa dell'anello
    righe: tuple           # pt: il riquadro delle righe, con l'abbondanza
    r_interno: float       # mm: la gonna, dentro
    altezza: float         # mm
    z_piano: float         # mm sotto il sommo: il piano del corpo
    fuori: np.ndarray      # [(z, r)] il profilo esterno, dal sommo in giu'
    scala: float
    note: list = field(default_factory=list)

    @property
    def r_piano(self):
        """La cordonatura del corpo che chiude il piano: quella piu' vicina al
        piano che la sezione misura, appena dentro la gonna."""
        dentro = [r for r in self.anelli if r < self.r_interno - 1.0]
        return dentro[0] if dentro else self.r_interno - 3.0


def _riquadro_anello(pdf, altezza_attesa):
    """Il rettangolo del DT alto quanto la gonna: l'area di stampa dell'anello.

    I quattro lati sono tratti del DT (stesso colore, a filo) che chiudono un
    rettangolo molto piu' largo che alto.
    """
    segs, _w, _h = tr.segmenti(pdf)
    H = [s for s in segs if s[0] == "H"]
    V = [s for s in segs if s[0] == "V"]
    meglio = None
    for i, h1 in enumerate(H):
        for h2 in H[i + 1:]:
            if abs(h1[2] - h2[2]) > 0.5 or abs(h1[3] - h2[3]) > 0.5:
                continue
            y0, y1 = sorted((h1[1], h2[1]))
            x0, x1 = h1[2], h1[3]
            alto = (y1 - y0) * PT2MM
            if (x1 - x0) < 3 * (y1 - y0) or alto < 3:
                continue
            lati = [v for v in V if abs(v[2] - y0) < 0.5 and abs(v[3] - y1) < 0.5
                    and (abs(v[1] - x0) < 0.5 or abs(v[1] - x1) < 0.5)]
            if len(lati) < 2:
                continue
            scarto = abs(alto - altezza_attesa)
            if meglio is None or scarto < meglio[0]:
                meglio = (scarto, (x0, y0, x1, y1))
    return meglio[1] if meglio else None


def _righe(T, riquadro):
    """Il riquadro della grafica dell'anello: i pieni che attraversano l'area
    di stampa, con l'abbondanza che hanno sopra e sotto."""
    x0, y0, x1, y1 = riquadro
    ys = [y0, y1]
    for t in T:
        if t.pieno is None:
            continue
        P = t.P
        if (P[:, 0].min() >= x0 - 30 and P[:, 0].max() <= x1 + 30
                and P[:, 1].min() <= y0 + 1 and P[:, 1].max() >= y1 - 1
                and np.ptp(P[:, 1]) < 3 * (y1 - y0)):
            ys += [float(P[:, 1].min()), float(P[:, 1].max())]
    return (x0, min(ys), x1, max(ys))


def leggi_tappo(pdf, T=None):
    """Il tappo: corpo e anello dallo steso, sezione dalla miniatura.

    La sezione e' l'unico posto che dice com'e' fatto il tappo montato: la
    gonna che scende sopra il bordo della coppa, la nervatura che ci si
    aggancia sotto, il gradino, il ricciolo che stringe il bordo del corpo,
    e il piano incassato. Si legge dai tratti neri: le orizzontali sono gli
    spigoli del giro visti di fronte (la piu' lunga e' l'interno della
    gonna), e il profilo esterno e' il nero piu' a sinistra a ogni altezza.
    """
    T = T if T is not None else tracce(pdf)
    gruppi = anelli(cerchi(T))
    g = gemello(gruppi)
    if g is None:
        raise ValueError("tappo: il corpo e la sua miniatura non si trovano "
                         "(servono i cerchi del corpo in grande e in piccolo)")
    G, piccolo, k = g
    raggi = [r * PT2MM for r in G[2]]
    # la sezione: le orizzontali nere lunghe quasi quanto il corpo in
    # miniatura, allineate su un asse
    D = 2 * piccolo[2][0]
    cx, cy = piccolo[0], piccolo[1]
    fin = (cx - 8 * D, cy - 6 * D, cx + 8 * D, cy + 6 * D)
    neri = _neri(T, fin)
    lunghe = []
    for t in neri:
        P = t.P
        if np.ptp(P[:, 1]) > 0.05:
            continue
        L = np.ptp(P[:, 0])
        if 0.80 * D <= L <= 0.99 * D:
            lunghe.append((float(P[:, 1].mean()), float(P[:, 0].min()),
                           float(P[:, 0].max())))
    assi = {}
    for y, a, b in lunghe:
        m = round((a + b) / 2, 0)
        assi.setdefault(m, []).append((y, a, b))
    righe = max(assi.values(), key=len) if assi else []
    if len(righe) < 3:
        raise ValueError("tappo: la sezione montata non si trova nella "
                         "miniatura")
    xm = float(np.mean([(a + b) / 2 for _y, a, b in righe]))
    L = max(b - a for _y, a, b in righe)
    ys = [y for y, _a, _b in righe]
    sez = [t for t in neri
           if np.abs(t.P[:, 0] - xm).max() <= 0.62 * L
           and t.P[:, 1].min() >= min(ys) - 0.05 * L
           and t.P[:, 1].max() <= max(ys) + 0.05 * L]
    # fitti: un lato dritto della sezione e' due punti soli
    pts = np.concatenate([_fitto(t.P, 0.01) for t in sez])
    y_su, y_giu = float(pts[:, 1].min()), float(pts[:, 1].max())
    r_int = L / 2 * k
    # il piano: il rosso del corpo, la sua riga piu' bassa; senza rosso, la
    # prima orizzontale corta sotto il ricciolo
    rossi = [t.P for t in T if t.tratto is not None and t.tratto[1] == ROSSO
             and np.abs(t.P[:, 0] - xm).max() <= 0.62 * L
             and y_su - 1 <= t.P[:, 1].min() and t.P[:, 1].max() <= y_giu + 1]
    if rossi:
        y_piano = max(float(P[:, 1].max()) for P in rossi)
    else:
        corte = sorted(y for y, a, b in righe if (b - a) < 0.97 * L)
        y_piano = corte[-1] if corte else y_su + 0.4 * (y_giu - y_su)
    # il profilo esterno: il nero piu' a sinistra (e a destra, specchiato) a
    # ogni altezza, ogni ventesimo di millimetro di pezzo
    passo = 0.05 / k
    fuori = []
    for y in np.arange(y_su, y_giu + passo / 2, passo):
        vicini = pts[np.abs(pts[:, 1] - y) <= passo]
        if not len(vicini):
            continue
        r = max(xm - vicini[:, 0].min(), vicini[:, 0].max() - xm)
        fuori.append(((y - y_su) * k, r * k))
    fuori = np.array(fuori)
    alto = (y_giu - y_su) * k
    anello = _riquadro_anello(pdf, alto)
    if anello is None:
        raise ValueError("tappo: l'area di stampa dell'anello non si trova nel "
                         "DT (un rettangolo alto quanto la gonna)")
    return Tappo(centro=(G[0], G[1]), r_taglio=raggi[0], anelli=raggi,
                 anello=anello, righe=_righe(T, anello), r_interno=r_int,
                 altezza=alto, z_piano=(y_piano - y_su) * k, fuori=fuori,
                 scala=k)


# --------------------------------------------------------------------------- #
# la coppa: steso, fondo e vista montata
# --------------------------------------------------------------------------- #
@dataclass
class Coppa:
    steso: Steso
    montata: Montata
    fondo: tuple            # (cx, cy, raggi mm) del fondo in grande
    note: list = field(default_factory=list)

    @property
    def parete(self):
        """La lunghezza della parete sulla generatrice, dalla piega al bordo."""
        m = self.montata
        return math.hypot(m.y_parete, m.r_parete - m.r_fondo)

    def sormonto(self, y):
        """La carta che avanza all'altezza `y`: va sotto il lembo, mm."""
        m = self.montata
        rho = self.steso.piega + self.parete * y / m.y_parete
        return self.steso.arco(rho) - 2 * math.pi * (m.r(y) - CARTA / 2)


def leggi_coppa(pdf, T=None):
    """Lo sleeve col fondo: lo steso e la coppa montata della miniatura."""
    T = T if T is not None else tracce(pdf)
    s = leggi_steso(T)
    if s is None:
        raise ValueError("coppa: sulla pagina non c'e' lo steso di uno sleeve "
                         "(un settore anulare)")
    g = gemello(anelli(cerchi(T)))
    if g is None:
        raise ValueError("coppa: il fondo e la sua miniatura non si trovano: "
                         "senza, la vista montata non ha la scala")
    G, piccolo, k = g
    # l'angolo del cono lo impone lo steso: sin(beta) = apertura / 2pi
    alpha = s.fi(0.5 * (s.R1 + s.R2), "dx") - s.fi(0.5 * (s.R1 + s.R2), "sx")
    beta = math.asin(min(alpha / (2 * math.pi), 0.99))
    m = leggi_montata(T, piccolo, k, beta)
    if m is None:
        raise ValueError("coppa: la vista montata non si trova accanto alla "
                         "miniatura del fondo")
    return Coppa(s, m, (G[0], G[1], [r * PT2MM for r in G[2]]))


def orienta(pdf):
    """`(pdf, cosa, gradi)`: il foglio nel verso in cui si legge, e che cos'e'.

    `cosa` e' 'coppa', 'tappo' o None; `pdf` e' il foglio girato di `gradi`
    in senso orario, se andava girato. Le viste montate si leggono DRITTE -
    pareti verticali, sezione orizzontale - e un foglio girato sulla tavola
    si gira prima di leggerlo, come gli astucci (`artwork.pagina_girata`).
    Lo sleeve il suo verso lo dice da se': la bocca sta sopra, dalla parte
    opposta al centro degli archi. Il tappo no: si prova girato finche' la
    sezione si trova, col piano nella meta' alta.
    """
    from . import artwork
    s = leggi_steso(tracce(pdf))
    if s is not None:
        rho = 0.5 * (s.R1 + s.R2)
        a, b = s.fi(rho, "sx"), s.fi(rho, "dx")
        mezzo = math.degrees(math.atan2(math.sin(a) + math.sin(b),
                                        math.cos(a) + math.cos(b)))
        # dritto, la mezzeria dello steso guarda in su: -90 gradi con la y
        # verso il basso
        gradi = int(round(-(mezzo + 90.0) / 90.0)) * 90 % 360
        return (artwork.pagina_girata(pdf, gradi) if gradi else pdf,
                "coppa", gradi)
    for gradi in (0, 180, 90, 270):
        q = artwork.pagina_girata(pdf, gradi) if gradi else pdf
        try:
            p = leggi_tappo(q)
        except ValueError:
            continue
        if p.z_piano < 0.5 * p.altezza:
            return q, "tappo", gradi
    return pdf, None, 0


def riconosci(pdf):
    """'coppa', 'tappo' o None: che cosa disegna questa pagina."""
    return orienta(pdf)[1]


# --------------------------------------------------------------------------- #
# le texture: tre ritagli dei due fogli in un atlante solo
# --------------------------------------------------------------------------- #
def ritagli(pdf, riquadri, dpi, regione, lastre_extra=()):
    """`({nome: immagine}, avvisi)`: i riquadri del foglio (pt) puliti.

    La stessa pulizia di tutti gli altri pack - livelli tecnici spenti, aree
    e GDA tolte, fuori dal DT via tutto - ma SENZA girare i ritagli sul verso
    della grafica come fa `texture_astuccio`: qui il verso lo dice la
    geometria, il settore e il cerchio, e un ritaglio girato sposterebbe la
    grafica fuori dalle sue UV.
    """
    from . import artwork, folding, nero
    from .dieline import Panel
    conti = {}
    pulito, lastre = artwork.senza_coperture(pdf, 0, lastre_extra,
                                             regione=regione, conti=conti)
    nero_deciso = nero.spia(pulito, 0, dpi / 72.0)
    avvisi = []
    fuori = artwork.avviso_fuori_dt(conti)
    if fuori:
        avvisi.append(fuori)
    avvisi.extend(artwork.avvisi_gda(conti))
    tex = folding.rasterize_panels(
        pulito, {k: Panel(*r, k) for k, r in riquadri.items()}, dpi=dpi,
        page_no=0, clean=True, note=avvisi, nero_deciso=nero_deciso)
    if lastre:
        avvisi.append("lastre tecniche e coperture tolte per nome: %s"
                      % ", ".join(lastre))
    return tex, avvisi


@dataclass
class Zona:
    """Un ritaglio dentro l'atlante: dove sta, e quale riquadro del foglio."""
    x: int
    y: int
    w: int
    h: int
    riquadro: tuple            # pt
    W: int = 1                 # misure dell'atlante, per normalizzare
    H: int = 1

    def uv(self, X, Y):
        """UV dell'atlante per i punti (X, Y) del foglio, in pt."""
        x0, y0, x1, y1 = self.riquadro
        px = self.x + (np.asarray(X) - x0) / (x1 - x0) * self.w
        py = self.y + (np.asarray(Y) - y0) / (y1 - y0) * self.h
        return px / self.W, py / self.H


def atlante(immagini, giri=None):
    """Mette le immagini in un atlante solo: `(atlante, {nome: Zona})`.

    `immagini` e' {nome: (PIL.Image, riquadro pt)}; l'anello va ripetuto,
    e `giri` dice quante volte, affiancato a se stesso. Lo sleeve sta sopra
    da solo, sotto il corpo del tappo, l'anello e la toppa bianca del
    rovescio. Fra i pezzi 16 pixel di margine, riempiti col colore del bordo,
    perche' il filtro della scheda video non peschi nel vicino.
    """
    from PIL import Image
    giri = giri or {}
    pad = 16
    pezzi = {}
    for nome, (im, riq) in immagini.items():
        n = giri.get(nome, 1)
        if n > 1:
            fila = Image.new("RGB", (im.width * n, im.height))
            for k in range(n):
                fila.paste(im, (k * im.width, 0))
            x0, y0, x1, y1 = riq
            riq = (x0, y0, x0 + (x1 - x0) * n, y1)
            im = fila
        pezzi[nome] = (im.convert("RGB"), riq)
    bianco = Image.new("RGB", (8, 8), BIANCO)
    pezzi["bianco"] = (bianco, (0.0, 0.0, 1.0, 1.0))
    # sopra lo sleeve; sotto, da sinistra, il corpo e una colonna con
    # l'anello e il bianco
    posti = {}
    x = y = 0
    alto = 0
    if "sleeve" in pezzi:
        im = pezzi["sleeve"][0]
        posti["sleeve"] = (0, 0)
        y = im.height + pad
    riga = ["corpo"] if "corpo" in pezzi else []
    for nome in riga:
        im = pezzi[nome][0]
        posti[nome] = (x, y)
        x += im.width + pad
        alto = max(alto, im.height)
    yy = y
    for nome in ("anello", "fondo", "bianco"):
        if nome in pezzi:
            im = pezzi[nome][0]
            posti[nome] = (x, yy)
            yy += im.height + pad
    alto = max(alto, yy - y)
    W = max(p[0] + pezzi[k][0].width for k, p in posti.items())
    H = max(p[1] + pezzi[k][0].height for k, p in posti.items())
    A = Image.new("RGB", (W + pad, H + pad), BIANCO)
    zone = {}
    for nome, (px, py) in posti.items():
        im, riq = pezzi[nome]
        # il margine: il bordo del pezzo allungato tutt'attorno
        largo = im.resize((im.width + 2 * pad, im.height + 2 * pad))
        A.paste(largo, (max(px - pad, 0), max(py - pad, 0)))
        A.paste(im, (px, py))
        zone[nome] = Zona(px, py, im.width, im.height, riq)
    for z in zone.values():
        z.W, z.H = A.size
    return A, zone


# --------------------------------------------------------------------------- #
# il fronte: dove sta il marchio sullo sleeve
# --------------------------------------------------------------------------- #
VIVO = 115     # max - min dei canali: i colori del marchio, non i fondi
# Quanto vicini devono stare due colori vivi per essere lo stesso marchio:
# il NEW sta 7 mm sopra la scritta nutella, il box "60" 20 mm a sinistra.
MARCHIO_STACCO = 4.0


def fronte(c, sleeve, riquadro):
    """`(frazione, gradi)`: dove sta il marchio sullo sleeve.

    `frazione` e' la frazione di giro (0..1 dal taglio sinistro) del
    baricentro del marchio, `gradi` lo stesso punto come angolo dello steso
    dalla sua mezzeria. `(None, 0)` se la grafica non ha colori vivi.

    Il fronte si ancora al baricentro angolare della grafica, non alla
    mezzeria del settore (REGOLE, *Coppe e contenitori conici*). Contano i
    colori VIVI - il marrone delle fasce gira tutto attorno e non dice
    niente - e di quelli il GRUPPO piu' grande, chiusi i buchi fra lettere
    vicine: e' il marchio. Il baricentro di tutti i colori vivi lo tirava
    verso il box "nutella 60" e il marchio usciva spostato a destra.
    """
    from scipy import ndimage
    s, m = c.steso, c.montata
    a = np.asarray(sleeve.convert("RGB").resize(
        (max(sleeve.width // 4, 1), max(sleeve.height // 4, 1))), float)
    x0, y0, x1, y1 = riquadro
    h, w = a.shape[:2]
    X = x0 + (np.arange(w) + 0.5) / w * (x1 - x0)
    Y = y0 + (np.arange(h) + 0.5) / h * (y1 - y0)
    X, Y = np.meshgrid(X, Y)
    rho = np.hypot(X - s.cx, Y - s.cy) * PT2MM
    fi = np.arctan2(Y - s.cy, X - s.cx)
    vivo = ((a.max(2) - a.min(2)) >= VIVO) & (rho >= s.piega) \
        & (rho <= s.piega + c.parete)
    if vivo.sum() < 50:
        return None, 0.0
    px_mm = w / ((x1 - x0) * PT2MM)
    k = max(int(round(MARCHIO_STACCO * px_mm)), 1)
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    lab, n = ndimage.label(ndimage.binary_closing(vivo,
                                                  structure=xx ** 2 + yy ** 2 <= k * k))
    if n == 0:
        return None, 0.0
    quanti = ndimage.sum(vivo, lab, index=np.arange(1, n + 1))
    sel = vivo & (lab == int(np.argmax(quanti)) + 1)
    r = rho[sel]
    sx = np.array([s.fi(q, "sx") for q in r])
    y = np.clip((r - s.piega) / c.parete, 0, 1) * m.y_parete
    giro = 2 * math.pi * (m.r(y) - CARTA / 2)
    f = ((fi[sel] - sx) % (2 * math.pi)) * r / giro
    f = f[f < 1.0]
    if len(f) < 20:
        return None, 0.0
    ang = 2 * math.pi * f
    media = (math.atan2(np.sin(ang).mean(), np.cos(ang).mean())
             / (2 * math.pi)) % 1.0
    # lo stesso punto sullo steso, a meta' parete, come angolo dalla mezzeria
    rho_m = s.piega + c.parete / 2
    fi_m = s.fi(rho_m, "sx") + media * 2 * math.pi * (m.r(m.y_parete / 2)
                                                       - CARTA / 2) / rho_m
    mezzo = 0.5 * (s.fi(rho_m, "sx") + s.fi(rho_m, "dx"))
    return media, math.degrees(fi_m - mezzo)


# --------------------------------------------------------------------------- #
# la maglia: solidi di rivoluzione
# --------------------------------------------------------------------------- #
class Maglia:
    """Vertici, UV e triangoli, e le parti per nome."""

    def __init__(self):
        self.V, self.UV, self.T = [], [], []
        self.n = 0
        self.parti = {}

    def giro(self, profilo, uv, inizio=0.0, lati=LATI):
        """Il solido di rivoluzione del profilo `[(r, y)]` attorno all'asse y.

        La faccia che si vede e' a destra di chi percorre il profilo:
        salendo lungo la parete esterna guarda fuori, scendendo lungo quella
        interna guarda dentro. `uv(j, s, teta)` da' le UV del punto j del
        profilo, a `s` mm di profilo dal primo punto, all'angolo `teta` -
        teta e' una fila, e la colonna in teta = inizio + 2pi e' doppia: la
        cucitura ha le sue UV.
        """
        P = np.asarray(profilo, float)
        s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
        teta = inizio + 2 * math.pi * np.arange(lati + 1) / lati
        base = self.n
        for j, (r, y) in enumerate(P):
            u, v = uv(j, s[j], teta)
            self.V.append(np.c_[r * np.sin(teta), np.full(lati + 1, y),
                                r * np.cos(teta)])
            self.UV.append(np.c_[np.broadcast_to(u, teta.shape),
                                 np.broadcast_to(v, teta.shape)])
        self.n += len(P) * (lati + 1)
        i = np.arange(lati)
        tris = []
        for j in range(len(P) - 1):
            a = base + j * (lati + 1) + i
            b, c = a + 1, a + lati + 1
            d = c + 1
            tris.append(np.c_[a, b, d])
            tris.append(np.c_[a, d, c])
        self.T.extend(tris)
        return s[-1]

    def segna(self, nome, primo):
        self.parti[nome] = (primo, self.triangoli())

    def triangoli(self):
        return int(sum(len(t) for t in self.T))

    def arrays(self):
        """`(V, UV, T, parti)`, con `parti` = [(nome, primo, ultimo)].

        I triangoli degeneri - quelli sull'asse, dove la fila di vertici e'
        un punto solo - non hanno area e vanno via; le parti si ricontano
        sui triangoli rimasti.
        """
        V = np.concatenate(self.V)
        UV = np.concatenate(self.UV)
        T = np.concatenate(self.T).astype(np.int64)
        A = np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]],
                                    V[T[:, 2]] - V[T[:, 0]]), axis=1)
        tieni = A > 1e-12
        prima = np.r_[0, np.cumsum(tieni)]
        parti = [(nome, int(prima[a]), int(prima[b]))
                 for nome, (a, b) in sorted(self.parti.items(),
                                            key=lambda kv: kv[1][0])]
        return V, UV, T[tieni], parti


def _semplifica(P, tol):
    """Douglas-Peucker: i punti del profilo che servono a tenerlo entro tol."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    d = b - a
    n = np.hypot(*d)
    if n < 1e-12:
        dist = np.hypot(*(P - a).T)
    else:
        dist = np.abs(np.cross(d, P - a)) / n
    k = int(np.argmax(dist))
    if dist[k] <= tol:
        return np.array([a, b])
    return np.concatenate([_semplifica(P[:k + 1], tol)[:-1],
                           _semplifica(P[k:], tol)])


def profilo_coppa(m):
    """I pezzi del profilo della coppa: `{nome: [(r, y)]}`.

    - `parete` sale dalla base alla cima della parete: e' la carta stampata,
      e prende lo sleeve;
    - `bordo` e' il bordo arrotolato, dalla cima della parete attorno al
      ricciolo; `carta` dice per ogni suo punto quanta carta c'e' fra lui e
      la parete, lungo la carta - vedi sotto;
    - `dentro` scende dal bordo lungo l'interno fino al piano del fondo, e
      `piano` va dal bordo del fondo all'asse: il rovescio, bianco;
    - sotto, `sotto` (il fondo visto da sotto), `orlo` (il risvolto dello
      sleeve attorno al fondo) e `base` (l'anello su cui la coppa poggia).

    Il ricciolo e' un cerchio alto quanto lui, tangente da fuori al diametro
    della bocca, e la parete ci entra da sotto. La carta ci si arrotola
    verso FUORI partendo dal lembo: il lembo - la fascia neutra in cima allo
    steso, che il DT vuole senza inchiostro - finisce al centro del rotolo,
    e il giro che si vede e' l'ultimo, quello attaccato alla parete. Lungo
    quel giro la carta sale dal lato interno, passa sopra e scende fuori:
    sul Nutella POT il marrone della fascia alta copre il lato interno e la
    cima, e il fuori del bordo resta bianco.
    """
    a = m.ricciolo / 2
    C = np.array([m.r_bordo - a, m.altezza - a])
    n_parete = 48
    ys = np.linspace(0.0, m.y_parete, n_parete + 1)
    parete = [(m.r(y), y) for y in ys]
    # il bordo: dalla cima della parete gira in senso antiorario - sotto,
    # fuori, sopra, dentro - fino a scendere un poco dentro
    P0 = np.array(parete[-1])
    f0 = math.atan2(P0[1] - C[1], P0[0] - C[0])
    r0 = float(np.hypot(*(P0 - C)))
    f1 = math.radians(225.0)
    bordo, carta = [tuple(P0)], [2 * math.pi * a]
    for f in np.linspace(f0, f1, 41)[1:]:
        t = min((f - f0) / math.radians(40.0), 1.0)
        rr = r0 + (a - r0) * (3 * t * t - 2 * t ** 3)
        bordo.append((C[0] + rr * math.cos(f), C[1] + rr * math.sin(f)))
        # la carta va in senso orario: dal lato interno, sopra, fuori
        carta.append(((f0 - f) % (2 * math.pi)) * a)
    fine = bordo[-1]
    y_fondo = m.rientro
    dentro = [fine] + [(m.r(y) - CARTA, y)
                       for y in np.linspace(m.y_parete, y_fondo + CARTA, 13)]
    r_piano = m.r(y_fondo + CARTA) - CARTA
    piano = [(r_piano, y_fondo + CARTA), (r_piano * 0.5, y_fondo + CARTA),
             (0.0, y_fondo + CARTA)]
    # il risvolto: tre strati di carta attorno alla gonna del fondo
    orlo_r = 3 * CARTA
    sotto = [(0.0, y_fondo), (0.5 * (m.r(y_fondo) - orlo_r), y_fondo),
             (m.r(y_fondo) - orlo_r, y_fondo)]
    orlo = [(m.r(y) - orlo_r, y) for y in np.linspace(y_fondo, 0.0, 5)]
    base = [(m.r_fondo - orlo_r, 0.0), (m.r_fondo, 0.0)]
    return {"parete": parete, "bordo": bordo, "carta": carta,
            "dentro": dentro, "piano": piano, "sotto": sotto, "orlo": orlo,
            "base": base}


def profilo_tappo(p, y_sommo):
    """I pezzi del profilo del tappo, alla quota `y_sommo` del suo sommo.

    - `fuori`: la gonna dal fondo al sommo, com'e' nella sezione, poi il
      ricciolo che scende dentro fino al piano: la carta dell'anello;
    - `piano`: il corpo, dal bordo all'asse;
    - `sotto` e `dentro`: il rovescio del corpo e della gonna, e `orlo`, lo
      spessore in fondo alla gonna.
    """
    F = _semplifica(p.fuori[::-1], 0.01)          # dal fondo al sommo
    fuori = [(r, y_sommo - z) for z, r in F]
    r_su = fuori[-1][0]
    z_p = p.z_piano - CARTA / 2                   # la faccia di sopra del piano
    r_p = p.r_piano
    # il ricciolo: dal sommo scende dentro, stretto, fino al bordo del piano
    giu = [(r_su - 0.9, 0.35), (r_su - 1.5, 1.0), (r_p + 0.35, z_p - 0.6),
           (r_p + 0.08, z_p - 0.12), (r_p, z_p)]
    fuori += [(r, y_sommo - z) for r, z in giu]
    piano = [(r_p, y_sommo - z_p), (r_p * 0.5, y_sommo - z_p),
             (0.0, y_sommo - z_p)]
    z_s = p.z_piano + CARTA / 2
    r_dentro = lambda z: float(np.interp(z, p.fuori[:, 0], p.fuori[:, 1])) - CARTA
    sotto = [(0.0, y_sommo - z_s), (r_dentro(z_s) * 0.5, y_sommo - z_s),
             (r_dentro(z_s), y_sommo - z_s)]
    zz = [z for z, _r in F[::-1] if z > z_s] + [p.altezza]
    zz = sorted(set([z_s] + zz))
    dentro = [(r_dentro(z), y_sommo - z) for z in zz]
    orlo = [(r_dentro(p.altezza), y_sommo - p.altezza),
            (r_dentro(p.altezza) + CARTA, y_sommo - p.altezza)]
    return {"fuori": fuori, "piano": piano, "sotto": sotto, "dentro": dentro,
            "orlo": orlo}


# --------------------------------------------------------------------------- #
# i riscontri: le misure dello steso contro quelle della vista montata
# --------------------------------------------------------------------------- #
def righe_del_lembo(T, s):
    """Le distanze (mm) dal taglio destro delle righe del DT parallele a lui.

    Il sormonto incollato il DT lo disegna come una striscia lungo il lato
    destro: una riga dove arriva il lembo sinistro, e le righe della
    grafica che gli finisce sotto. Servono a riscontrare la carta che la
    costruzione lascia sotto il lembo, non a costruire.
    """
    p, d = np.asarray(s.dx[0], float), np.asarray(s.dx[1], float)
    # la normale al taglio destro che guarda dentro lo steso, cioe' dalla
    # parte del lato sinistro
    nrm = np.array([-d[1], d[0]])
    if np.dot(np.asarray(s.sx[0], float) - p, nrm) < 0:
        nrm = -nrm
    out = []
    for t in T:
        if t.tratto is None or t.tratto[0] > 1.0 or len(t.P) < 2:
            continue
        a, b, scarto = _dritto(t.P)
        L = np.hypot(*(b - a))
        if scarto > 0.05 or L * PT2MM < 0.4 * (s.R2 - s.R1):
            continue
        u = (b - a) / L
        if abs(u[0] * d[1] - u[1] * d[0]) > math.sin(math.radians(1.0)):
            continue
        dist = float(np.dot((a + b) / 2 - p, nrm)) * PT2MM
        if 0.3 < dist < 15.0:
            if all(abs(dist - q) > 0.05 for q in out):
                out.append(dist)
    return sorted(out)


def riscontri(c, T):
    """Le righe di verifica della coppa: tornano, o dicono di quanto no."""
    s, m = c.steso, c.montata
    out = []
    w0, w1 = c.sormonto(0.0), c.sormonto(m.y_parete)
    righe = righe_del_lembo(T, s)
    if righe:
        vicina = min(righe, key=lambda q: abs(q - 0.5 * (w0 + w1)))
        esito = ("torna" if min(w0, w1) - 0.6 <= vicina <= max(w0, w1) + 0.6
                 else "NON TORNA")
        out.append("verifica sormonto: sotto il lembo restano %.1f mm al fondo "
                   "e %.1f alla bocca, il DT ha la riga del lembo a %.2f mm dal "
                   "taglio destro - %s" % (w0, w1, vicina, esito))
    else:
        out.append("verifica sormonto: sotto il lembo restano %.1f mm al fondo "
                   "e %.1f alla bocca; il DT non disegna la riga del lembo, "
                   "non si riscontra" % (w0, w1))
    if not (0.0 <= min(w0, w1) and max(w0, w1) <= 20.0):
        out.append("SORMONTO FUORI MISURA: la coppa montata e lo steso non "
                   "parlano dello stesso pezzo")
    beta_s = math.asin(min((s.arco(s.piega + c.parete) - s.arco(s.piega))
                           / c.parete / (2 * math.pi), 0.99))
    scarto = math.degrees(abs(m.pendenza - beta_s))
    out.append("verifica cono: la parete della vista montata pende %.2f gradi, "
               "lo steso ne svolge %.2f - %s"
               % (math.degrees(m.pendenza), math.degrees(beta_s),
                  "torna" if scarto <= 0.5 else "NON TORNA, scarto %.2f" % scarto))
    return out


# --------------------------------------------------------------------------- #
# la costruzione
# --------------------------------------------------------------------------- #
def costruisci(pdf_coppa=None, pdf_tappo=None, dpi=300, lastre_extra=(),
               tex_max=8192):
    """`(V, UV, T, atlante, parti, meta)` della coppa, del tappo, o dei due.

    V in mm, asse della coppa su y, base a y = 0, fronte verso +z. `parti`
    e' `[(nome, primo, ultimo)]` sui triangoli: la coppa e il tappo sono due
    nodi del GLB, e il tappo si toglie. Il dpi si abbassa fino a quello che
    l'atlante terra' davvero sotto `tex_max`, come per il vassoio: rendere
    lo sleeve a 300 dpi per poi ridurlo a 1700 punti e' memoria buttata.
    """
    if not pdf_coppa and not pdf_tappo:
        raise ValueError("coppa: nessun PDF")
    meta, avvisi = [], []
    immagini, giri = {}, {}
    c = p = None
    Tc = None
    if pdf_coppa:
        Tc = tracce(pdf_coppa)
        c = leggi_coppa(pdf_coppa, Tc)
        s, m = c.steso, c.montata
        x0, y0, x1, y1 = s.riquadro
        riq_s = (x0 - 3, y0 - 3, x1 + 3, y1 + 3)
        dpi = min(dpi, tex_max * 72.0 / (riq_s[2] - riq_s[0]))
        fx, fy, fr = c.fondo
        R = fr[0] / PT2MM
        riq_f = (fx - R, fy - R, fx + R, fy + R)
        regione = (min(riq_s[0], riq_f[0]), min(riq_s[1], riq_f[1]),
                   max(riq_s[2], riq_f[2]), max(riq_s[3], riq_f[3]))
        tex, avv = ritagli(pdf_coppa, {"sleeve": riq_s, "fondo": riq_f}, dpi,
                           regione, lastre_extra)
        avvisi += ["sleeve: " + a for a in avv]
        immagini["sleeve"] = (tex["sleeve"], riq_s)
        fondo = np.asarray(tex["fondo"].convert("L"), float)
        if (fondo < 200).mean() > 0.02:
            immagini["fondo"] = (tex["fondo"], riq_f)
        meta.append("coppa: alta %.1f mm, bocca %.1f, fondo %.1f, bordo "
                    "arrotolato %.1f, fondo rientrato %.1f - dalla vista montata "
                    "in miniatura, misurata a 1:%.2f sui cerchi del fondo"
                    % (m.altezza, 2 * m.r_bordo, 2 * m.r_fondo, m.ricciolo,
                       m.rientro, m.scala / PT2MM))
        meta.append("sleeve: settore da R %.1f a %.1f mm sul taglio, piega del "
                    "fondo a R %.2f, parete %.1f mm sulla generatrice"
                    % (s.R1, s.R2, s.piega, c.parete))
        meta += s.note
    if pdf_tappo:
        Tt = tracce(pdf_tappo)
        p = leggi_tappo(pdf_tappo, Tt)
        bx, by = p.centro
        R = p.r_taglio / PT2MM + 2
        riq_c = (bx - R, by - R, bx + R, by + R)
        ax0, ay0, ax1, ay1 = p.anello
        _rx0, ry0, _rx1, ry1 = p.righe
        riq_a = (ax0, ry0 - 3, ax1, ry1 + 3)
        regione = (min(riq_c[0], riq_a[0]), min(riq_c[1], riq_a[1]),
                   max(riq_c[2], riq_a[2]), max(riq_c[3], riq_a[3]))
        tex, avv = ritagli(pdf_tappo, {"corpo": riq_c, "anello": riq_a}, dpi,
                           regione, lastre_extra)
        avvisi += ["tappo: " + a for a in avv]
        # l'anello e' righe: meta' risoluzione bastano, e l'atlante resta
        # sotto gli 8192 punti anche ripetuto
        an = tex["anello"]
        an = an.resize((max(an.width // 2, 1), max(an.height // 2, 1)))
        modulo = (ax1 - ax0) * PT2MM
        r_max = float(p.fuori[:, 1].max())
        giri["anello"] = int(math.ceil(2 * math.pi * r_max / modulo))
        immagini["corpo"] = (tex["corpo"], riq_c)
        immagini["anello"] = (an, riq_a)
        meta.append("tappo: gonna di %.1f mm dentro, alta %.1f; piano del corpo "
                    "incassato di %.1f mm, largo %.1f - dalla sezione montata in "
                    "miniatura, a 1:%.2f sui cerchi del corpo"
                    % (2 * p.r_interno, p.altezza, p.z_piano, 2 * p.r_piano,
                       p.scala / PT2MM))
        meta.append("anello: %.1f x %.1f mm ripetuto %d volte attorno - la "
                    "stampa dell'anello e' casuale, come sul nastro il motivo "
                    "si ripete e sul retro si interrompe"
                    % (modulo, (ay1 - ay0) * PT2MM, giri["anello"]))
    A, zone = atlante(immagini, giri)
    bianco = zone["bianco"]
    ub, vb = bianco.uv(0.5, 0.5)

    def tinta(_j, _s, teta):
        return np.full(teta.shape, ub), np.full(teta.shape, vb)

    M = Maglia()
    if c is not None:
        s, m = c.steso, c.montata
        f, gradi = fronte(c, immagini["sleeve"][0], immagini["sleeve"][1])
        if f is None:
            f = 0.5
            meta.append("FRONTE NON TROVATO: lo sleeve non ha colori vivi, la "
                        "mezzeria dello steso guarda davanti")
        else:
            meta.append("fronte: il marchio, a %+.1f gradi dalla mezzeria "
                        "dello steso (il gruppo piu' grande di colori vivi)"
                        % gradi)
        inizio = -2 * math.pi * f
        P = profilo_coppa(m)
        zs = zone["sleeve"]
        rho_c = s.piega + c.parete
        w_c = c.sormonto(m.y_parete)
        parete, carta = P["parete"], P["carta"]

        def sullo_steso(rho, fr, giro):
            fi = s.fi(rho, "sx") + fr * giro / rho
            Rp = rho / PT2MM
            return zs.uv(s.cx + Rp * np.cos(fi), s.cy + Rp * np.sin(fi))

        def sleeve(j, sj, teta):
            # la parete: tanta carta quanta e' la circonferenza a quell'altezza
            fr = (teta - inizio) / (2 * math.pi)
            return sullo_steso(s.piega + sj, fr,
                               2 * math.pi * (parete[j][0] - CARTA / 2))

        def bordo(j, _sj, teta):
            # il bordo: la carta che segue la parete, nel verso in cui si
            # arrotola; lungo il giro, la stessa carta della cima della parete
            rho = min(rho_c + carta[j], s.R2 - 0.2)
            fr = (teta - inizio) / (2 * math.pi)
            return sullo_steso(rho, fr, s.arco(rho) - w_c)

        primo = M.triangoli()
        M.giro(parete, sleeve, inizio)
        M.giro(P["bordo"], bordo, inizio)
        if "fondo" in zone:
            zf = zone["fondo"]
            fx, fy, _fr = c.fondo

            def fondo(j, _sj, teta):
                r = P["sotto"][j][0]
                return zf.uv(fx + r * np.sin(teta) / PT2MM,
                             fy + r * np.cos(teta) / PT2MM)
            M.giro(P["sotto"], fondo, inizio)
        else:
            M.giro(P["sotto"], tinta, inizio)
        for nome in ("dentro", "piano", "orlo", "base"):
            M.giro(P[nome], tinta, inizio)
        M.segna("coppa", primo)
        meta += riscontri(c, Tc)
    if p is not None:
        if c is not None:
            # il piano del corpo poggia sul sommo del bordo
            y_sommo = c.montata.altezza + p.z_piano + CARTA / 2
        else:
            y_sommo = p.altezza
        Q = profilo_tappo(p, y_sommo)
        za, zc = zone["anello"], zone["corpo"]
        fuori = Q["fuori"]
        F = np.asarray(fuori)
        s_tappo = np.r_[0.0, np.cumsum(np.hypot(*np.diff(F, axis=0).T))]
        k_su = len(_semplifica(p.fuori[::-1], 0.01)) - 1
        S_su = s_tappo[k_su]
        r_rif = float(p.fuori[:, 1].max())
        ax0, ay0, ax1, ay1 = p.anello
        _x, ry0, _x2, ry1 = p.righe

        def anello(_j, sj, teta):
            X = ax0 + (teta - math.pi) * r_rif / PT2MM
            if sj <= S_su:
                Y = ay1 - sj / S_su * (ay1 - ay0)
            else:
                Y = max(ay0 - (sj - S_su) / PT2MM, ry0 - 2.5)
            return za.uv(X, np.full(teta.shape, Y))

        bx, by = p.centro
        piano = Q["piano"]

        def corpo(j, _sj, teta):
            r = piano[j][0]
            return zc.uv(bx + r * np.sin(teta) / PT2MM,
                         by + r * np.cos(teta) / PT2MM)

        primo = M.triangoli()
        M.giro(fuori, anello, math.pi)
        M.giro(piano, corpo, 0.0)
        for nome in ("sotto", "dentro", "orlo"):
            M.giro(Q[nome], tinta, 0.0)
        M.segna("tappo", primo)
        if c is not None:
            gioco = p.r_interno - c.montata.r_bordo
            meta.append("verifica tappo: la gonna e' larga %.2f mm dentro, la "
                        "bocca %.2f fuori - %s"
                        % (2 * p.r_interno, 2 * c.montata.r_bordo,
                           "calza" if -0.4 <= gioco <= 1.0
                           else "NON CALZA, gioco %.2f mm" % gioco))
    V, UV, T, parti = M.arrays()
    return V, UV, T, A, parti, meta + avvisi
