"""
Le strade di lettura del disegno tecnico, e il punteggio che sceglie fra le
letture.

Il punto 2 del piano del 20 novembre 2026: il proprietario preferisce che il
deterministico «fallisca il meno possibile a discapito del tempo», perche' un
caso che va alla routine costa di piu' di una costruzione lenta. Fino ad
allora la fustella si leggeva in un modo solo - per penna, `dieline.extract`
- e dell'astuccio vinceva la prima forma che passava. Adesso:

- **le strade della fustella** (`fustelle`): per colore, la lettura di
  sempre; coi tratti riuniti (`unisci`: i pezzi di una linea che si toccano
  sono una linea, come li esportano certi CAD); per geometria
  (`per_geometria`: senza guardare i colori, il gruppo di tratti collegati
  col contorno piu' grande, e fuori quote, legenda, cornice, miniature e
  segni che non lo toccano); per colore senza una penna dubbia
  (`penne_dubbie`: una penna di quote o di riquadri che i numeri non hanno
  fatto riconoscere);
- **su ogni strada tutte le letture dell'astuccio** (`dieline.letture_carton`:
  le serie di fasce candidate per tutte le forme);
- **il punteggio** (`punteggio`), un costo: le misure delle facce che non
  tornano fra loro (`dieline.costo_misure`), le correzioni, quanto della
  fustella la scatola spiega (`copertura`), le quote scritte che la
  confermano o la smentiscono, il verso della grafica;
- **il verdetto** (`scegli`): vince il costo piu' basso, la lettura di prima
  a pari merito (`dieline.PRECEDENZA`); due letture che danno astucci
  diversi a meno di `DUBBIO` sono un **dubbio dichiarato**, scritto nella
  lettura e negli avvisi, non un errore.

Le rotazioni del foglio le prova `artwork.astuccio_sulla_grafica` con queste
letture: il verso lo dice la grafica, la lettura le misure.

Le altre strade costano poco - sono conti sui tratti gia' letti - e si fanno
sempre quando il disegno e' un astuccio. Sul parco devono dare le letture di
prima (regole/astucci.md, *Le letture a punteggio*).
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict
from dataclasses import dataclass, field

from . import dieline as dl
from . import tentativi
from .dieline import PT2MM

# Le penne del disegno tecnico sono sottili (`dieline._technical_pens`).
SOTTILE = 1.2
# Due pezzi della stessa linea: sulla stessa retta e che si toccano, in punti.
STESSA_RETTA = 0.35
SALTO_PEZZI = 0.35
# Due tratti si toccano, per la strada per geometria: 0,35 mm. Una quota coi
# richiami staccati, una legenda, una cornice, un crocino stanno piu' in la'.
TOCCA = 1.0
# Oltre tanti tratti la strada per geometria non si prova: e' una pagina di
# campiture tratteggiate, non un disegno.
PEZZI_MAX = 40000
# Quante penne dubbie al piu' si provano a togliere.
PENNE_DUBBIE_MAX = 5
# Una penna coi tratti che finiscono quasi tutti sulle altre e' una cordonatura.
TOCCA_CERTA = 0.95
# Il costo di una strada che non e' quella di sempre, e di ogni sua
# correzione (una penna tolta).
COSTO_STRADA = 0.1
# Un voto della grafica (`artwork._consenso`: il fronte vale due) costa o
# guadagna tanto.
GRAFICA = 0.5
# Le quote scritte: ogni conferma (la terna del cartiglio, una catena) fa
# guadagnare tanto, fino a tre; ogni smentita costa tanto, fino a due.
QUOTA_CONFERMA = 0.5
QUOTA_SMENTITA = 1.0
# La scatola deve spiegare la fustella, non un suo pezzo: sotto questa
# frazione del riquadro piu' grande fra le strade la lettura paga.
COPERTURA_MIN = 0.45
COPERTURA_PESO = 5.0
# Due letture con astucci diversi a meno di tanto di costo: un dubbio.
DUBBIO = 0.25
# La lettura per colore basta, e le altre strade non si provano, se il suo
# costo geometrico e' al piu' tanto (`forte`).
COSTO_FORTE = 1.0

STRADE = {"colore": "per colore", "uniti": "coi tratti riuniti",
          "geometria": "per geometria"}


# --------------------------------------------------------------------------- #
# le strade
# --------------------------------------------------------------------------- #
def unisci(segs, salto=SALTO_PEZZI, stessa=STESSA_RETTA):
    """I pezzi della stessa linea - stessa penna, sulla stessa retta, che si
    toccano o si sovrappongono - uniti in un tratto solo.

    Certi CAD esportano il disegno una linea per ogni pezzo: col DT in pezzi
    di 3 mm (la variante `spezzati` del banco) nessun tratto era abbastanza
    lungo per una penna tecnica, e 51 casi su 55 non si leggevano. Non e' una
    regola per tutti: sull'impaginato del T6 aperto riunire cambia le penne
    tecniche da cinque a una. E' una strada accanto alle altre."""
    per = defaultdict(list)
    for k, c, a, b, st in segs:
        per[(k, st)].append((c, a, b))
    out = []
    for (k, st), tr in per.items():
        tr.sort()
        rette, cur = [], [tr[0]]
        for t in tr[1:]:
            if t[0] - cur[-1][0] <= stessa:
                cur.append(t)
            else:
                rette.append(cur)
                cur = [t]
        rette.append(cur)
        for r in rette:
            r.sort(key=lambda t: t[1])
            corsa = [r[0]]
            fine = r[0][2]
            for t in r[1:]:
                if t[1] <= fine + salto:
                    corsa.append(t)
                    fine = max(fine, t[2])
                    continue
                out.append(_un_tratto(k, corsa, fine, st))
                corsa, fine = [t], t[2]
            out.append(_un_tratto(k, corsa, fine, st))
    return out


def _un_tratto(k, corsa, fine, st):
    lungo = sum(t[2] - t[1] for t in corsa) or 1.0
    c = sum(t[0] * (t[2] - t[1]) for t in corsa) / lungo
    return (k, c, corsa[0][1], fine, st)


def _obliqui(t):
    """I tratti sottili obliqui o curvi della pagina, come segmenti: le
    alette coi lati inclinati e gli angoli tondi, che legano al corpo quello
    che le linee dritte non legano."""
    out = []
    for kind, st, o in t.oggetti:
        if kind not in ("line", "curve") or (st[0] or 0) > SOTTILE:
            continue
        pts = o.get("pts") or []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dx, dy = abs(bx - ax), abs(by - ay)
            dritto = ((dy > 1.0 and (dx < 0.7 or dx <= dl.QUASI_DRITTO * dy))
                      or (dx > 1.0 and (dy < 0.7 or dy <= dl.QUASI_DRITTO * dx)))
            if not dritto and (dx > 0.2 or dy > 0.2):
                out.append((ax, ay, bx, by))
    return out


def _distanza_punto(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    u = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
    return math.hypot(px - (x0 + u * dx), py - (y0 + u * dy))


def _incrociano(p, q):
    def lato(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d1 = lato(q[0], q[1], q[2], q[3], p[0], p[1])
    d2 = lato(q[0], q[1], q[2], q[3], p[2], p[3])
    d3 = lato(p[0], p[1], p[2], p[3], q[0], q[1])
    d4 = lato(p[0], p[1], p[2], p[3], q[2], q[3])
    return d1 * d2 < 0 and d3 * d4 < 0


def _si_toccano(p, q, tol):
    if (max(p[0], p[2]) + tol < min(q[0], q[2]) or max(q[0], q[2]) + tol < min(p[0], p[2])
            or max(p[1], p[3]) + tol < min(q[1], q[3])
            or max(q[1], q[3]) + tol < min(p[1], p[3])):
        return False
    if _incrociano(p, q):
        return True
    return min(_distanza_punto(p[0], p[1], *q), _distanza_punto(p[2], p[3], *q),
               _distanza_punto(q[0], q[1], *p), _distanza_punto(q[2], q[3], *p)) <= tol


def _gruppi_collegati(hv, obl, tol=TOCCA, cella=24.0):
    """`trova(i)`: il gruppo di ogni tratto - prima le H/V di `hv`
    `(k, c, a, b, ...)`, poi gli obliqui di `obl` `(x0, y0, x1, y1)` - dove due
    tratti stanno insieme se si toccano o si incrociano (a meno di `tol`).
    Non per vicinanza, come `dieline._gruppi` (25 punti): e' cosi' che
    legenda e quote finivano attaccate al disegno.

    Le H e le V, che sono quasi tutto, si incrociano con l'ordinamento: per
    ogni H le V nel suo tratto di x, poi chi delle due contiene l'altra; due
    H (o due V) sulla stessa retta che si toccano. Gli obliqui con una griglia,
    contro tutti."""
    import bisect
    n_hv = len(hv)
    padre = list(range(n_hv + len(obl)))

    def trova(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def lega(i, j):
        ri, rj = trova(i), trova(j)
        if ri != rj:
            padre[ri] = rj

    H = sorted((s[1], s[2], s[3], i) for i, s in enumerate(hv) if s[0] == "H")
    V = sorted((s[1], s[2], s[3], i) for i, s in enumerate(hv) if s[0] == "V")
    vx = [v[0] for v in V]
    for c, a, b, i in H:
        for c2, a2, b2, j in V[bisect.bisect_left(vx, a - tol):
                                bisect.bisect_right(vx, b + tol)]:
            if a2 - tol <= c <= b2 + tol:
                lega(i, j)
    for lista in (H, V):
        k = 0
        while k < len(lista):
            m = k + 1
            while m < len(lista) and lista[m][0] - lista[m - 1][0] <= tol:
                m += 1
            retta = sorted(lista[k:m], key=lambda t: t[1])
            fine, prima = retta[0][2], retta[0][3]
            for c, a, b, i in retta[1:]:
                if a <= fine + tol:
                    lega(prima, i)
                    fine = max(fine, b)
                else:
                    fine = b
                prima = i
            k = m
    if obl:
        pezzi = [((s[2], s[1], s[3], s[1]) if s[0] == "H" else (s[1], s[2], s[1], s[3]))
                 for s in hv] + list(obl)
        celle = defaultdict(list)
        for i, (x0, y0, x1, y1) in enumerate(pezzi):
            for cx in range(int((min(x0, x1) - tol) // cella),
                            int((max(x0, x1) + tol) // cella) + 1):
                for cy in range(int((min(y0, y1) - tol) // cella),
                                int((max(y0, y1) + tol) // cella) + 1):
                    celle[(cx, cy)].append(i)
        for lista in celle.values():
            obliqui = [i for i in lista if i >= n_hv]
            for i in obliqui:
                for j in lista:
                    if j == i or (j >= n_hv and j < i):
                        continue
                    if trova(i) != trova(j) and _si_toccano(pezzi[i], pezzi[j], tol):
                        lega(i, j)
    return trova


OBLIQUI_MAX = 8000


def per_geometria(t, dettaglio=None):
    """I tratti della fustella letti per geometria, senza guardare i colori:
    il gruppo di tratti sottili collegati - si toccano, non basta che siano
    vicini - che ha piu' disegno (lunghezza per righe distinte, come
    `dieline._punteggi_penna`), e che non e' una cornice: un gruppo che ne
    racchiude un altro con almeno tre decimi del suo disegno e' la cornice
    della tavola. Quote, legenda, cartiglio, miniature e segni che non
    toccano la fustella restano fuori. Due viste quasi uguali affiancate: vince
    quella con piu' grafica sotto (`dettaglio`), come per colore."""
    hv = [s for s in unisci(list(t.segmenti)) if (s[4][0] or 0) <= SOTTILE]
    if not hv:
        return []
    if len(hv) > PEZZI_MAX:
        return []
    obl = _obliqui(t)
    if len(obl) > OBLIQUI_MAX:
        obl = []
    trova = _gruppi_collegati(hv, obl)
    gruppi = defaultdict(list)
    for i in range(len(hv)):
        gruppi[trova(i)].append(i)
    lim = 0.05 * max(t.larghezza, t.altezza)
    cand = []
    for idx in gruppi.values():
        lungo = [hv[i] for i in idx if hv[i][3] - hv[i][2] >= lim]
        L = sum(hv[i][3] - hv[i][2] for i in idx)
        if not lungo or L < 4 * lim:
            continue
        righe = {k: [] for k in "HV"}
        for k, c, a, b, _st in lungo:
            righe[k].append((c, 1.0))
        n = sum(len(dl._cluster(righe[k])) for k in "HV")
        xs = [v for i in idx for v in ((hv[i][1],) if hv[i][0] == "V" else hv[i][2:4])]
        ys = [v for i in idx for v in ((hv[i][1],) if hv[i][0] == "H" else hv[i][2:4])]
        cand.append(dict(punti=L * max(n, 1), lungo=L, idx=idx,
                         riq=(min(xs), min(ys), max(xs), max(ys))))
    if not cand:
        return []

    def racchiude(r, q, tol=4.0):
        return (r[0] <= q[0] + tol and r[1] <= q[1] + tol
                and r[2] >= q[2] - tol and r[3] >= q[3] - tol)
    tenuti = [g for g in cand
              if not any(h is not g and racchiude(g["riq"], h["riq"])
                         and h["punti"] >= 0.3 * g["punti"] for h in cand)] or cand
    meglio = max(tenuti, key=lambda g: g["punti"])
    if dettaglio is not None:
        viste = [g for g in tenuti if g["lungo"] >= dl.ALTRA_VISTA * meglio["lungo"]]
        if len(viste) > 1:
            meglio = max(viste, key=lambda g: dettaglio(g["riq"]))
    return [hv[i] for i in meglio["idx"]]


def penne_dubbie(segs, page_w, page_h, massimo=PENNE_DUBBIE_MAX):
    """Le penne della fustella per colore che possono non esserlo: tutte, se
    sono piu' d'una, le meno convinte prima (`dieline._punteggi_penna`). Anche
    quella che sa di fustella piu' di tutte: sul T2x12 coi testi in curve la
    penna blu delle quote, senza numeri vivi, non si riconosceva piu' come
    quote, e con le sue catene lunghe era proprio lei la prima; entrava nella
    fustella e faceva una colonna, un fianco da 18,6 mm su una scatola
    profonda 45. Togliere la penna del taglio o delle pieghe da' una scatola
    che non torna, e il punteggio la scarta.

    Non e' dubbia una penna coi tratti che finiscono tutti (`TOCCA_CERTA`) su
    quelli delle altre: e' una cordonatura, come per `_penne_fustella_pulite`
    (le pieghe rosse dei fianchi del T2x25; tolte, la profondita' veniva 89,5
    invece di 90,2)."""
    penne = {s[4] for s in segs}
    if len(penne) < 2:
        return []
    p = dl._punteggi_penna(segs, page_w, page_h)
    dubbie = [st for st in penne
              if dl._quanto_tocca(segs, st, penne - {st}) < TOCCA_CERTA]
    return sorted(dubbie, key=lambda st: (p.get(st, 0.0), str(st)))[:massimo]


def nome_penna(st):
    """Una penna come si scrive in un cartellino: lo spessore e il colore."""
    w, colore = st
    return "%s pt %s" % (("%g" % w) if w else "0", colore)


@dataclass
class Fustella:
    """Una fustella candidata: la strada, le sue correzioni, la griglia, e
    la penna tolta se e' una lettura senza una penna dubbia."""
    strada: str
    correzioni: tuple
    d: object
    penna: object = None

    def chiave(self):
        return (self.strada, self.penna)


class Pagina:
    """Quello che le strade di una pagina leggono una volta sola: i tratti, i
    numeri e le lettere del testo, la grafica sotto un riquadro."""

    def __init__(self, pdf, page_no=0):
        self.pdf, self.page_no = pdf, page_no
        self.t = dl.tratti(pdf, page_no)
        self.numeri, self.caratteri = dl.testo_del_disegno(pdf, page_no)
        self.W, self.H = self.t.larghezza, self.t.altezza

    def dettaglio(self, r):
        return dl._colori(self.pdf, r, self.page_no)

    def per_colore(self, segs):
        """La fustella per penna di questi tratti (`dieline.fustella_per_colore`)."""
        return dl.fustella_per_colore(segs, self.W, self.H, self.numeri,
                                      self.caratteri, self.dettaglio)


def _griglia(pag, strada, corr, segs, viste, penna=None):
    """La `Fustella` di questi tratti, o None se non ne fanno una o se e' la
    stessa griglia di una gia' vista (la prima strada che la trova la tiene)."""
    if not segs:
        return None
    try:
        d = dl.griglia(segs, pag.W, pag.H)
    except Exception:                               # noqa: BLE001
        return None
    firma = (tuple(round(x, 1) for x in d.xs), tuple(round(y, 1) for y in d.ys),
             tuple(round(v, 1) for v in d.bbox))
    if firma in viste:
        return None
    viste.add(firma)
    return Fustella(strada, corr, d, penna)


def altre_fustelle(pag, colore, viste, solo=None):
    """Le fustelle delle strade diverse da quella per colore: coi tratti
    riuniti; per colore e coi tratti riuniti senza una penna dubbia alla
    volta, rifatte da capo senza di lei (togliendola dopo, sul T2x25 coi
    tratti spezzati la fustella perdeva il taglio e restava il corpo); per
    geometria. `colore` sono i tratti della fustella per colore, `viste` le
    griglie gia' trovate; `solo`, se c'e', le strade da fare (`Fustella.chiave`):
    sui fogli girati, quelle che sul foglio com'era davano una lettura."""
    out = []

    def serve(strada, penna=None):
        return solo is None or (strada, penna) in solo

    def metti(strada, corr, segs, penna=None):
        f = _griglia(pag, strada, corr, segs, viste, penna)
        if f is not None:
            out.append(f)
    tutti = list(pag.t.segmenti)
    riuniti = uniti = None
    if solo is None or any(k[0] == "uniti" for k in solo):
        riuniti = unisci(tutti)
        uniti = pag.per_colore(riuniti)
        if serve("uniti"):
            metti("uniti", ("tratti riuniti",), uniti)
    for base, scelti, strada, corr in ((tutti, colore, "colore", ()),
                                       (riuniti, uniti, "uniti", ("tratti riuniti",))):
        if scelti is None:
            continue
        penne = (penne_dubbie(scelti, pag.W, pag.H) if solo is None else
                 [k[1] for k in solo if k[0] == strada and k[1] is not None])
        for st in penne:
            metti(strada, corr + ("senza la penna %s" % nome_penna(st),),
                  pag.per_colore([x for x in base if x[4] != st]), st)
    if serve("geometria"):
        metti("geometria", ("per geometria",), per_geometria(pag.t, pag.dettaglio))
    return out


def fustelle(pdf, page_no=0, cartotecnico=False):
    """Tutte le fustelle candidate della pagina, `[Fustella]`, la strada per
    colore per prima - e' `dieline.extract`, uguale. Le altre solo se per
    colore il disegno si legge da cartotecnico (`dieline.classify`), come
    prima, o se il pack e' dichiarato cartotecnico: senza dichiarazione un
    flowpack steso resta un flowpack, e lo legge la sua famiglia."""
    pag = Pagina(pdf, page_no)
    colore = pag.per_colore(list(pag.t.segmenti))
    viste = set()
    f = _griglia(pag, "colore", (), colore, viste)
    if f is None:
        return []
    if dl.classify(f.d) not in ("carton", "unknown") and not cartotecnico:
        return [f]
    return [f] + altre_fustelle(pag, colore, viste)


# --------------------------------------------------------------------------- #
# il punteggio
# --------------------------------------------------------------------------- #
class Contesto:
    """Quello che il punteggio delle letture di una pagina legge una volta
    sola: i numeri e le terne delle quote, e il riquadro piu' grande fra le
    fustelle che danno un astuccio (per la copertura)."""

    def __init__(self, pdf, page_no=0):
        self.pdf, self.page_no = pdf, page_no
        self._quote = None
        self.riquadro = 0.0

    def quote(self):
        if self._quote is None:
            from . import quote
            try:
                self._quote = (quote.numeri(self.pdf, self.page_no),
                               quote.terne(self.pdf, self.page_no))
            except Exception:                       # noqa: BLE001
                self._quote = ([], [])
        return self._quote


def copertura(d, area):
    """Quanto del riquadro `area` (in punti quadri) copre la scatola letta: il
    riquadro dei suoi pannelli."""
    P = list(d.panels.values())
    if not P or area <= 0:
        return 1.0
    x0, y0 = min(p.x0 for p in P), min(p.y0 for p in P)
    x1, y1 = max(p.x1 for p in P), max(p.y1 for p in P)
    return max(0.0, (x1 - x0) * (y1 - y0)) / area


def voce_quote(l, ctx):
    """Le quote scritte contro la lettura: guadagna per ogni conferma, paga per
    ogni smentita; senza quote leggibili, niente."""
    nums, scritte = ctx.quote()
    if not nums:
        return 0.0
    from . import quote
    conf, div = quote.esito_riscontro(quote.attese_astuccio(l.d), l.d.dims_mm,
                                      nums, scritte)
    return -QUOTA_CONFERMA * min(len(conf), 3) + QUOTA_SMENTITA * min(len(div), 2)


def punteggio(letture, ctx):
    """Il costo intero delle letture valide: alle misure e alle correzioni
    (gia' in `voci`) aggiunge la copertura, le quote e la grafica. La grafica
    si chiede una volta per astuccio diverso (`dieline.stesso_modello`)."""
    from . import artwork
    valide = [l for l in letture if l.valida]
    for l in valide:
        c = copertura(l.d, ctx.riquadro)
        if c < COPERTURA_MIN:
            l.voci["copertura"] = round((COPERTURA_MIN - c) * COPERTURA_PESO, 3)
        q = voce_quote(l, ctx)
        if q:
            l.voci["quote"] = round(q, 3)
    fatti = []
    for l in valide:
        gia = next((f for f in fatti if dl.stesso_modello(f, l)
                    and _stessi_pannelli(f.d, l.d)), None)
        if gia is not None:
            l.voti = dict(gia.voti)
        else:
            try:
                l.voti = artwork.voti_della_grafica(l.pdf, l.d, ctx.page_no)
            except Exception:                       # noqa: BLE001
                l.voti = {}
            fatti.append(l)
        g = artwork._consenso(l.voti)
        if g:
            l.voci["grafica"] = round(-GRAFICA * g, 3)
        l.costo = round(sum(l.voci.values()), 3)
    return valide


def _stessi_pannelli(a, b, tol=1.0):
    return all(k in b.panels and all(abs(u - v) <= tol for u, v in
                                     zip(a.panels[k].bbox(), b.panels[k].bbox()))
               for k in a.panels)


# --------------------------------------------------------------------------- #
# il verdetto
# --------------------------------------------------------------------------- #
def scegli(letture, precedenza=dl.PRECEDENZA, dubbio=DUBBIO):
    """`(lettura, dubbio)`: la lettura che vince fra le plausibili
    (`dieline.plausibili`) - il costo piu' basso, quella di prima a meno di
    `precedenza` - e, se un'altra da' un astuccio diverso a meno di `dubbio`,
    la riga che lo dice. `(None, "")` se nessuna vale."""
    # gli astucci che un tentativo prima ha gia' costruito e il controllo
    # ha scartato non vincono piu' (`pack3d.tentativi`)
    valide = [l for l in dl.plausibili(letture) if not tentativi.escluso(l)]
    if not valide:
        return None, ""
    best = min(valide, key=lambda l: l.costo)
    prima = next((l for l in valide if l.prima), None)
    if prima is not None and prima.costo <= best.costo + precedenza:
        best = prima
    altre = [l for l in valide if not dl.stesso_modello(l, best)]
    if not altre:
        return best, ""
    seconda = min(altre, key=lambda l: l.costo)
    if seconda.costo - best.costo >= dubbio:
        return best, ""
    return best, riga_dubbio(best, seconda)


def riga_dubbio(best, seconda):
    """Il cartellino del dubbio: cosa si e' costruito e cosa era quasi alla
    pari, perche' chi guarda il modello sappia cosa controllare."""
    return ("DUBBIO DI LETTURA: costruito %s; quasi alla pari %s. Controllare "
            "il modello sul PDF" % (best.descrivi(), seconda.descrivi()))


def riga_strada(d):
    """Il cartellino dell'astuccio `d` se la fustella non e' venuta per
    colore com'era, la strada di sempre; None se si'."""
    come = []
    for c in d.correzioni:
        if c == "tratti riuniti":
            come.append("coi tratti riuniti (il disegno e' fatto di pezzi corti)")
        elif c == "per geometria":
            come.append("per geometria, senza guardare i colori delle penne")
        elif c.startswith("senza la penna"):
            come.append(c + ", che e' di quote o riquadri")
    if not come:
        return None
    return ("fustella letta %s: per colore, com'era, l'astuccio non tornava"
            % "; ".join(come))


@dataclass
class Esito:
    """Le letture dell'astuccio su un foglio: tutte, la vincente col suo
    dubbio, la fustella per colore (quella di `dieline.extract`), e l'errore
    se nessuna vale. `astuccio` dice se qualche strada si legge come
    cartotecnico (`dieline.classify`)."""
    letture: list = field(default_factory=list)
    migliore: object = None
    dubbio: str = ""
    colore: object = None
    errore: object = None
    astuccio: bool = False

    def dieline(self):
        """L'astuccio vincente, con scritto come e' stato letto."""
        l = self.migliore
        d = dl._applica(l)
        d.dubbio = self.dubbio
        return d


def _leggi(f, pdf, giro, es):
    """Le letture dell'astuccio su una fustella, con la strada scritta."""
    d = f.d
    d.kind = dl.classify(d)
    if d.kind not in ("carton", "unknown"):
        return []
    es.astuccio = True
    layout, _ = dl.detect_layout(d)
    if layout == "hwrap":
        ls = [_orizzontale(d, pdf)]
    else:
        try:
            ls = dl.letture_carton(d)
        except Exception as e:                      # noqa: BLE001
            if f.strada == "colore" and not f.correzioni:
                es.errore = e
            return []
        for l in ls:
            if l.d is not None:
                l.d.layout = "vwrap"
        if f.strada == "colore" and not f.correzioni and not dl.migliore(ls):
            es.errore = ValueError(dl.perche_no(d, ls))
    for l in ls:
        l.strada, l.giro, l.pdf = f.strada, giro, pdf
        l.chiave = f.chiave()
        if f.correzioni:
            l.prima = False
            l.correzioni = tuple(f.correzioni) + tuple(l.correzioni)
            if l.valida:
                l.voci["strada"] = round(COSTO_STRADA * len(f.correzioni), 3)
                l.costo = round(sum(l.voci.values()), 3)
    return ls


def forte(l, ctx):
    """Se la lettura per colore basta, e le altre strade non si provano: le
    misure tornano (costo geometrico al piu' `COSTO_FORTE`) e le quote, se ci
    sono, non la smentiscono. Il verso no: se la grafica non e' d'accordo si
    gira il foglio (`artwork.astuccio_sulla_grafica`), non si cambia strada."""
    if tentativi.larghe():
        # le soglie larghe di un tentativo: tutte le strade, sempre
        return False
    return (l is not None and l.geometrico <= COSTO_FORTE
            and voce_quote(l, ctx) <= 0)


def strade_buone(es):
    """Le strade (`Fustella.chiave`) che hanno dato una lettura plausibile, a
    parte quella per colore: sui fogli girati si rifanno solo loro."""
    return {getattr(l, "chiave", ("colore", None)) for l in dl.plausibili(es.letture)
            } - {("colore", None)}


def letture(pdf, page_no=0, giro=0, cartotecnico=False, solo=None, tutte=False):
    """Tutte le letture dell'astuccio su questo foglio, col costo intero, e il
    verdetto (`Esito`).

    Prima la strada per colore, quella di sempre. Se la sua lettura e' forte
    (`forte`), le altre non servono e non costano niente: e' la strada dei
    PDF come quelli del parco. Se no - non si risolve, o le misure non
    tornano, o le quote la smentiscono - tutte le altre (`altre_fustelle`),
    solo se il disegno per colore si legge da cartotecnico, come prima, o se
    il pack e' dichiarato tale (`cartotecnico`). `solo`, se c'e', le strade
    da rifare (`strade_buone`); `set()` nessuna, solo quella per colore.
    `tutte`: tutte le strade anche se quella per colore e' forte, per
    misurare i margini (`prove/punteggi.py`)."""
    ctx = Contesto(pdf, page_no)
    pag = Pagina(pdf, page_no)
    colore = pag.per_colore(list(pag.t.segmenti))
    viste = set()
    f0 = _griglia(pag, "colore", (), colore, viste)
    if f0 is None:
        # nessun tratto da fustella: la griglia vuota di `extract`, come
        # prima, e il registro va avanti
        try:
            es = Esito(colore=dl.griglia(colore, pag.W, pag.H))
            es.colore.kind = dl.classify(es.colore)
        except Exception:                           # noqa: BLE001
            es = Esito(colore=dl.Dieline(pag.W, pag.H, (0.0, 0.0, 0.0, 0.0)))
        return es
    tipo = dl.classify(f0.d)
    es = Esito(colore=copy.copy(f0.d))
    es.colore.kind = tipo
    es.letture = _leggi(f0, pdf, giro, es)
    if ((tipo in ("carton", "unknown") or cartotecnico) and solo != set()
            and (tutte or not forte(dl.migliore(es.letture), ctx))):
        for f in altre_fustelle(pag, colore, viste, solo):
            es.letture += _leggi(f, pdf, giro, es)
    plaus = dl.plausibili(es.letture)
    if plaus:
        ctx.riquadro = max((_area(l.d.bbox) for l in plaus), default=0.0)
        punteggio(es.letture, ctx)
    es.migliore, es.dubbio = scegli(es.letture)
    if es.migliore is not None:
        es.errore = None
    elif es.errore is None and es.astuccio:
        es.errore = ValueError(
            "astuccio: nessuna lettura torna, su nessuna strada della fustella "
            "(%s)" % ", ".join(sorted({STRADE.get(l.strada, l.strada)
                                       for l in es.letture})))
    return es


def _area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _orizzontale(d, pdf):
    """La lettura dell'astuccio a fasciatura orizzontale (`solve_carton_h`),
    una sola: la prima della fila che passa, come prima."""
    l = dl.Lettura("orizzontale", [], {})
    try:
        l.d = dl.solve_carton_h(copy.copy(d), pdf)
    except Exception as e:                          # noqa: BLE001
        l.scartata = str(e)
        return l
    l.voci = dl.costo_misure(l.d)
    l.costo = round(sum(l.voci.values()), 3)
    l.prima = True
    return l
