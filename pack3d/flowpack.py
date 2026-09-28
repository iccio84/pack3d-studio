"""
Flowpack: dallo steso di stampa alla forma tridimensionale.

Un flowpack non e' un poliedro. Il film esce da una bobina, si avvolge attorno
al prodotto e viene saldato in tre punti: una pinna longitudinale dove i due
bordi del nastro si incontrano, e due pinne trasversali alle estremita', dove
la sezione si schiaccia fino a diventare piatta. Le pinne trasversali sono
tagliate a zigzag dalle ganasce (zingrinatura).

Lo steso va quindi letto come una fascia: la direzione trasversale al nastro e'
lo sviluppo del perimetro della sezione, quella longitudinale e' la lunghezza.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pdfplumber

from .dieline import _segments, _cluster, PT2MM


@dataclass
class Flowpack:
    W: float = 0.0            # larghezza del prodotto (faccia fronte)
    T: float = 0.0            # spessore del prodotto
    L: float = 0.0            # lunghezza fra le due saldature di testa
    end_fin: float = 0.0      # sporgenza della pinna trasversale
    side_fin: float = 0.0     # altezza della pinna longitudinale
    back_a: float = 0.0       # tratto di retro fra pinna e primo spigolo
    back_b: float = 0.0       # tratto di retro dall'altro lato
    # chiusura a sovrapposizione: lembo di film che passa SOTTO l'altro bordo
    # invece di girare intorno al prodotto. Se e' > 0 il pack e' un tubo
    # piatto - fronte e retro, nessun fianco e nessuna falda che sporge.
    sovrapposizione: float = 0.0
    # tratto fra la saldatura di testa e la fine del prodotto, dove il tubo si
    # schiaccia verso la pinna: la zona "grinze" del DT, o la gola. Zero se il
    # disegno non la segna uguale dai due lati.
    gola: float = 0.0
    # le linee del DT che attraversano il nastro, in mm dal primo taglio: la
    # verifica delle UV le confronta con le testate del modello
    linee_passo: tuple = ()
    web_mm: float = 0.0
    step_mm: float = 0.0
    # riquadro dello steso, in punti PDF: (x0, y0, x1, y1)
    sheet: tuple = (0.0, 0.0, 0.0, 0.0)
    girth_span: tuple = (0.0, 0.0)   # y del perimetro utile, in punti
    # steso analizzato trasposto, con il perimetro lungo la x della pagina:
    # sheet e girth_span sono in quel telaio, la texture va trasposta anche lei
    ruotato: bool = False
    warnings: list = field(default_factory=list)

    @property
    def pillow(self):
        """Vero se la chiusura e' a sovrapposizione e non a pinna."""
        return self.sovrapposizione > 0.0

    @property
    def girth(self):
        """Il film che gira davvero intorno al prodotto.

        A pinna i due lembi escono fuori e il giro e' il perimetro della
        sezione, 2(W+T). A sovrapposizione non esce niente: il lembo passa
        sotto, quindi il giro e' tutto il nastro meno quel lembo.
        """
        if self.sovrapposizione > 0.0:
            return self.web_mm - self.sovrapposizione
        return 2.0 * (self.W + self.T)


def _technical_segments(page, min_len=25.0, dentro=None):
    """Il tracciato tecnico dello steso: tratti sottili, i piu' lunghi.

    `dentro`, se c'e', dice quali segmenti guardare: la penna si sceglie fra
    quelli, non sulla pagina intera dove possono vincere le copie tecniche.
    """
    segs = [s for s in _segments(page) if s[3] - s[2] > min_len and s[4][0] <= 0.8]
    if dentro is not None:
        segs = [s for s in segs if dentro(s)]
    if not segs:
        return []
    score = {}
    for k, c, a, b, st in segs:
        score[st] = score.get(st, 0.0) + (b - a)
    pen = max(score, key=score.get)
    return [s for s in segs if s[4] == pen]


def analyze(pdf_path: str, page_no: int = 0, tol: float = 0.02,
            bbox=None) -> Flowpack:
    """Il solutore vecchio: l'ultimo ripiego, quando `analyze_auto` non chiude.

    Con `bbox` - il riquadro del DT con la grafica, in punti - guarda solo
    li'. Senza, misurava la pagina intera: quote, copie tecniche, legenda e
    cartiglio finivano nelle fasce, e ne usciva un pack plausibile e
    sbagliato, il difetto peggiore che questo progetto possa avere.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_no]

        def _in(sg):
            bx0, by0, bx1, by1 = bbox
            k, c, a0, b0, _st = sg
            if k == "H":
                return (by0 - 3 <= c <= by1 + 3 and a0 >= bx0 - 3
                        and b0 <= bx1 + 3)
            return (bx0 - 3 <= c <= bx1 + 3 and a0 >= by0 - 3
                    and b0 <= by1 + 3)
        segs = _technical_segments(page, dentro=_in if bbox else None)

        V = _cluster([(c, b - a) for k, c, a, b, st in segs if k == "V"], 2.0)
        H = _cluster([(c, b - a) for k, c, a, b, st in segs if k == "H"], 2.0)
        if not V or not H:
            raise ValueError("nessun tracciato tecnico riconoscibile")

        ys = [c for c, w in H]
        web_pt = ys[-1] - ys[0]
        # le linee a tutta altezza segnano taglio di ripetizione e saldature
        full = sorted(c for c, w in V if w > web_pt * 0.9)
        if len(full) < 4:
            raise ValueError("saldature di testa non riconosciute")
        cut0, seal0, seal1, cut1 = full[0], full[1], full[-2], full[-1]

        steps = [(ys[i + 1] - ys[i]) * PT2MM for i in range(len(ys) - 1)]
        i = int(np.argmax(steps))
        W = steps[i]

        # lo spessore e' la fascia adiacente al fronte su entrambi i lati; puo'
        # essere spezzata in piu' tratti dalle linee di riferimento grafiche
        def run(start, direction, target):
            tot, n = 0.0, 0
            j = start
            while 0 <= j < len(steps) and tot < target * (1 + tol):
                tot += steps[j]
                n += 1
                if abs(tot - target) <= max(0.4, target * tol):
                    return n, tot
                j += direction
            return None, None

        best = None
        for cand in sorted({round(s, 1) for s in steps}, reverse=True):
            if cand >= W or cand <= 0:
                continue
            nl, tl = run(i - 1, -1, cand)
            nr, tr = run(i + 1, +1, cand)
            if nl is None or nr is None:
                continue
            girth = 2 * (W + cand)
            # la fascia del perimetro deve chiudere su 2*(W+T)
            for a in range(0, i - nl + 1):
                for b in range(i + nr, len(steps)):
                    tot = sum(steps[a:b + 1])
                    if abs(tot - girth) <= max(1.0, girth * tol):
                        err = abs(tot - girth)
                        if best is None or err < best[0]:
                            best = (err, cand, a, b, nl, nr)
        if best is None:
            raise ValueError("perimetro della sezione non riconosciuto")
        _, T, a, b, nl, nr = best

        back_a = sum(steps[a:i - nl])
        back_b = sum(steps[i + nr + 1:b + 1])
        fin_material = sum(steps[:a]) + sum(steps[b + 1:])

        fp = Flowpack(
            W=round(W, 1), T=round(T, 1),
            L=round((seal1 - seal0) * PT2MM, 1),
            end_fin=round((seal0 - cut0) * PT2MM, 1),
            side_fin=round(fin_material / 2.0, 1),
            back_a=round(back_a, 1), back_b=round(back_b, 1),
            web_mm=round(web_pt * PT2MM, 1),
            step_mm=round((cut1 - cut0) * PT2MM, 1),
            sheet=(cut0, ys[0], cut1, ys[-1]),
            girth_span=(ys[a], ys[b + 1]),
        )
        if abs(back_a + back_b - W) > max(1.0, W * 0.03):
            fp.warnings.append(
                f"il retro misura {back_a + back_b:.1f} mm contro {W:.1f} mm di fronte")
        if abs(fp.end_fin - (cut1 - seal1) * PT2MM) > 0.5:
            fp.warnings.append("le due pinne di testa hanno larghezza diversa")
        return fp


# --------------------------------------------------------------------------- #
# costruzione della mesh
# --------------------------------------------------------------------------- #
def _section_path(fp: Flowpack, r: float, n_arc: int = 10, section_w=None):
    """Sezione trasversale: rettangolo W x T con spigoli raccordati.

    Il cammino parte dalla pinna longitudinale e gira nello stesso ordine in cui
    lo steso scorre dall'alto verso il basso: retro, fianco, fronte, fianco,
    retro. Restituisce i punti e l'ascissa curvilinea."""
    W, T = (section_w or fp.W), fp.T
    r = min(r, W / 2 - 0.1, T / 2 - 0.1)
    hy, hz = W / 2, T / 2
    y_fin = hy - fp.back_a

    corners = [(+hy, -hz), (+hy, +hz), (-hy, +hz), (-hy, -hz)]
    pts = [(y_fin, -hz)]
    for k, (cy, cz) in enumerate(corners):
        sy = 1 if cy > 0 else -1
        # ingresso e uscita dello spigolo
        if k in (0, 2):      # spigoli sul lato del retro/fronte -> arrivo in y
            pts.append((cy - sy * r, cz))
        pts.append((cy, cz))
    # ricostruzione esplicita con archi
    path = []

    def arc(cy, cz, a0, a1):
        for t in np.linspace(a0, a1, n_arc):
            path.append((cy + r * np.cos(t), cz + r * np.sin(t)))

    path.append((y_fin, -hz))
    path.append((hy - r, -hz))
    arc(hy - r, -hz + r, -np.pi / 2, 0.0)
    path.append((hy, hz - r))
    arc(hy - r, hz - r, 0.0, np.pi / 2)
    path.append((-hy + r, hz))
    arc(-hy + r, hz - r, np.pi / 2, np.pi)
    path.append((-hy, -hz + r))
    arc(-hy + r, -hz + r, np.pi, 1.5 * np.pi)
    path.append((y_fin, -hz))

    P = np.array(path, float)
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    return P, d



def superellipse_section(fp: Flowpack, n: float, thickness=None, npts: int = 1600):
    """Sezione a superellisse |y/a|^n + |z/b|^n = 1.

    Il rettangolo raccordato ha la curvatura che salta di colpo nei punti di
    tangenza, e il salto si legge come una piega netta. La superellisse ha
    curvatura continua: e' la forma che da' l'aspetto morbido del pack reale.
    Lo spessore lo fissa il prodotto; la semilarghezza `a` viene ricavata
    imponendo che il perimetro sia quello del film.
    """
    b = (thickness if thickness is not None else fp.T) / 2.0
    t = np.linspace(0.0, 2.0 * np.pi, npts, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    uy = np.sign(ct) * np.abs(ct) ** (2.0 / n)
    uz = np.sign(st) * np.abs(st) ** (2.0 / n)

    def perim(a):
        P = np.stack([a * uy, b * uz], 1)
        return float(np.sum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)))

    lo, hi = b, 4.0 * fp.girth
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if perim(mid) < fp.girth:
            lo = mid
        else:
            hi = mid
    a = 0.5 * (lo + hi)
    P = np.stack([a * uy, b * uz], 1)
    # L'origine di v deve cadere sulla cucitura, come nel profilo raccordato:
    # altrimenti la grafica ruota attorno al tubo e il fronte non guarda piu'
    # davanti. La cucitura sta a `back_a` di arco prima dello SPIGOLO (+y, -z),
    # quello da cui _section_path fa partire il cammino.
    #
    # Ancorare al punto di y massima, come si faceva qui, prende il CENTRO
    # della faccia laterale e non lo spigolo: sono mezzo spessore di distanza,
    # e la grafica gira attorno al tubo di altrettanto. Misurato fascia per
    # fascia: 4,2 mm su Kinder Country (T 10), 12,9 su Paradiso (T 27), 25,7
    # su Brioss (T 57).
    #
    # Nella parametrizzazione lo spigolo e' il punto a 45 gradi, dove
    # |uy| = |uz|, cioe' t = 7/4 pi: per n grande tende allo spigolo vero del
    # rettangolo, ed e' quello da cui _section_path fa partire il cammino.
    #
    # Su un tubo piatto non e' quello. Li' non ci sono spigoli: ci sono le due
    # PIEGHE del tubo appiattito, che sono gli estremi dell'asse maggiore,
    # cioe' t = 0. Ancorare comunque ai 45 gradi ruota la grafica di tutto
    # l'arco fra i due punti - misurato sul K Tronky T1: 7,55 mm su un giro di
    # 71, il 10,6%, con il fronte che finiva mezzo sul fianco.
    dd = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(dd)])
    per = cum[-1]
    i_sp = 0 if fp.pillow else int(round(npts * 7.0 / 8.0)) % npts
    s0 = (cum[i_sp] - fp.back_a) % per
    i0 = int(np.searchsorted(cum, s0)) % len(P)
    P = np.roll(P, -i0, axis=0)
    P = np.vstack([P, P[:1]])           # contorno chiuso
    dd = np.linalg.norm(np.diff(P, axis=0), axis=1)
    d = np.concatenate([[0.0], np.cumsum(dd)])
    return P, d, a


def sezione_rigonfiata(fp: Flowpack, n: float, npts: int = 1600):
    """Sezione al livello di rigonfiamento `n`, a steso invariato.

    Il rigonfiamento e' un cambio di forma, non di taglia: la sezione passa dal
    rettangolo (n alto, pack teso sul prodotto) all'ellisse (n=2, pack pieno
    d'aria) tenendo fermi il rapporto larghezza/spessore misurato e il
    perimetro del film. A parita' di perimetro una forma tonda e' piu' grande
    di una squadrata, quindi il pack si gonfia in entrambe le direzioni: e' la
    scala che lo mette in conto, e il perimetro scala con lei.
    """
    t = np.linspace(0.0, 2.0 * np.pi, npts, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    P = np.stack([fp.W / 2.0 * np.sign(ct) * np.abs(ct) ** (2.0 / n),
                  fp.T / 2.0 * np.sign(st) * np.abs(st) ** (2.0 / n)], 1)
    per = float(np.sum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)))
    return fp.girth / per


def _incrocio(P, d, asse, segno):
    """Arco `d` dove la coordinata `asse` del contorno passa per zero mentre
    l'altra ha il segno `segno`: y = 0 sopra e' il centro del fronte, y = 0
    sotto quello del retro, z = 0 la meta' di un fianco."""
    a, b = P[:, asse], P[:, 1 - asse]
    ok = (a[:-1] * a[1:] <= 0) & ((b[:-1] + b[1:]) * segno > 0)
    k = int(np.flatnonzero(ok)[0])
    den = a[k] - a[k + 1]
    t = a[k] / den if abs(den) > 1e-12 else 0.5
    return float(d[k] + t * (d[k + 1] - d[k]))


class _GiroSulFilm:
    """Dove mettere i vertici di un anello perche' il giro sia quello del film.

    Nel corpo i vertici stanno dove li mette la sezione, e i nodi dei pannelli
    fanno cadere ogni fascia sulla sua faccia. Verso la pinna la sezione si
    schiaccia e si allarga, e scalarla, come si faceva, porta con se' le
    fasce: il fronte si allargava con la pinna, del 46% sul Paradiso, e i
    fianchi si chiudevano a zero sul bordo. La grafica sterzava verso fuori
    lungo la gola e sulla pinna arrivava stirata.

    La pinna invece e' il tubo appiattito: il film non si allunga, quindi un
    punto del fronte a 20 mm dal centro sta a 20 mm dal centro anche sulla
    pinna, e le pieghe dei bordi cadono a meta' dei fianchi. Qui ogni anello
    si rimisura sul film a partire dal centro del fronte e da quello del
    retro, e la differenza di lunghezza fra anello e film - poca con la pinna
    aperta, tutto il fianco con una scatola dentro, dove il fianco si
    ripiega a soffietto - la prende la fascia della piega. Il peso `w` passa
    dalla sezione (0) al film (1) lungo la gola, e la forma non cambia: i
    vertici scorrono sull'anello, non ne escono.
    """
    MARGINE = 2.0     # mm di film ai due lati della piega che fanno da cerniera

    def __init__(self, P, d, G, v, giro):
        ks, kf, fronte, retro = giro
        self.P, self.d, self.G = P, d, G
        if ks is not None:
            film = lambda s: np.interp(s, ks, kf)
        else:
            film = lambda s: np.asarray(s, float)
        self.sF = _incrocio(P, d, 0, +1)
        self.sB = _incrocio(P, d, 0, -1)
        avanti = lambda s: (s - self.sF) % G
        self.sP, self.sM = sorted([_incrocio(P, d, 1, +1), _incrocio(P, d, 1, -1)],
                                  key=avanti)
        fF = film(self.sF)
        self.o = (film(v * G) - fF) % G          # film dal centro del fronte
        self.oB = float((film(self.sB) - fF) % G)
        self.fronte, self.retro = fronte / 2.0, retro / 2.0
        self.sg = self.sF + d                    # un giro a partire dal fronte
        self.nat = v * G

    def anello(self, sy, sz, w):
        """Punti della sezione (non scalata) su cui cadono i vertici."""
        P, d, G = self.P, self.d, self.G
        Q = P * np.array([sy, sz])
        c = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
        per = float(c[-1])
        C = lambda s: np.interp(np.mod(s, G), d, c) + np.floor_divide(s, G) * per
        Cg = C(self.sg) - C(self.sF)
        R = lambda s: np.interp(self.sF + np.mod(s - self.sF, G), self.sg, Cg)
        Ap, H, Am = float(R(self.sP)), float(R(self.sB)), float(R(self.sM))
        g = self.MARGINE
        f1p = max(0.0, min(self.fronte - g, Ap - g))
        b1p = max(0.0, min(self.retro - g, H - Ap - g))
        b1m = max(0.0, min(self.retro - g, Am - H - g))
        f1m = max(0.0, min(self.fronte - g, per - Am - g))
        oB = self.oB
        film = np.maximum.accumulate([0.0, f1p, oB - b1p, oB, oB + b1m, G - f1m, G])
        giro = np.maximum.accumulate([0.0, f1p, H - b1p, H, H + b1m, per - f1m, per])
        r_film = np.interp(self.o, film, giro)
        r_sez = R(self.nat)
        r_film = r_film - per * np.round((r_film - r_sez) / per)
        r = np.mod((1.0 - w) * r_sez + w * r_film, per)
        s = np.mod(np.interp(r, Cg, self.sg), G)
        return np.stack([np.interp(s, d, P[:, 0]), np.interp(s, d, P[:, 1])], 1)


def _stendi_spalla(verts, uvs, u, half, taper):
    """Lungo il passo, sulla spalla, il film si stende sulla superficie.

    Con u proporzionale a x la spalla prende tanto film quanto e' lunga in
    pianta, ma in pianta e' piu' corta che in superficie, perche' scende: la
    grafica si stirava dove la discesa e' ripida e restava giusta dove e'
    piana, e una scritta a cavallo usciva con le lettere di larghezze diverse.
    Qui, colonna per colonna, il film fra l'ultimo anello a sezione piena e
    la saldatura si distribuisce in proporzione alla lunghezza vera: i due
    capi restano dove sono - saldatura e corpo non si muovono, e della
    texture non si perde niente - e lo stiro, che il film non puo' evitare,
    diventa uguale su tutta la spalla invece di fare picco.
    """
    for lato in (-1.0, 1.0):
        dentro = [i for i, ui in enumerate(u) if lato * ui <= half - taper + 1e-9
                  and lato * ui >= 0]
        fuori = [i for i, ui in enumerate(u) if abs(lato * ui - half) < 1e-9]
        if not dentro or not fuori:
            continue
        i0 = max(dentro, key=lambda i: lato * u[i])      # ultimo a sezione piena
        i1 = fuori[0]                                     # la saldatura
        sel = sorted(range(min(i0, i1), max(i0, i1) + 1), key=lambda i: lato * u[i])
        if len(sel) < 3:
            continue
        tratti = np.linalg.norm(np.diff(verts[sel], axis=0), axis=2)
        s = np.vstack([np.zeros((1, verts.shape[1])), np.cumsum(tratti, axis=0)])
        f = s / np.maximum(s[-1:], 1e-9)
        u0, u1 = uvs[sel[0], :, 0], uvs[sel[-1], :, 0]
        uvs[sel, :, 0] = u0 + (u1 - u0) * f


def build_mesh(fp: Flowpack, nu: int = 72, nv: int = 108, corner_r: float = 3.5,
               taper: float = 24.0, flat_end: float = 0.035, width_end: float = 0.93,
               section_w=None,
               crimp_period: float = 1.6, crimp_mm: float = 0.30,
               serration: bool = True, serr_period: float = 0.85,
               serr_amp: float = 0.45, bulge: float = 0.0,
               serr_teeth: int = 0, fin_stations: int = 44,
               sec_exp: float = 0.0, sec_thickness=None, soft: bool = False,
               soft_r: float = 0.0, soft_n: float = 3.0, flare_pow: float = 2.0,
               wrinkle_mm: float = 0.0, wrinkle_v: float = 3.0, wrinkle_u: float = 2.5,
               giro=None, spalla_sul_film: bool = False):
    """Mesh del flowpack con UV riferite allo steso.

    u percorre la lunghezza (comprese le pinne di testa), v il perimetro. Dove
    la sezione si schiaccia non basta lasciare le UV quelle del piano: scalando
    la sezione le fasce del film la seguono, e la grafica si allarga con la
    pinna. Il film non si allunga, e sulle testate i vertici vanno rimessi
    dove il film li porta.

    `giro` = (ks, kf, fronte, retro): i nodi dei pannelli (arco della sezione
    -> film, o None) e le larghezze di film di fronte e retro. Se c'e', nella
    gola e nella pinna i vertici si rimettono sull'anello misurandoli sul
    film, vedi `_GiroSulFilm`. `spalla_sul_film` fa la stessa cosa lungo il
    passo, sulla spalla: vedi `_stendi_spalla`.
    """
    if soft_r > 0:
        P, d, section_w = soft_section_fit(fp, soft_r, soft_n)
    elif sec_exp > 0:
        P, d, _a = superellipse_section(fp, sec_exp, thickness=sec_thickness)
    else:
        P, d = _section_path(fp, corner_r, section_w=section_w)
    G = d[-1]
    v = np.linspace(0.0, 1.0, nv + 1)
    sec = np.stack([np.interp(v * G, d, P[:, 0]), np.interp(v * G, d, P[:, 1])], 1)
    sul_film = None
    if giro is not None:
        try:
            sul_film = _GiroSulFilm(P, d, G, v, giro)
        except IndexError:
            # una sezione senza centri o fianchi da trovare non esiste fra
            # quelle che si costruiscono; se arrivasse, meglio la mappatura
            # di prima - che la terza verifica grida - che niente modello
            sul_film = None
    sec_pinna = sul_film.anello(width_end, flat_end, 1.0) if sul_film else sec

    half = fp.L / 2.0
    total = half + fp.end_fin
    # sezioni fitte dentro le pinne: il dente e' profondo circa 1,6 mm e con il
    # passo del corpo verrebbe fuori a gradini invece che a punta
    body = np.linspace(-half, half, nu + 1)
    fin = np.linspace(half, total, max(fin_stations, 2) + 1)[1:]
    u = np.concatenate([-fin[::-1], body, fin])

    # zigzag della zigrinatura sul bordo esterno delle pinne
    if serration and serr_teeth > 0:
        # Il dente va contato sul bordo della pinna, non sul perimetro della
        # sezione: la pinna e' schiacciata, quindi il suo bordo misura due
        # volte l'apertura. Passo e altezza danno triangoli equilateri.
        y_fin = sec_pinna[:, 0] * width_end
        hy = float(np.max(np.abs(y_fin)))
        base = 2.0 * hy / serr_teeth
        depth = base * math.sqrt(3.0) / 2.0
        phase = (y_fin + hy) / base
        saw = 2.0 * np.abs(phase - np.floor(phase + 0.5))
        trim = depth * saw
    elif serration and serr_period > 0:
        phase = (v * G) / serr_period
        saw = 2.0 * np.abs(phase - np.floor(phase + 0.5))
        trim = serr_amp * saw
    else:
        trim = np.zeros_like(v)

    # normale 2D del contorno: serve per le grinze, che vanno date lungo la
    # normale, non in verticale, altrimenti la sezione si deforma
    def normali(s):
        tang = np.gradient(s, axis=0)
        tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
        n = np.stack([tang[:, 1], -tang[:, 0]], 1)
        return -n if float(np.sum(n * s)) < 0 else n
    nrm = normali(sec)

    verts = np.zeros((len(u), nv + 1, 3))
    uvs = np.zeros((len(u), nv + 1, 2))
    for i, ui in enumerate(u):
        a = abs(ui)
        if a <= half - taper:
            k = 0.0
        elif a <= half:
            k = (a - (half - taper)) / taper
            if soft:
                k = k * k * (3.0 - 2.0 * k)   # raccordo senza spigolo di spalla
        else:
            k = 1.0
        sz = (1.0 - k * k) * (1.0 - flat_end) + flat_end
        # l'apertura della pinna si concentra vicino alla saldatura: con una
        # rampa quadratica il gonfiore invade il corpo e deforma la grafica
        sy = 1.0 - (1.0 - width_end) * k ** flare_pow
        sec_i, nrm_i = sec, nrm
        if sul_film is not None and k > 0:
            # l'anello si misura sulla sua forma senza nervature, cosi' tutte
            # le stazioni della pinna tengono gli stessi vertici e le colonne
            # restano dritte
            sec_i = sec_pinna if a > half else sul_film.anello(sy, sz, k)
            nrm_i = normali(sec_i)
        if a > half and crimp_mm > 0:
            # nervature delle ganasce: sono loro a dare alla pinna il grigio
            # rigato che la stacca dal fondo, altrimenti resta bianco su bianco
            ridge = abs(np.sin(np.pi * (a - half) / crimp_period))
            sz += (crimp_mm / max(fp.T / 2.0, 1e-6)) * ridge
        # leggera pancia al centro
        sw = 1.0 + bulge * (1.0 - (ui / max(total, 1e-6)) ** 2)
        uu = ui
        if a > half:                       # dentro la pinna: taglio a zigzag
            # il taglio tocca solo il bordo: l'interno della pinna resta piano,
            # altrimenti il dente si trasforma in una scanalatura lunga 8 mm
            uu = np.sign(ui) * np.minimum(a, total - trim)
        yy = sec_i[:, 0] * sy * (sw if a <= half else 1.0)
        zz = sec_i[:, 1] * sz * (sw if a <= half else 1.0)
        if wrinkle_mm > 0 and a <= half:
            # il film e' lasco e si increspa soprattutto verso le saldature.
            # La grinza va data lungo la normale del contorno: spostando in
            # verticale si schiaccerebbe la sezione e la grafica ne risentirebbe.
            g = (a / max(half, 1e-6)) ** 2
            ph = 2.0 * np.pi * ui / max(fp.L, 1e-6)
            wob = (np.sin(2.0 * np.pi * wrinkle_v * v + 1.7 * ph)
                   + 0.6 * np.sin(2.0 * np.pi * wrinkle_v * 1.9 * v - 1.1 * ph)
                   + 0.5 * np.sin(wrinkle_u * ph + 2.0 * np.pi * v))
            wv = wrinkle_mm * g * wob / 2.1
            yy = yy + wv * nrm_i[:, 0]
            zz = zz + wv * nrm_i[:, 1]
        verts[i, :, 0] = uu
        verts[i, :, 1] = yy
        verts[i, :, 2] = zz
        uvs[i, :, 0] = (ui + total) / (2 * total)
        uvs[i, :, 1] = v

    if spalla_sul_film:
        _stendi_spalla(verts, uvs, u, half, taper)

    V = verts.reshape(-1, 3)
    UV = uvs.reshape(-1, 2)
    idx = lambda i, j: i * (nv + 1) + j
    tris = []
    for i in range(len(u) - 1):
        for j in range(nv):
            a_, b_, c_, e_ = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            # avvolgimento antiorario visto da fuori: con l'ordine opposto il
            # modello si vede rovesciato in ogni viewer che scarta le facce
            # posteriori, ed e' cosi' che la grafica appare capovolta e riflessa
            tris.append((a_, c_, b_))
            tris.append((a_, e_, c_))
    return V, UV, np.array(tris, np.int32)


def build_side_fin(fp: Flowpack, nu: int = 120, nv: int = 8, gap: float = 0.45,
                   fade: float = 12.0):
    """Pinna longitudinale ripiegata sul retro.

    I due bordi del nastro si saldano fra loro e la falda viene coricata contro
    il retro. La grafica della falda e' il film che prosegue oltre la cucitura,
    quindi sullo steso sta subito fuori dalla fascia del perimetro.
    """
    hy, hz = fp.W / 2.0, fp.T / 2.0
    y_seam = hy - fp.back_a
    half = fp.L / 2.0
    x = np.linspace(-half, half, nu + 1)
    s = np.linspace(0.0, 1.0, nv + 1)          # 0 alla piega, 1 alla cimosa

    y0s, web = fp.sheet[1], fp.sheet[3] - fp.sheet[1]
    g0 = fp.girth_span[0]
    fin_pt = fp.side_fin / PT2MM

    V = np.zeros((nu + 1, nv + 1, 3))
    UV = np.zeros((nu + 1, nv + 1, 2))
    for i, xi in enumerate(x):
        k = min(1.0, (half - abs(xi)) / fade)    # la falda si spegne nelle teste
        h = fp.side_fin * (k * k * (3 - 2 * k))
        V[i, :, 0] = xi
        V[i, :, 1] = y_seam - s * h
        V[i, :, 2] = -(hz + gap)
        UV[i, :, 0] = (xi + half + fp.end_fin) / (fp.L + 2 * fp.end_fin)
        UV[i, :, 1] = (g0 - y0s - s * fin_pt) / web

    Vf = V.reshape(-1, 3)
    UVf = UV.reshape(-1, 2)
    idx = lambda i, j: i * (nv + 1) + j
    tris = []
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            tris.append((a, c, b))
            tris.append((a, d, c))
    return Vf, UVf, np.array(tris, np.int32)


def remap_to_sheet(UV, fp: Flowpack):
    """Porta le v del tubo dalla fascia del perimetro all'intero steso."""
    y0s, web = fp.sheet[1], fp.sheet[3] - fp.sheet[1]
    g0, g1 = fp.girth_span
    out = UV.copy()
    out[:, 1] = (g0 - y0s + UV[:, 1] * (g1 - g0)) / web
    return out


def _soft_section(fp: Flowpack, r: float, section_w: float, n_corner: float = 3.0,
                  n_pts: int = 40):
    """Sezione con centro piano e spigoli a curvatura continua.

    Il raccordo circolare lascia un salto di curvatura dove incontra il tratto
    dritto, e sotto luce quel salto si legge come una piega netta. Qui lo
    spigolo e' un quarto di superellisse con esponente > 2: entra ed esce con
    curvatura nulla, quindi la piega si ammorbidisce senza rinunciare al centro
    piano che serve a non deformare la grafica.
    """
    hy, hz = section_w / 2.0, fp.T / 2.0
    y_fin = fp.W / 2.0 - fp.back_a
    p = 2.0 / n_corner

    def corner(cy, cz, sy, sz):
        """Quarto di spigolo dal tratto orizzontale a quello verticale."""
        t = np.linspace(0.0, np.pi / 2.0, n_pts)
        return np.stack([cy + sy * r * np.sin(t) ** p,
                         cz + sz * r * (1.0 - np.cos(t) ** p)], 1)

    path = [np.array([[y_fin, -hz]]), np.array([[hy - r, -hz]])]
    path.append(corner(hy - r, -hz, +1, +1))          # basso destra
    path.append(np.array([[hy, hz - r]]))
    path.append(corner(hy - r, hz, +1, -1)[::-1])     # alto destra
    path.append(np.array([[-(hy - r), hz]]))
    path.append(corner(-(hy - r), hz, -1, -1))        # alto sinistra
    path.append(np.array([[-hy, -hz + r]]))
    path.append(corner(-(hy - r), -hz, -1, +1)[::-1])  # basso sinistra
    path.append(np.array([[y_fin, -hz]]))
    P = np.vstack(path)
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-9]
    P = P[keep]
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    return P, d


def soft_section_fit(fp: Flowpack, r: float, n_corner: float = 3.0):
    """Larghezza che porta il perimetro della sezione morbida a coincidere con
    la circonferenza del film."""
    lo, hi = fp.T, 3.0 * fp.girth
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        _, d = _soft_section(fp, r, mid, n_corner)
        if d[-1] < fp.girth:
            lo = mid
        else:
            hi = mid
    w = 0.5 * (lo + hi)
    P, d = _soft_section(fp, r, w, n_corner)
    return P, d, w


def fin_on_surface(grid, fp: Flowpack, G: float, nv: int, gap: float = 0.5,
                   fade: float = 10.0, u_tubo=None):
    """Pinna longitudinale appoggiata sul retro, che ne segue la forma.

    La falda non e' un rettangolo piatto sospeso: e' film incollato sul retro,
    quindi va costruita come superficie offset della sezione a partire dalla
    cucitura. Cosi' segue pancia, raccordi e grinze del pack invece di
    tagliarli.
    """
    jmax = max(2, int(round(fp.side_fin / G * nv)))
    y0s, web = fp.sheet[1], fp.sheet[3] - fp.sheet[1]
    g0 = fp.girth_span[0]
    half = fp.L / 2.0
    nu = grid.shape[0]

    V = np.zeros((nu, jmax + 1, 3))
    UV = np.zeros((nu, jmax + 1, 2))
    for i in range(nu):
        x = grid[i, 0, 0]
        t = min(1.0, max(0.0, (half - abs(x)) / fade))
        lift = gap * (t * t * (3 - 2 * t))
        for j in range(jmax + 1):
            p = grid[i, j]
            n = np.array([0.0, p[1], p[2]])
            nn = np.linalg.norm(n)
            n = n / nn if nn > 1e-9 else np.array([0.0, 0.0, -1.0])
            V[i, j] = p + lift * n
            s = j / nv * G                      # arco dalla cucitura
            UV[i, j] = (grid[i, j, 0] - grid[0, 0, 0]) / (grid[-1, 0, 0] - grid[0, 0, 0]), \
                       (g0 - y0s - s / PT2MM) / web
        UV[i, :, 0] = (x - grid[0, 0, 0]) / (grid[-1, 0, 0] - grid[0, 0, 0])
        if u_tubo is not None:
            # la falda e' lo stesso film del tubo sotto di lei: stessa u,
            # anche sulla spalla dove il film non va piu' a passo costante
            UV[i, :, 0] = u_tubo[i, :jmax + 1]

    Vf = V.reshape(-1, 3); UVf = UV.reshape(-1, 2)
    idx = lambda i, j: i * (jmax + 1) + j
    tris = []
    for i in range(nu - 1):
        for j in range(jmax):
            a_, b_, c_, e_ = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            tris.append((a_, c_, b_))
            tris.append((a_, e_, c_))
    return Vf, UVf, np.array(tris, np.int32)


def _collapse_guides(vals, max_gap=8.0, tol=0.6):
    """Le due letture possibili di un disegno con guide ravvicinate.

    Tre linee ravvicinate ed equidistanti *possono* essere una piega sola
    disegnata con due guide ai lati - senza fonderle le fasce escono assurde
    (5 | 63 | 5). Ma possono anche essere tre pieghe vere, e il disegno non
    lo dice.

    Questa funzione non decide piu'. Restituisce ENTRAMBE le letture, fuse e
    intere, e lascia che a scegliere sia la credibilita' della soluzione -
    cioe' la falda, che e' una quantita' fisica.

    Il motivo e' misurato. La soglia di 0,6 mm sullo scarto fra i due passi
    decideva tutto, e i disegni ci stanno sopra a cavallo:

        K Brioss STD    341,31 344,81 348,31   scarto 0,00  -> fuse
        K Brioss Promo  341,31 345,15 348,31   scarto 0,67  -> intere

    Stesso pack, stesso disegno tecnico, stesse quote a cartiglio. Fuse, la
    piega a 341,3 sparisce e con lei la quaterna giusta: il pack usciva
    spesso 7 mm invece di 57. Il Promo funzionava per SETTE CENTESIMI di
    millimetro. Mezzo millimetro di differenza fra due disegni simili non
    puo' produrre due pack diversi.
    """
    v = sorted(vals)
    fuse, i = [], 0
    while i < len(v):
        if (i + 2 < len(v) and v[i + 1] - v[i] <= max_gap
                and abs((v[i + 2] - v[i + 1]) - (v[i + 1] - v[i])) <= tol):
            fuse.append(v[i + 1]); i += 3
        else:
            fuse.append(v[i]); i += 1
    # l'ordine conta solo a parita' di merito: prima la lettura intera, che
    # e' quella che non butta via informazione
    return [v, fuse] if fuse != v else [v]


def merito(b):
    """Quanto e' credibile una soluzione. Piu' piccolo, meglio e'.

    Prima la falda: una falda fuori scala non e' una falda, e nessuno scarto
    numerico puo' valere quanto quella. Poi la simmetria, poi quanto passo
    attraversano le quattro pieghe, poi il fronte piu' largo.

    Il passo attraversato viene prima del fronte per via delle guide
    dell'area di stampa. Una piega corre lungo tutto il tubo; una guida si
    ferma alle saldature, perche' li' la stampa finisce. Sul Kinder Cards T2
    le pieghe sono lunghe 108 mm (il passo) e le guide, a 1,5 mm da ogni
    piega, 88: prendendo le guide al posto delle pieghe i conti chiudono lo
    stesso - con la cucitura centrata la simmetria e' zero comunque - e il
    fronte largo vinceva con 46,5 x 15,7 e falda 11,8 invece di 45 x 15 e
    14. La miniatura del file le disegna in due colori, pieghe e area di
    stampa, e le pieghe sono proprio quelle che attraversano il passo.

    Conta la piega PIU' CORTA delle quattro, arrotondata al 5%: un gruppo di
    linee dello stesso tipo ha tutto la stessa lunghezza, e un centesimo di
    rumore non deve decidere. Dove tutte le pieghe sono uguali - Colazione,
    Paradiso, Brioss - il criterio pareggia e decide il fronte come prima.
    """
    return (b["side_fin"] > FALDA_LIMITE, b["simmetria"],
            -b.get("copertura", 0.0), -b["front"])


def solve_bands(web_mm, folds_mm, tol=1.5, copertura=None):
    """Vedi solve_bands_any: la simmetria non vale su tutti i pack.

    `folds_mm` puo' essere una lista di pieghe o piu' LETTURE alternative
    dello stesso disegno (una lista di liste): si risolvono tutte e vince la
    piu' credibile. Serve a non far decidere a un decimo di millimetro quale
    lettura e' giusta - vedi _collapse_guides.

    `copertura` e' `{piega: frazione del passo che la linea attraversa}`,
    con le stesse chiavi di `folds_mm`: vedi `merito`.
    """
    if folds_mm and isinstance(folds_mm[0], (list, tuple)):
        sol = [b for b in (solve_bands_any(web_mm, f, tol, copertura)
                           for f in folds_mm) if b]
        return min(sol, key=merito) if sol else None
    return solve_bands_any(web_mm, folds_mm, tol, copertura)


# Falde misurate su tutti i pack coperti: 4,1 (K Brioss T10) 12,5 (Paradiso)
# 14,0 (Milch-Schnitte) 15,0 (FULFIL) 16,0 (Country), su nastri da 122 a 420
# mm. Non scala col nastro perche' e' il lembo che schiacciano le ganasce, e
# le ganasce non cambiano con la taglia del sacchetto. Il margine e' meta'
# del massimo visto: serve a non escludere una falda davvero grande, non a
# lasciar passare un quarto del film.
FALDA_LIMITE = 24.0


def solve_bands_any(web_mm, folds_mm, tol=2.0, copertura=None):
    """Ricava fronte, fianco e falda enumerando tutte le quaterne di pieghe.

    La versione precedente cercava coppie speculari rispetto alla mezzeria del
    nastro: funziona finche' la cucitura e' centrata sul retro, e fallisce
    quando non lo e' (Kinder Pingui, Kinder Bueno T2). L'invariante che vale
    sempre e' un altro: retro = fronte, fianchi uguali, perimetro + 2 falde =
    nastro.
    """
    copertura = copertura or {}
    import itertools
    best = None
    for y1, y2, y3, y4 in itertools.combinations(sorted(set(folds_mm)), 4):
        sa, front, sb = y2 - y1, y3 - y2, y4 - y3
        if min(sa, front, sb) <= 2 or abs(sa - sb) > tol:
            continue
        fin = (y1 + web_mm - y4 - front) / 2.0
        if not (2 < fin < web_mm * 0.25):
            continue
        ba, bb = y1 - fin, (web_mm - fin) - y4
        if ba < 0 or bb < 0 or abs(ba + bb - front) > tol:
            continue
        cand = dict(front=round(front, 2), thick=round((sa + sb) / 2, 2),
                    side_fin=round(fin, 2), back_a=round(ba, 2),
                    back_b=round(bb, 2), folds=(y1, y2, y3, y4),
                    simmetria=round(abs(ba - bb), 2),
                    copertura=round(20.0 * min(copertura.get(y, 0.0)
                                               for y in (y1, y2, y3, y4))) / 20.0)
        # Prima la falda, poi la simmetria. Su K Brioss STD le due quaterne in
        # gara erano queste:
        #
        #   W 134,93  T  7,00  falda 68,02   simmetria 0,12   <- vinceva
        #   W 134,93  T 67,73  falda  7,29   simmetria 0,65
        #
        # e vinceva la prima per mezzo millimetro di simmetria. A questa scala
        # mezzo millimetro e' rumore del disegno; una falda da 68 mm no. Il
        # pack usciva spesso 7 mm, cioe' piatto, con nastro e passo giusti.
        if best is None or merito(cand) < merito(best):
            best = cand
    return best


def risolvi_pillow(web_mm, folds_mm, tol=2.0):
    """Il tubo piatto chiuso a sovrapposizione: fronte, retro, lembo coperto.

    Non tutti i flowpack hanno la pinna longitudinale. Su un wrap di
    barretta il film si chiude spesso a SOVRAPPOSIZIONE: un bordo passa
    sotto l'altro e non sporge niente. Il pack non ha quindi fianchi: e' un
    tubo piatto, fronte e retro, e gonfiato prende una sezione a ellisse.

    Cambia l'invariante. A pinna vale `perimetro + 2 falde = nastro`; qui
    vale `fronte + retro + lembo = nastro` con `fronte = retro`, cioe' il
    fronte misura mezzo giro. Il K Tronky T1 chiude cosi' al millimetro:

        23 (retro) + 36 (FRONTE) + 12 (retro) + 12 (lembo) = 83
        giro 71, fronte 36, mezzo giro 35,5

    e la fascia da 36 e' proprio quella che il disegno marca TEXT
    ORIENTATION, come vuole la regola del pannello marcato.

    Il lembo sta a un capo del nastro o all'altro, e si provano tutti e due.
    Vince la lettura in cui il fronte e' piu' vicino a mezzo giro.
    """
    v = sorted(set([0.0] + [float(x) for x in folds_mm] + [float(web_mm)]))
    best = None
    for coda in (True, False):
        for s_ in v:
            lembo = (web_mm - s_) if coda else s_
            if not (2.0 < lembo < web_mm * 0.25):
                continue
            g0 = 0.0 if coda else lembo
            g1 = s_ if coda else web_mm
            giro = g1 - g0
            for i2, y1 in enumerate(v):
                if not (g0 <= y1 < g1):
                    continue
                for y2 in v[i2 + 1:]:
                    if y2 > g1:
                        break
                    fronte = y2 - y1
                    err = abs(fronte - giro / 2.0)
                    if err > tol or fronte <= 2.0:
                        continue
                    ba, bb = y1 - g0, g1 - y2
                    if min(ba, bb) < 0:
                        continue
                    cand = dict(front=round(fronte, 2),
                                sovrapposizione=round(lembo, 2),
                                back_a=round(ba, 2), back_b=round(bb, 2),
                                giro=round(giro, 2), inizio=round(g0, 2),
                                scarto=round(err, 2))
                    if best is None or cand["scarto"] < best["scarto"]:
                        best = cand
    return best


def _solve_bands_symmetric(web_mm, folds_mm, tol=1.5):
    """Ricava fronte, fianco e falda longitudinale dalle pieghe.

    Su un flowpack la fasciatura e' simmetrica rispetto alla mezzeria del
    nastro, quindi le pieghe stanno a coppie speculari: quella esterna separa
    retro e fianco, quella interna fianco e fronte. Verificato su
    Milch-Schnitte, FULFIL e Kinder Bueno Dark.
    """
    mid = web_mm / 2.0
    pairs = []
    for a in folds_mm:
        if a >= mid:
            continue
        b = min((x for x in folds_mm if abs(x - (web_mm - a)) <= tol),
                key=lambda x: abs(x - (web_mm - a)), default=None)
        if b is not None:
            pairs.append((a, b))
    pairs.sort()

    best = None
    for i, (y1, y4) in enumerate(pairs):
        for y2, y3 in pairs[i + 1:]:
            T = ((y2 - y1) + (y4 - y3)) / 2.0
            front = y3 - y2
            fin = (y1 + web_mm - y4 - front) / 2.0
            if T <= 0 or front <= T or not (2.0 < fin < web_mm * 0.2):
                continue
            back_a, back_b = y1 - fin, (web_mm - fin) - y4
            if abs((back_a + back_b) - front) > tol:
                continue
            cand = dict(front=round(front, 2), thick=round(T, 2),
                        side_fin=round(fin, 2), back_a=round(back_a, 2),
                        back_b=round(back_b, 2), folds=(y1, y2, y3, y4))
            if best is None or cand["front"] > best["front"]:
                best = cand
    return best


class _StesoNonRisolto(ValueError):
    """Le fasce non chiudono su questo asse: forse lo steso e' ruotato."""


# Risoluzione a cui l'analisi guarda la pagina. E' anche la piu' alta che
# serva al flusso su un foglio grande, quindi chi rasterizza per primo lo fa
# a questa e gli altri riscalano: vedi dieline.render_page.
SCALA_ANALISI = 150 / 72.0


def analyze_auto(pdf_path, page_no: int = 0, bbox=None):
    """Analisi automatica di un flowpack: nastro, passo, fasce e saldature.

    Copre gli impaginati in cui il disegno tecnico traccia le cordonature; per
    gli artwork che non rientrano resta il registro dei casi calibrati.
    """
    import numpy as np
    from .dieline import _technical_pens, render_page
    from .tracciati import segmenti

    # I tracciati li legge pypdfium2, non pdfplumber: stessa informazione,
    # un decimo del tempo e un sesto della memoria. Vedi tracciati.py.
    if True:
        segs, pagina_w, pagina_h = segmenti(pdf_path, page_no)
        if bbox:
            # una tavola contiene piu' viste: senza riquadro si misura il foglio
            bx0, by0, bx1, by1 = bbox
            def _in(sg):
                k, c, a0, b0, _ = sg
                if k == "H":
                    return by0 - 3 <= c <= by1 + 3 and a0 >= bx0 - 3 and b0 <= bx1 + 3
                return bx0 - 3 <= c <= bx1 + 3 and a0 >= by0 - 3 and b0 <= by1 + 3
            segs = [sg for sg in segs if _in(sg)]
        pens = _technical_pens(segs, pagina_w, pagina_h)
        S = [s for s in segs if s[4] in pens]

    # pdfplumber si tiene un oggetto Python per ogni tracciato della pagina, e
    # su un impaginato grande sono decine di migliaia: centinaia di MB che il
    # `with` chiude ma che l'allocatore non restituisce da solo. Qui sotto si
    # rasterizza, e le due cose sommate sono il picco. Una raccolta esplicita
    # prima di allocare costa millisecondi.
    import gc
    gc.collect()

    sc = SCALA_ANALISI
    im = render_page(pdf_path, page_no, sc)
    # int16, non int: su un foglio come quello del Brioss la rasterizzazione a
    # 150 dpi e' una ventina di MB in uint8, e .astype(int) li moltiplica per
    # otto perche' int e' int64. Del raster qui serve solo max(2)-min(2) su
    # canali 0-255: int16 basta e avanza. Misurato: il picco della sola
    # analisi passa da 501 a 205 MB.
    raster = np.asarray(im).astype(np.int16)

    # Le pinne stanno in verticale o in orizzontale a seconda delle proporzioni,
    # ma lo schema e' lo stesso ruotato di 90 gradi. Invece di insegnare
    # l'orientamento al solutore si traspongono i suoi ingressi: i segmenti
    # scambiando H con V, la rasterizzazione scambiando righe e colonne. Cosi'
    # il solutore resta uno solo e lavora sempre nel verso che conosce. Si
    # parte dall'orizzontale, che e' il piu' comune.
    # Quattro tentativi: due chiusure per due versi. Prima la pinna in tutti e
    # due i versi, poi la sovrapposizione.
    #
    # L'ordine conta, e l'ho imparato rompendolo: "le fasce non chiudono" e'
    # anche il segnale che lo steso e' girato di 90 gradi. Provando l'altra
    # chiusura prima dell'altro verso, il K Brioss - che va letto ruotato -
    # trovava una lettura plausibile nel verso sbagliato, e il verso giusto
    # non veniva mai provato.
    primo = None
    for modo in ("pinna", "pillow"):
        for ruotato in (False, True):
            try:
                return _risolvi_steso(S, raster, sc, ruotato, modo)
            except _StesoNonRisolto as e:
                # Si tiene il MESSAGGIO, non l'oggetto eccezione. Un'eccezione si
                # porta dietro il traceback, il traceback il frame di
                # _risolvi_steso, e il frame tutti i suoi locali: le
                # rasterizzazioni intermedie del tentativo fallito restavano vive
                # per tutto il secondo tentativo. Su un foglio grande sono
                # centinaia di MB tenuti in ostaggio da una variabile che serve
                # solo a ricordare una frase.
                primo = primo or str(e)
            # si passa all'altro verso; al giro dopo si torna a questo
            S = [("V" if k == "H" else "H", c, a0, b0, st)
                 for k, c, a0, b0, st in S]
            raster = raster.transpose(1, 0, 2)
    raise _StesoNonRisolto(primo)


# Fin dove, da un taglio verso l'interno, si cerca la testata: oltre un terzo
# del passo si e' nel corpo, e una linea li' e' una cordonatura della
# grafica, non una saldatura.
TESTATA_MAX = 0.3


def _strutture(dist):
    """Le linee di una testata in ordine dal taglio: `[(mm, piega)]`.

    Tre linee ravvicinate ed equidistanti sono una piega sola, quella di mezzo,
    disegnata con due guide ai lati: e' la stessa lettura di
    `_collapse_guides`, e sulla testata la conferma la quota. Su Colazione il
    cartiglio scrive 20 | 37,5 | 215 | 37,5 | 20, e le guide stanno a 52,5,
    57,5 e 62,5: la piega e' a 57,5 = 20 + 37,5.
    """
    v = sorted(dist)
    fuori, i = [], 0
    while i < len(v):
        if (i + 2 < len(v) and v[i + 1] - v[i] <= 8.0
                and abs((v[i + 2] - v[i + 1]) - (v[i + 1] - v[i])) <= 0.6):
            fuori.append((v[i + 1], True))
            i += 3
        else:
            fuori.append((v[i], False))
            i += 1
    return fuori


def testate_dal_dt(vs, x0, x1):
    """Pinna di testa e gola lette dal disegno tecnico. `(pinna, gola, righe)`.

    `vs` sono le linee lunghe che attraversano il nastro, `x0` e `x1` i due
    tagli, in punti nel telaio del solutore. `pinna` e' None se il disegno non
    dice niente, e allora chi chiama ricade sullo stampato.

    La regola e' **prima le misure, poi il contenuto**. La pinna si misurava
    dal margine non stampato, e il margine non stampato non e' la pinna quando
    la grafica ha del bianco: su Colazione il fronte ha una fascia bianca sopra
    il marchio, e il margine veniva 41,2 mm contro i 20 della saldatura -
    quella che il DT disegna e il cartiglio quota. Sul Brioss STD usciva 32,6
    contro i 37,6 della piega, che e' la misura su cui la gola e' tarata.

    Dal taglio verso l'interno:

    - la prima linea e' la SALDATURA, e la pinna finisce li';
    - la seconda e' dove finisce il prodotto, e fra le due c'e' la GOLA: il
      tubo che si schiaccia verso la pinna. Il DT la chiama zona grinze
      (KMS, KP: 10 mm) o la quota come tratto a se' (Colazione: 37,5);
    - se la prima struttura e' una piega con le sue guide, la saldatura non e'
      disegnata e la testata arriva alla piega: e' il film che avvolge una
      scatola (Brioss), dove la gola la decide lo spessore.

    I due lati devono dire la stessa cosa. Se non la dicono, per la pinna si
    tiene il rientro piu' stretto - la regola che c'era gia' per le saldature
    - e la gola non si usa: un solo lato non basta a dire dove finisce il
    prodotto.
    """
    passo = (x1 - x0) * PT2MM
    lim = TESTATA_MAX * passo

    def lato(dist):
        dist = [d for d in dist if 0.3 < d <= lim]
        if not dist:
            return None
        st = _strutture(dist)
        primo, piega = st[0]
        if piega:
            return primo, None, "piega"
        return primo, (st[1][0] - primo if len(st) > 1 else None), "saldatura"

    sx = lato([(c - x0) * PT2MM for c in vs])
    dx = lato([(x1 - c) * PT2MM for c in vs])
    righe = []
    if sx is None and dx is None:
        return None, 0.0, righe
    if sx is None or dx is None:
        uno = sx or dx
        righe.append("testata letta da un lato solo: il DT dall'altro non "
                     "segna niente")
        return round(uno[0], 1), 0.0, righe
    (a, ga, ka), (b, gb, kb) = sx, dx
    if abs(a - b) <= 0.5:
        pinna = round((a + b) / 2.0, 1)
    else:
        pinna = round(min(a, b), 1)
        righe.append("rientri diversi (%.1f e %.1f mm) su un disegno "
                     "speculare: tengo il piu' stretto" % (a, b))
    gola = 0.0
    if ka == kb == "saldatura" and ga is not None and gb is not None:
        if abs(ga - gb) <= 1.0:
            gola = round((ga + gb) / 2.0, 1)
        else:
            righe.append("gola diversa ai due capi (%.1f e %.1f mm): non la "
                         "uso" % (ga, gb))
    if ka == kb == "piega":
        righe.append("testate dal DT: piega a %.1f mm dal taglio, saldatura "
                     "non disegnata" % pinna)
    else:
        righe.append("testate dal DT: saldatura %.1f mm%s" % (
            pinna, ", gola %.1f fino alla fine del prodotto" % gola
            if gola else ""))
    return pinna, gola, righe


def _copre(linee, c, a0, a1, tol=3.0):
    """Frazione di `[a0, a1]` coperta dalle `linee` `(c, a, b)` vicine a `c`.

    Si misura l'UNIONE dei tratti, non la somma: una piega disegnata due
    volte non attraversa il passo due volte. `tol` e' quella di `_cluster`
    che ha raccolto il gruppo.
    """
    tratti = sorted((max(a, a0), min(b, a1)) for cc, a, b in linee
                    if abs(cc - c) <= tol and min(b, a1) > max(a, a0))
    tot, fine = 0.0, a0
    for a, b in tratti:
        if b > fine:
            tot += b - max(a, fine)
            fine = b
    return tot / (a1 - a0) if a1 > a0 else 0.0


def _risolvi_steso(S, raster, sc, ruotato, modo="pinna"):
    """Ricava il flowpack da segmenti e rasterizzazione gia' orientati."""
    from .dieline import _cluster

    # Le soglie erano assolute, 150 e 250 punti, e non possono esserlo: fra il
    # nastro di K Tronky (83 mm) e quello di K Brioss (420 mm) c'e' un fattore
    # cinque. Una linea che attraversa TUTTO il nastro del Tronky e' lunga 83
    # mm, sotto gli 88,2 mm che servivano per essere presa sul serio, quindi
    # nessuna cordonatura verticale passava e lo steso risultava non coperto.
    # Si misura invece in frazione del tratto piu' lungo, che e' il contorno
    # dello steso: sui formati gia' coperti le due frazioni valgono quanto le
    # vecchie costanti.
    # La frazione puo' solo ABBASSARE la soglia, mai alzarla: `min` con la
    # costante vecchia. Renderla relativa e basta l'aveva alzata sugli steso
    # piu' lunghi del riferimento, e su Milch-Schnitte T1 si perdeva la
    # cordonatura a 108,5 mm - il cui gruppo misura fra gli 88,2 mm della
    # vecchia soglia e i 91,5 della nuova. Senza quella piega solve_bands non
    # chiude piu', ed e' esattamente il difetto che le regole descrivono per
    # Kinder Bueno T2: un filtro troppo stretto in ingresso e nessun solutore
    # a valle puo' rimediare. Le costanti restano la taratura buona sugli
    # impaginati gia' coperti; la frazione serve solo a non escludere gli
    # steso piccoli, dove una linea che attraversa tutto il nastro e' comunque
    # piu' corta della costante (K Tronky, nastro 83 mm).
    ext_h = max((b - a for k, c, a, b, st in S if k == "H"), default=0.0)
    ext_v = max((b - a for k, c, a, b, st in S if k == "V"), default=0.0)
    seg_h, seg_v = min(150.0, 0.35 * ext_h), min(150.0, 0.35 * ext_v)
    grp_h, grp_v = min(250.0, 0.60 * ext_h), min(250.0, 0.60 * ext_v)
    H = [(c, b - a) for k, c, a, b, st in S if k == "H" and b - a > seg_h]
    V = [(c, b - a) for k, c, a, b, st in S if k == "V" and b - a > seg_v]
    hs = [c for c, w in _cluster(H, 3.0) if w > grp_h]
    vs = [c for c, w in _cluster(V, 3.0) if w > grp_v]
    if len(hs) < 4 or len(vs) < 2:
        raise _StesoNonRisolto("cordonature non riconosciute: impaginato non coperto")

    y0, y1 = min(hs), max(hs)
    x0, x1 = min(vs), max(vs)
    web, step = (y1 - y0) * PT2MM, (x1 - x0) * PT2MM
    folds = _collapse_guides([(c - y0) * PT2MM for c in hs])
    # quanto passo attraversa ogni piega: separa le pieghe dalle guide
    # dell'area di stampa, che si fermano alle saldature. Vedi `merito`.
    lunghe = [(c, a, b) for k, c, a, b, st in S if k == "H" and b - a > seg_h]
    copertura = {(c - y0) * PT2MM: _copre(lunghe, c, x0, x1) for c in hs}
    avvisi = []
    if modo == "pinna":
        b = solve_bands(web, folds, copertura=copertura)
        if b is None:
            raise _StesoNonRisolto("fasce non risolvibili: nastro %.1f mm" % web)
        lembo, inizio = 0.0, b["side_fin"]
        giro = 2.0 * (b["front"] + b["thick"])
        spessore, falda = b["thick"], b["side_fin"]
    else:
        sol = [q for q in (risolvi_pillow(web, f) for f in folds) if q]
        b = min(sol, key=lambda q: q["scarto"]) if sol else None
        if b is None:
            raise _StesoNonRisolto("ne' a pinna ne' a sovrapposizione: "
                                   "nastro %.1f mm" % web)
        lembo, inizio, giro = b["sovrapposizione"], b["inizio"], b["giro"]
        spessore, falda = 0.0, 0.0
        avvisi.append("chiusura a sovrapposizione: lembo coperto %.1f mm, "
                      "giro %.1f, fronte %.1f su mezzo giro %.1f"
                      % (lembo, giro, b["front"], giro / 2.0))

    # Pinne di testa: PRIMA il disegno tecnico. Lo stampato si guarda solo se
    # il DT sulle testate non dice niente - vedi testate_dal_dt per perche'.
    end_fin, gola, righe = testate_dal_dt(vs, x0, x1)
    avvisi.extend(righe)
    if end_fin is None:
        end_fin, gola = _testate_dallo_stampato(raster, sc, x0, x1, y0,
                                                inizio, b, spessore), 0.0
        avvisi.append("testate: il DT non segna la saldatura, pinna %.1f mm "
                      "dal margine non stampato - e' una stima, la grafica "
                      "puo' avere del bianco" % end_fin)
        if end_fin < 1.0:
            raise ValueError("pinne di testa non misurabili: il DT non segna "
                             "le saldature e la fascia fronte non ha margine "
                             "non stampato")

    if ruotato:
        avvisi.append("steso ruotato di 90 gradi: le pinne corrono in verticale")
    # sheet e girth_span restano nel telaio in cui ha lavorato il solutore: chi
    # ritaglia la texture lo rimette dritto guardando `ruotato`.
    return Flowpack(W=b["front"], T=spessore, L=round(step - 2 * end_fin, 1),
                    end_fin=end_fin, side_fin=falda, warnings=avvisi, gola=gola,
                    linee_passo=tuple(round((c - x0) * PT2MM, 2)
                                      for c in sorted(vs) if x0 < c < x1),
                    back_a=b["back_a"], back_b=b["back_b"],
                    sovrapposizione=lembo,
                    web_mm=round(web, 1), step_mm=round(step, 1),
                    sheet=(x0, y0, x1, y1), ruotato=ruotato,
                    # a pinna il giro si ancora ai due bordi misurati del
                    # nastro, non si accumula dalle fasce: accumulare sposta
                    # il secondo capo di quel poco che il solutore tollera.
                    # A sovrapposizione il lembo sta da un lato solo, quindi
                    # il secondo capo lo da' il giro.
                    girth_span=((y0 + falda / PT2MM, y1 - falda / PT2MM)
                                if not lembo else
                                (y0 + inizio / PT2MM,
                                 y0 + (inizio + giro) / PT2MM)))


def riporta_da_copia(fp, copia, dt, riga=None):
    """Un Flowpack letto su una COPIA del DT, riportato sul DT con la grafica.

    `copia` e `dt` sono i riquadri `(x, y, w, h)` dei due disegni, in punti
    nel telaio di misura. La copia e' lo stesso DT in scala - una copia
    tecnica, la miniatura del cartiglio - e la stessa affinita' che porta il
    suo riquadro su quello del DT porta le sue linee: le misure lungo il
    nastro e lungo il passo si scalano ognuna col suo asse, e lo steso e il
    perimetro utile finiscono sul DT, da dove si ritaglia la grafica.
    """
    from dataclasses import replace
    cx, cy, cw, ch = copia
    dx, dy, dw, dh = dt
    kx, ky = dw / cw, dh / ch

    def px(x):
        return dx + (x - cx) * kx

    def py(y):
        return dy + (y - cy) * ky

    s0, s1, s2, s3 = fp.sheet
    g0, g1 = fp.girth_span
    if fp.ruotato:
        # nel telaio del solutore la x e' la y della pagina, e viceversa
        sheet = (py(s0), px(s1), py(s2), px(s3))
        girth = (px(g0), px(g1))
        kn, kp = kx, ky
    else:
        sheet = (px(s0), py(s1), px(s2), py(s3))
        girth = (py(g0), py(g1))
        kn, kp = ky, kx
    avvisi = list(fp.warnings)
    if riga:
        avvisi.append(riga)
    return replace(
        fp, W=round(fp.W * kn, 2), T=round(fp.T * kn, 2),
        side_fin=round(fp.side_fin * kn, 2), back_a=round(fp.back_a * kn, 2),
        back_b=round(fp.back_b * kn, 2),
        sovrapposizione=round(fp.sovrapposizione * kn, 2),
        web_mm=round(fp.web_mm * kn, 1),
        L=round(fp.L * kp, 1), end_fin=round(fp.end_fin * kp, 1),
        gola=round(fp.gola * kp, 1), step_mm=round(fp.step_mm * kp, 1),
        linee_passo=tuple(round(v * kp, 2) for v in fp.linee_passo),
        sheet=sheet, girth_span=girth, warnings=avvisi)


def foglio_in_pagina(fp):
    """Il riquadro dello steso nel telaio della pagina, `(x0, y0, x1, y1)`.

    `fp.sheet` sta nel telaio del solutore, che per uno steso ruotato ha x e
    y scambiate: e' da qui che si ritaglia la texture, ed e' il DT fuori dal
    quale la costruzione toglie tutto.
    """
    sh = fp.sheet
    return (sh[1], sh[0], sh[3], sh[2]) if fp.ruotato else tuple(sh)


def _testate_dallo_stampato(raster, sc, x0, x1, y0, inizio, b, spessore):
    """La pinna dal margine non stampato della fascia fronte: il ripiego.

    La zona non stampata e' quella che finisce nelle ganasce - quando lo e'. Se
    la grafica ha del bianco vicino alla testata il margine si allunga fino a
    lui, ed e' per questo che si guarda solo quando il DT tace.
    """
    import numpy as np
    fy0 = y0 + (inizio + b["back_a"] + spessore) / PT2MM
    fy1 = fy0 + b["front"] / PT2MM
    band = raster[int(fy0 * sc):int(fy1 * sc), int(x0 * sc):int(x1 * sc)]
    ch = (band.max(2) - band.min(2)).mean(0)
    mm = np.arange(len(ch)) / sc * PT2MM
    idx = np.nonzero(ch > 25)[0]
    if not len(idx):
        return 0.0
    return round(float((mm[idx[0]] + (mm[-1] - mm[idx[-1]])) / 2.0), 1)


def riquadro_fustella(pdf_path, page_no: int = 0, stampato=None, tol: float = 1.0,
                      entro=None):
    """Il rettangolo che la fustella CHIUDE, in punti PDF, o `None`.

    Serve quando l'ingombro dello stampato non e' la fustella. Sul Kinder
    Choco Fresh T1 la grafica scende sotto il tracciato - c'e' una striscia
    di fondo bianco che il disegno non comprende - e misurando lo stampato il
    nastro veniva 121 mm invece di 115: le fasce non chiudevano piu' e il file
    non si costruiva. La fustella invece si riconosce senza ambiguita', perche'
    e' **chiusa**: due orizzontali della stessa larghezza, due verticali della
    stessa altezza, e i quattro angoli che coincidono.

    Non e' un'euristica sul colore ne' sullo spessore: e' una condizione
    geometrica, o i quattro tratti chiudono o non chiudono.

    Di rettangoli chiusi una tavola ne ha parecchi - la cornice del foglio, i
    cartigli, i riquadri della legenda - e prendere il piu' grande da' la
    cornice. Vince invece quello che **somiglia di piu' all'ingombro
    stampato**, per sovrapposizione: la fustella e' il rettangolo in cui la
    grafica sta. Senza `stampato` non si sceglie e si torna `None`, perche'
    senza riferimento la scelta sarebbe un'altra euristica.
    """
    from .tracciati import segmenti

    if stampato is None:
        return None
    try:
        segs, _w, _h = segmenti(pdf_path, page_no)
        S = segs
    except Exception:
        return None

    if entro is not None:
        # Solo i segmenti in quel riquadro: la ricerca prova ogni coppia di
        # orizzontali con ogni coppia di verticali, e su una tavola piena di
        # note - il Nutella B-ready T2 - sulla pagina intera non finiva.
        ex0, ey0, ex1, ey1 = entro
        S = [x for x in S
             if (x[0] == "H" and ey0 <= x[1] <= ey1 and x[3] >= ex0
                 and x[2] <= ex1)
             or (x[0] == "V" and ex0 <= x[1] <= ex1 and x[3] >= ey0
                 and x[2] <= ey1)]
    H = [(c, a, b) for k, c, a, b, st in S if k == "H"]
    V = [(c, a, b) for k, c, a, b, st in S if k == "V"]
    if len(H) < 2 or len(V) < 2:
        return None

    px0, py0, px1, py1 = stampato
    area_st = max(1e-6, (px1 - px0) * (py1 - py0))

    def somiglianza(x0, y0, x1, y1):
        """Sovrapposizione fra il rettangolo e l'ingombro stampato, 0..1."""
        ix = max(0.0, min(x1, px1) - max(x0, px0))
        iy = max(0.0, min(y1, py1) - max(y0, py0))
        inter = ix * iy
        unione = (x1 - x0) * (y1 - y0) + area_st - inter
        return inter / unione if unione > 0 else 0.0

    # I lati devono COPRIRE il rettangolo, non coincidere con esso. Una
    # fustella sborda: sul Choco Fresh la verticale di destra scende 6 mm sotto
    # l'orizzontale di sotto, e pretendendo che gli estremi combaciassero il
    # rettangolo giusto veniva scartato.
    copre = lambda a, b, p, q: a <= p + tol and b >= q - tol
    migliore = None
    for i, (y0, hx0, hx1) in enumerate(H):
        for y1, gx0, gx1 in H[i + 1:]:
            alto, basso = min(y0, y1), max(y0, y1)
            if basso - alto <= tol:
                continue
            for x0, va0, va1 in V:
                if not copre(va0, va1, alto, basso):
                    continue
                for x1, vb0, vb1 in V:
                    if x1 - x0 <= tol or not copre(vb0, vb1, alto, basso):
                        continue
                    # e le due orizzontali devono coprire da x0 a x1
                    if not (copre(hx0, hx1, x0, x1) and copre(gx0, gx1, x0, x1)):
                        continue
                    q = somiglianza(x0, alto, x1, basso)
                    if migliore is None or q > migliore[0]:
                        migliore = (q, (x0, alto, x1, basso))
    if migliore is None or migliore[0] < 0.5:
        return None
    return migliore[1]
