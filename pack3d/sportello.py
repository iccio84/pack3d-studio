"""
La scatola chiusa con la plancia RICAVATA DENTRO il coperchio.

Il caso e1b3cc77a7 (un display per dieci flowpack): la scatola arriva chiusa,
come un astuccio basso - coperchio stampato, quattro pareti, un fondo bianco -
e si apre da un contorno perforato tutto dentro il coperchio. Il contorno ha
il lato dritto sulla cordonatura del retro, che fa da cerniera, i fianchi
lungo i fianchi del coperchio, gli angoli smussati, e davanti una linguetta
che sconfina nella parete del fronte: e' l'attacco per il dito. Una riga lo
attraversa a meta'.

Aperto: lo sportello si alza sulla cerniera del retro, e la meta' davanti si
ripiega sulla riga di mezzo, verso chi guarda. La plancia sta in piedi sul
retro, alta mezzo sportello, con la meta' davanti stampata verso chi guarda e
la meta' dietro verso il retro; del coperchio resta la cornice, gli angoli
fuori dal contorno, e la scatola sotto e' aperta col prodotto dentro.

Non e' il display con plancia di `pack3d.plancia`: li' il coperchio e' un
pannello a se' oltre una parete, che si stacca intero; qui il coperchio resta
al suo posto e la plancia e' un pezzo ritagliato dentro di lui. Si prova DOPO
il vassoio e la plancia, quando hanno rifiutato il foglio: i casi del parco
non cambiano strada.

La firma, sulla griglia della fustella (tutte, nel verso in cui il retro sta
in alto sul foglio - `riconosci_sulla_tavola` gira il foglio di un quarto,
mezzo e tre quarti):

- il COPERCHIO, un rettangolo di righe di almeno 40 mm per lato, con una
  parete su ognuno dei quattro lati;
- il FONDO, un pannello grande quanto il coperchio (0,9-1,1 della larghezza)
  oltre la parete di UN fianco solo: e' la scatola che gira attorno;
- la RIGA di mezzo, una riga orizzontale dentro il coperchio, fra il 35 e il
  65 per cento della lunghezza, lunga quasi quanto il coperchio e' largo;
- i FIANCHI dello sportello, due righe verticali dentro il coperchio, a meno
  di 5 mm dai suoi fianchi, che coprono almeno meta' della lunghezza;
- il FRONTE, la testata dove il contorno sconfina nella parete (la
  linguetta): tratti della fustella dentro quella parete, lontani dai suoi
  bordi. Il retro non ne ha. Se nessuna delle due testate ne ha, o tutte e
  due, non si sa da che parte si apre, e non e' questa forma.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .dieline import PT2MM
from .plancia import (COPERCHIO, COPRE, COPRE_FIANCO, FONDO_MINIMO, GRIGLIA,
                      MARGINE, Pezzi, TRATTO_PX, _al_piu_vicino, _copre, _corse,
                      _prima, _su, tratti)
from .vassoio import SPESSORE, Maglia

MM = 1.0 / PT2MM
# dove sta la riga di mezzo, in frazione della lunghezza del coperchio
RIGA = (0.35, 0.65)
# quanto lontano dal fianco del coperchio puo' stare il fianco dello sportello
FIANCO_SPORTELLO = 5.0 * MM
# quanto della lunghezza del coperchio deve coprire il fianco dello sportello
COPRE_SPORTELLO = 0.5
# la linguetta: tratti nella parete del fronte, almeno cosi' lontani dai bordi
LINGUETTA_BORDO = 2.0 * MM
# una parete piu' alta o piu' bassa delle altre di tanto si dice
PARETE_DIVERSA = 1.5
# la parete del fianco col fondo, al piu' tanto della larghezza del coperchio
PARETE_MASSIMA = 0.75
# le zone piu' piccole di cosi' sono fori e intagli, non cartone
ZONA_MINIMA = 4.0          # mm quadrati


@dataclass
class Sportello:
    """Quello che si legge sul foglio, in punti PDF con la y dall'alto, nel
    verso in cui il retro sta in alto."""
    coperchio: tuple          # (x0, y0, x1, y1)
    bordi: dict               # ovest, est, nord, sud: il bordo esterno di ogni parete
    fondo: tuple              # (xa, xb): la piega col fianco e il lato libero
    lato_fondo: str           # "ovest" o "est"
    riga: float               # la y della riga di mezzo
    fianchi: tuple            # le x dei fianchi dello sportello
    warnings: list = field(default_factory=list)

    @property
    def pareti(self):
        """L'altezza di ogni parete sul foglio, in mm."""
        x0, y0, x1, y1 = self.coperchio
        b = self.bordi
        return {"ovest": (x0 - b["ovest"]) * PT2MM, "est": (b["est"] - x1) * PT2MM,
                "nord": (y0 - b["nord"]) * PT2MM, "sud": (b["sud"] - y1) * PT2MM}

    @property
    def alto(self):
        """L'altezza della scatola: la mediana delle quattro pareti, cosi' una
        parete che sul foglio ha una falda in piu' non la decide da sola."""
        h = sorted(self.pareti.values())
        return (h[1] + h[2]) / 2.0

    @property
    def dims_mm(self):
        x0, y0, x1, y1 = self.coperchio
        return ((x1 - x0) * PT2MM, self.alto, (y1 - y0) * PT2MM)

    @property
    def mezzo_mm(self):
        """La parte dietro dello sportello, dalla cerniera alla riga: e'
        l'altezza della plancia sopra la scatola."""
        return (self.riga - self.coperchio[1]) * PT2MM


def _fondo(V, H, x0, y0, x1, y1, bordo, verso):
    """Il fondo oltre la parete di un fianco: `(xa, xb)`, o None.

    Due righe oltre il fianco che coprono la lunghezza del coperchio,
    distanti quanto il coperchio e' largo: la piega col fianco e il lato
    libero, con i lati di testa sulle righe del coperchio. La prima riga
    oltre il coperchio puo' essere una cordonatura in mezzo alla parete, e
    allora la parete arriva fino alla piega del fondo.
    """
    largo = x1 - x0
    oltre = sorted((r for r in V if (r[0] - bordo) * verso > GRIGLIA
                    and _copre(r, y0, y1, COPRE_FIANCO)),
                   key=lambda r: abs(r[0] - bordo))
    # Non per forza di fila: dentro il fondo ci possono essere altre righe,
    # il riquadro della colla o la feritoia della chiusura.
    for i, a in enumerate(oltre):
        if abs(a[0] - bordo) > PARETE_MASSIMA * largo:
            break
        buoni = []
        for b in oltre[i + 1:]:
            if not COPERCHIO[0] <= abs(b[0] - a[0]) / largo <= COPERCHIO[1]:
                continue
            fa, fb = sorted((a[0], b[0]))
            # un pannello vero, chiuso in testa: senza, due righe a caso
            # oltre il fianco - la cordonatura della parete e il riquadro
            # della colla - sembravano un fondo largo giusto
            if _su(H, y0, fa, fb) and _su(H, y1, fa, fb):
                buoni.append(b)
        if buoni:
            # il lato libero e' la riga che fa il fondo piu' simile al
            # coperchio: dentro il fondo puo' esserci il riquadro della colla
            b = min(buoni, key=lambda r: abs(abs(r[0] - a[0]) - largo))
            return a[0], b[0]
    return None


def _linguetta(linee, x0, x1, ya, yb):
    """Se dentro la parete fra ya e yb ci sono tratti lontani dai bordi."""
    a, b = min(ya, yb) + LINGUETTA_BORDO, max(ya, yb) - LINGUETTA_BORDO
    l0, l1 = x0 + 0.2 * (x1 - x0), x1 - 0.2 * (x1 - x0)
    return any(l0 <= x <= l1 and a <= y <= b for linea in linee for x, y in linea)


def riconosci(d, linee):
    """`Sportello` dalla griglia della fustella e dai suoi tratti, o None.

    `d` e' quello di `dieline.extract`, `linee` i tratti di `plancia.tratti`
    (servono per la linguetta, che e' una curva). Solo nel verso col retro in
    alto: gli altri versi li prova `riconosci_sulla_tavola`.
    """
    V = _corse(getattr(d, "vsegs", None) or [])
    H = _corse(getattr(d, "hsegs", None) or [])
    for i, v0 in enumerate(V):
        for v1 in V[i + 1:]:
            x0, x1 = sorted((v0[0], v1[0]))
            if x1 - x0 < FONDO_MINIMO:
                continue
            for j, h0 in enumerate(H):
                for h1 in H[j + 1:]:
                    y0, y1 = sorted((h0[0], h1[0]))
                    if y1 - y0 < FONDO_MINIMO:
                        continue
                    if not (_copre(h0, x0, x1) and _copre(h1, x0, x1)
                            and _copre(v0, y0, y1) and _copre(v1, y0, y1)):
                        continue
                    s = _attorno(V, H, linee, x0, y0, x1, y1)
                    if s is not None:
                        return s
    return None


def _attorno(V, H, linee, x0, y0, x1, y1):
    ovest = _prima(V, x0, -1, y0, y1)
    nord = _prima(H, y0, -1, x0, x1)
    sud = _prima(H, y1, +1, x0, x1)
    if None in (ovest, nord, sud):
        return None
    # il fondo oltre UNO dei due fianchi
    cand = []
    for lato, bordo, verso in (("est", x1, +1), ("ovest", x0, -1)):
        f = _fondo(V, H, x0, y0, x1, y1, bordo, verso)
        if f is not None:
            cand.append((lato, f))
    if len(cand) != 1:
        return None
    lato_fondo, fondo = cand[0]
    if lato_fondo == "est":
        est = fondo[0]
    else:
        est = _prima(V, x1, +1, y0, y1)
        if est is None:
            return None
        est = est[0]
        if ovest[0] - fondo[0] > GRIGLIA:
            # anche a ovest la parete arriva fino alla piega del fondo
            ovest = (fondo[0],) + tuple(ovest[1:])
    # la riga di mezzo
    lungo = y1 - y0
    righe = [r for r in H if y0 + RIGA[0] * lungo <= r[0] <= y0 + RIGA[1] * lungo
             and _copre(r, x0, x1, COPRE)]
    if len(righe) != 1:
        return None
    riga = righe[0][0]
    # i fianchi dello sportello, dentro il coperchio
    fianchi = []
    for c, verso in ((x0, +1), (x1, -1)):
        f = [r for r in V if 0 < (r[0] - c) * verso <= FIANCO_SPORTELLO
             and r[2] - r[1] >= COPRE_SPORTELLO * lungo
             and r[1] < riga < r[2]]
        if not f:
            return None
        fianchi.append(min(f, key=lambda r: abs(r[0] - c))[0])
    # il fronte: la linguetta sconfina nella testata sud, e il retro e' a nord
    if not _linguetta(linee, x0, x1, y1, sud[0]):
        return None
    if _linguetta(linee, x0, x1, nord[0], y0):
        return None
    s = Sportello(coperchio=(x0, y0, x1, y1),
                  bordi={"ovest": ovest[0], "est": est, "nord": nord[0],
                         "sud": sud[0]},
                  fondo=fondo, lato_fondo=lato_fondo, riga=riga,
                  fianchi=tuple(fianchi))
    alto = s.alto
    for nome, h in sorted(s.pareti.items()):
        if abs(h - alto) > PARETE_DIVERSA:
            s.warnings.append(
                "la parete %s sul foglio e' %.1f mm, la scatola e' alta %.1f "
                "(la mediana delle quattro): la si stende su quell'altezza"
                % (nome, h, alto))
    return s


def riconosci_sulla_tavola(pdf):
    """`(pdf, dieline estratta, Sportello o None, giro, avviso)`.

    Il retro deve stare in alto sul foglio: si prova il foglio com'e', e
    girato di un quarto, di mezzo giro e di tre quarti.
    """
    from . import artwork, dieline
    for giro in (0, 90, 180, 270):
        g = artwork.pagina_girata(pdf, giro) if giro else pdf
        if giro and g == pdf:
            break
        d = dieline.extract(g)
        if d.bbox is None:
            continue
        s = riconosci(d, tratti(g, d.bbox))
        if s is not None:
            return g, d, s, giro, (
                None if not giro else
                "foglio girato di %d gradi: sulla tavola il retro non stava in "
                "alto" % giro)
    return pdf, None, None, 0, None


def dichiara(s):
    W, H, L = s.dims_mm
    return ["Display a scatola con la plancia nel coperchio: %.1f x %.1f mm, "
            "alta %.1f mm" % (W, L, H),
            "plancia: lo sportello perforato del coperchio, alzato sulla "
            "cerniera del retro e ripiegato a meta' sulla riga: alta %.1f mm "
            "sopra la scatola, la meta' davanti verso chi guarda" % s.mezzo_mm,
            "fondo oltre il fianco %s" % s.lato_fondo] + list(s.warnings)


# --------------------------------------------------------------------------- #
# i pezzi

def pezzi(pdf, s, d, px_mm=4.0, page_no=0):
    """Le maschere dei pezzi, come `plancia.pezzi`: si disegnano i tratti, e
    ogni zona chiusa e' cartone, tranne il foglio attorno e i fori. Poi:

    - le pareti e il fondo sono il cartone nei loro riquadri della griglia;
    - nel coperchio, la CORNICE sono le zone che toccano un angolo, e il
      resto fra i fianchi dello sportello e' lo sportello: la parte dietro
      sopra la riga, la parte davanti sotto;
    - nella testata del fronte, la zona piu' grande e' la parete, e quelle
      attaccate al coperchio sono la linguetta, che va con la parte davanti.

    Le alette, le falde incollate e le linguette di chiusura stanno dentro
    la scatola chiusa e da fuori non si vedono: non si stendono.
    """
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy.ndimage import label

    scala = px_mm * PT2MM          # pixel per punto
    bx0, by0, bx1, by1 = d.bbox
    ox, oy = bx0 - MARGINE, by0 - MARGINE
    W = int(math.ceil((bx1 - bx0 + 2 * MARGINE) * scala))
    H = int(math.ceil((by1 - by0 + 2 * MARGINE) * scala))
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for linea in tratti(pdf, d.bbox, page_no):
        dr.line([((x - ox) * scala, (y - oy) * scala) for x, y in linea],
                fill=255, width=TRATTO_PX)
    tratto = np.asarray(img) > 0
    lab, n = label(~tratto)
    zone = _al_piu_vicino(tratto, lab)
    bordo = set(np.unique(np.concatenate([zone[0], zone[-1], zone[:, 0],
                                          zone[:, -1]])).tolist())
    quante = np.bincount(zone.ravel(), minlength=n + 1)
    minima = ZONA_MINIMA * px_mm * px_mm
    P = lambda x: (x - ox) * scala
    Q = lambda y: (y - oy) * scala

    x0, y0, x1, y1 = s.coperchio
    b = s.bordi
    fa, fb = s.fondo
    sagoma = ~np.isin(zone, list(bordo))
    # i fori e gli intagli piccoli non sono cartone
    sagoma &= quante[zone] >= minima

    def rett(a, c, e, f):
        """Il cartone nel riquadro: i pezzi del foglio stanno fra le righe
        della griglia. Non a zone intere: le cordonature si fermano a mezzo
        millimetro dagli angoli, e da li' il fianco, il fondo e le sue falde
        diventano una zona sola."""
        m = np.zeros((H, W), bool)
        m[max(int(round(Q(min(c, f)))), 0):max(int(round(Q(max(c, f)))), 0),
          max(int(round(P(min(a, e)))), 0):max(int(round(P(max(a, e)))), 0)] = True
        return m & sagoma

    m = {"coperchio": rett(x0, y0, x1, y1), "nord": rett(x0, b["nord"], x1, y0),
         "sud": rett(x0, y1, x1, b["sud"]), "ovest": rett(b["ovest"], y0, x0, y1),
         "est": rett(x1, y0, b["est"], y1), "fondo": rett(fa, y0, fb, y1)}
    # Lo sportello: le zone del coperchio che non toccano un angolo, fra i suoi
    # fianchi; diviso dalla riga in parte dietro e parte davanti. Fianchi e
    # riga si prendono dalla griglia, non dalle zone: la striscia fra il
    # fianco del coperchio e quello dello sportello, larga un millimetro e
    # mezzo, si attacca alle zone dello sportello dove i tratti non si
    # chiudono, e la plancia si portava dietro un filo della cornice.
    angoli = [(x0 + 1.5 * MM, y0 + 1.5 * MM), (x1 - 1.5 * MM, y0 + 1.5 * MM),
              (x0 + 1.5 * MM, y1 - 1.5 * MM), (x1 - 1.5 * MM, y1 - 1.5 * MM)]
    cornice = {int(zone[int(Q(y)), int(P(x))]) for x, y in angoli}
    sp = m["coperchio"] & ~np.isin(zone, list(cornice))
    sp[:, :max(int(round(P(s.fianchi[0]))), 0)] = False
    sp[:, int(round(P(s.fianchi[1]))):] = False
    r = int(round(Q(s.riga)))
    m["plancia dietro"] = sp.copy()
    m["plancia dietro"][r:] = False
    m["plancia davanti"] = sp.copy()
    m["plancia davanti"][:r] = False
    m["coperchio"] &= ~sp
    # La linguetta: nella testata del fronte, le zone attaccate al coperchio
    # che non sono la parete, cioe' la zona piu' grande.
    zs, conti = np.unique(zone[m["sud"]], return_counts=True)
    if len(zs):
        parete = zs[int(np.argmax(conti))]
        riga_cop = int(round(Q(y1)))
        fascia = zone[max(riga_cop - TRATTO_PX, 0):riga_cop + TRATTO_PX + 1]
        for z in zs:
            if z != parete and (fascia == z).any():
                lin = m["sud"] & (zone == z)
                m["plancia davanti"] |= lin
                m["sud"] &= ~lin
    vuoti = [k for k, v in m.items() if not v.any()]
    if vuoti:
        raise ValueError("display con la plancia nel coperchio: sul foglio "
                         "non si trovano %s" % ", ".join(vuoti))
    maschere = {k: m[k] for k in ("coperchio", "nord", "sud", "ovest", "est",
                                  "fondo", "plancia dietro", "plancia davanti")}
    righe = {"coperchio": (P(x0), P(x1), Q(y0), Q(y1)), "riga": Q(s.riga),
             "bordi": {k: (P(v) if k in ("ovest", "est") else Q(v))
                       for k, v in b.items()},
             "fondo": (P(fa), P(fb))}
    return Pezzi(maschere=maschere, righe=righe, origine=(ox, oy), scala=scala,
                 lato=(W, H))


# --------------------------------------------------------------------------- #
# la maglia

def mesh(s, pz, px_mm, spessore=SPESSORE, alt_texture=None, parti=None):
    """La maglia del display APERTO: vertici in mm, UV sullo steso, triangoli.

    Il fronte guarda +Z, la cima +Y, il fondo sta a Y = 0. Ogni pezzo gira
    rigido sulla sua piega; detto `a` quanto un punto dello sportello dista
    dalla cerniera del retro, e `A` la parte dietro fino alla riga:

      - la cornice del coperchio sta in cima, a Y = alto, stampa in su;
      - le pareti scendono dai lati del coperchio, ognuna stesa sull'altezza
        della scatola; il fondo sta a Y = 0, girato sotto dal fianco del suo
        lato;
      - la parte DIETRO sta in piedi sul retro, nel piano del retro, stampa
        verso dietro: Y = alto + a;
      - la parte DAVANTI e' ripiegata sulla riga verso chi guarda, due
        spessori davanti: Y = alto + A - (a - A). La linguetta, che sul foglio
        sta oltre il coperchio, finisce dentro la scatola, dietro il prodotto.
    """
    import numpy as np

    mk = pz.maschere
    Hp, Wp = mk["coperchio"].shape
    maglia = Maglia(Wp, Hp, spessore, alt_texture, parti)
    ox, oy = pz.origine
    sc = pz.scala
    x0, y0, x1, y1 = s.coperchio
    b = s.bordi
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    W, alto, L = s.dims_mm
    A = s.mezzo_mm
    fa, fb = s.fondo

    def foglio(X, Y):
        return ox + np.asarray(X, float) / sc, oy + np.asarray(Y, float) / sc

    def mm(v):
        return np.asarray(v, float) * PT2MM

    def coperchio(X, Y):
        u, v = foglio(X, Y)
        return (mm(u - cx), alto + 0.0 * u, mm(v - cy))

    def nord(X, Y):
        u, v = foglio(X, Y)
        return (mm(u - cx), alto - (y0 - v) / (y0 - b["nord"]) * alto,
                -L / 2.0 + 0.0 * u)

    def sud(X, Y):
        u, v = foglio(X, Y)
        return (mm(u - cx), alto - (v - y1) / (b["sud"] - y1) * alto,
                L / 2.0 + 0.0 * u)

    def ovest(X, Y):
        u, v = foglio(X, Y)
        return (-W / 2.0 + 0.0 * u, alto - (x0 - u) / (x0 - b["ovest"]) * alto,
                mm(v - cy))

    def est(X, Y):
        u, v = foglio(X, Y)
        return (W / 2.0 + 0.0 * u, alto - (u - x1) / (b["est"] - x1) * alto,
                mm(v - cy))

    def fondo(X, Y):
        u, v = foglio(X, Y)
        t = (u - fa) / (fb - fa)
        lato = 1.0 if s.lato_fondo == "est" else -1.0
        return (lato * W / 2.0 * (1.0 - 2.0 * t), 0.0 * u, mm(v - cy))

    def dietro(X, Y):
        u, v = foglio(X, Y)
        return (mm(u - cx), alto + mm(v - y0), -L / 2.0 + 0.0 * u)

    def davanti(X, Y):
        u, v = foglio(X, Y)
        return (mm(u - cx), alto + A - mm(v - s.riga),
                -L / 2.0 + 2.2 * spessore + 0.0 * u)

    def tupla(f):
        return lambda X, Y: tuple(float(c) for c in f(X, Y))

    r = pz.righe
    cX0, cX1, cY0, cY1 = r["coperchio"]
    pezzo = maglia.pezzo
    pezzo(mk["coperchio"], "righe", tupla(coperchio), (0, -1, 0),
          [("X", cX0), ("X", cX1), ("Y", cY0), ("Y", cY1)], "coperchio")
    pezzo(mk["nord"], "righe", tupla(nord), (0, 0, 1), [("Y", cY0)], "nord")
    pezzo(mk["sud"], "righe", tupla(sud), (0, 0, -1), [("Y", cY1)], "sud")
    pezzo(mk["ovest"], "colonne", tupla(ovest), (1, 0, 0), [("X", cX0)], "ovest")
    pezzo(mk["est"], "colonne", tupla(est), (-1, 0, 0),
          [("X", cX1), ("X", r["fondo"][0])], "est")
    pezzo(mk["fondo"], "colonne", tupla(fondo), (0, 1, 0),
          [("X", r["fondo"][0])], "fondo")
    # la plancia per ultima: i suoi triangoli in fondo, un nodo a se'
    pezzo(mk["plancia dietro"], "righe", tupla(dietro), (0, 0, 1),
          [("Y", cY0), ("Y", r["riga"])], "plancia dietro")
    pezzo(mk["plancia davanti"], "righe", tupla(davanti), (0, 0, -1),
          [("Y", r["riga"])], "plancia davanti")
    return maglia.array()
