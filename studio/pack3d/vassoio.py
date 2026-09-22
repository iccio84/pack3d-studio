"""
Il vassoio espositore: un fondo e quattro pareti che si alzano.

Non e' un astuccio e non e' un flowpack, ed e' la terza famiglia. Il display
del Milch-Schnitte Raspberry cadeva nel ramo flowpack e usciva "saldature di
testa non riconosciute": un messaggio che non dice niente a chi ha in mano un
vassoio.

La forma e' la piu' semplice di tutte: un rettangolo centrale - il **fondo** -
con una parete attaccata a ciascuno dei suoi quattro lati, e le alette agli
angoli che tengono su le pareti. Le quattro pareti NON sono alte uguali: su un
display da scaffale i fianchi lunghi sono alti perche' reggono la pila, e la
parete davanti e' bassa perche' il prodotto si deve vedere. Sul Milch-Schnitte
sono 98,6 e 98,5 contro 40,0 e 40,5.

Quello che lo distingue si legge nella griglia della fustella, e non e'
un'euristica: **cinque colonne e tre fasce**, con la colonna e la fascia di
mezzo che coincidono sul fondo. Le due colonne sottili fra fondo e pareti sono
la cordonatura, due millimetri di spessore del cartoncino.

    colonne (mm)   98,6 | 2,0 | 145,5 | 2,0 | 98,5
    fasce   (mm)   40,0 | 385,9 | 40,5

Le alette angolari non vengono costruite: da fuori non si vedono, perche' le
copre la parete che tengono. Il modello e' fondo piu' quattro pareti, con lo
spessore del cartoncino che ci mette `folding.guscio`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .dieline import PT2MM

# la cordonatura fra fondo e parete: due tratti vicini, non un pannello
CORDONATURA_MAX = 6.0
# una parete sotto questa altezza non e' una parete, e' un'aletta
PARETE_MINIMA = 8.0


@dataclass
class Vassoio:
    """Un vassoio, in millimetri. Le pareti girano da nord in senso orario."""
    fondo_w: float
    fondo_h: float
    pareti: dict          # {"nord": alt, "est": alt, "sud": alt, "ovest": alt}
    riquadri: dict        # {nome: (x0, y0, x1, y1) in punti PDF}
    warnings: list = field(default_factory=list)

    @property
    def dims_mm(self):
        """Ingombro del vassoio montato: larghezza, profondita', altezza."""
        return (self.fondo_w, self.fondo_h, max(self.pareti.values()))


def _fasce(valori):
    """Da una lista di coordinate alle luci fra l'una e l'altra, in mm."""
    return [(b - a) * PT2MM for a, b in zip(valori, valori[1:])]


def riconosci(d):
    """`Vassoio` dalla griglia della fustella, o `None` se non lo e'.

    `d` e' quello che restituisce `dieline.extract`. Si guarda la griglia e
    basta: cinque colonne con la seconda e la quarta sottili (cordonature),
    tre fasce, e la colonna di mezzo larga quanto il fondo. Niente di
    stimato - o la griglia ha questa forma o non ce l'ha.
    """
    xs = sorted({round(v, 2) for v in getattr(d, "xs", [])})
    ys = sorted({round(v, 2) for v in getattr(d, "ys", [])})
    if len(xs) != 6 or len(ys) != 4:
        return None
    col = _fasce(xs)
    ban = _fasce(ys)
    # [ovest | cordone | fondo | cordone | est]
    if not (col[1] <= CORDONATURA_MAX and col[3] <= CORDONATURA_MAX):
        return None
    ovest, fondo_w, est = col[0], col[2], col[4]
    nord, fondo_h, sud = ban[0], ban[1], ban[2]
    if min(ovest, est, nord, sud) < PARETE_MINIMA:
        return None
    if fondo_w <= max(ovest, est) * 0.5 or fondo_h <= max(nord, sud) * 0.5:
        return None

    riquadri = {
        "fondo": (xs[2], ys[1], xs[3], ys[2]),
        "ovest": (xs[0], ys[1], xs[1], ys[2]),
        "est":   (xs[4], ys[1], xs[5], ys[2]),
        "nord":  (xs[2], ys[0], xs[3], ys[1]),
        "sud":   (xs[2], ys[2], xs[3], ys[3]),
    }
    v = Vassoio(fondo_w=round(fondo_w, 1), fondo_h=round(fondo_h, 1),
                pareti={"nord": round(nord, 1), "est": round(est, 1),
                        "sud": round(sud, 1), "ovest": round(ovest, 1)},
                riquadri=riquadri)
    lunghe = sorted(v.pareti.values())
    if lunghe[-1] - lunghe[0] > 1.0:
        v.warnings.append(
            "pareti di altezze diverse (%s mm): normale su un display, dove i "
            "fianchi reggono la pila e il davanti lascia vedere il prodotto"
            % ", ".join("%.1f" % a for a in lunghe))
    return v


def _strisce(maschera, verso):
    """Il pezzo come striscia: per ogni riga (o colonna) i due estremi pieni.

    I pezzi di un vassoio sono tutti **convessi in una direzione** - ogni riga
    di un fianco e' un tratto solo, dalla cordonatura al taglio - quindi non
    serve inseguire un contorno: bastano i due bordi, e fra loro la maglia e'
    una striscia di triangoli. Robusto e senza librerie.
    """
    import numpy as np

    m = maschera if verso == "righe" else maschera.T
    righe = []
    for i in range(m.shape[0]):
        x = np.flatnonzero(m[i])
        if x.size:
            righe.append((i, int(x[0]), int(x[-1]) + 1))
    return righe


def mesh(v: Vassoio, sagoma, px_mm, creste):
    """La maglia del vassoio piegato: vertici, UV sullo steso, triangoli.

    I NOMI, come li chiama chi il display ce l'ha in mano: **base** al
    centro, **fronte** e **retro** sulle due testate, **lato SX** e
    **lato DX** sulle due colonne, e quattro **alette** agli angoli.

    LE ALETTE SONO DEI LATERALI, non delle testate. Piegano di 90 gradi
    rispetto al laterale, e quando il laterale a sua volta piega di 90
    rispetto alla base si ritrovano in posizione frontale e posteriore: sono
    lo strato interno del fronte e del retro, che poi ci si chiudono sopra.
    E' il modo in cui un vassoio sta in piedi, e sbagliarlo vuol dire
    costruire quattro pareti che non si tengono.

    Una texture sola - lo steso intero - e le UV prese dalla posizione nel
    piano: la piega sposta i vertici e la grafica se li porta dietro, quindi
    non c'e' nessun ritaglio da ruotare.

    `sagoma` e' la maschera della cartotecnica, `px_mm` i pixel per
    millimetro, `creste` le due cordonature verticali e le due orizzontali,
    in pixel della maschera.
    """
    import numpy as np

    H, W = sagoma.shape
    cxL, cxR, cyT, cyB = creste
    Xc, Yc = (cxL + cxR) / 2.0, (cyT + cyB) / 2.0
    # la z NON si specchia: sullo steso visto da fuori, la colonna di
    # sinistra deve restare a sinistra anche guardando il vassoio dal
    # fronte. Girando il segno il modello esce speculare, e si vede solo
    # confrontandolo con il pack vero.
    mx = lambda X: (Xc - X) / px_mm
    mz = lambda Y: (Y - Yc) / px_mm
    xL, xR, zT, zB = mx(cxL), mx(cxR), mz(cyT), mz(cyB)
    # le alette stanno DENTRO fronte e retro: mezzo millimetro piu' in
    # dentro, se no le due superfici combattono per lo stesso pixel
    DENTRO = 0.5

    V, UV, T = [], [], []

    def striscia(masc, verso, punto):
        righe = _strisce(masc, verso)
        if len(righe) < 2:
            return
        prima = None
        for i, a, b in righe:
            for X, Y in (((a, i), (b, i)) if verso == "righe" else ((i, a), (i, b))):
                V.append(punto(X, Y))
                UV.append((X / float(W), Y / float(H)))
            if prima is not None:
                # l'avvolgimento e' orario: il rasterizzatore e l'export
                # prendono per diritta quella faccia, e con l'altro verso il
                # marchio si legge specchiato - che e' come si vede da fuori
                # il rovescio di un triangolo
                k = len(V) - 4
                T.append((k, k + 3, k + 1))
                T.append((k, k + 2, k + 3))
            prima = i

    def cella(y0, y1, x0, x1):
        m = np.zeros((H, W), bool)
        m[y0:y1, x0:x1] = True
        return m & sagoma

    # base: resta distesa
    striscia(cella(cyT, cyB, cxL, cxR), "righe",
             lambda X, Y: (mx(X), 0.0, mz(Y)))
    # laterali: quello che sta oltre la cordonatura verticale diventa altezza
    striscia(cella(cyT, cyB, 0, cxL), "righe",
             lambda X, Y: (xL, (cxL - X) / px_mm, mz(Y)))
    striscia(cella(cyT, cyB, cxR, W), "righe",
             lambda X, Y: (xR, (X - cxR) / px_mm, mz(Y)))

    # retro e fronte: oltre la cordonatura orizzontale
    striscia(cella(0, cyT, cxL, cxR), "colonne",
             lambda X, Y: (mx(X), (cyT - Y) / px_mm, zT))
    striscia(cella(cyB, H, cxL, cxR), "colonne",
             lambda X, Y: (mx(X), (Y - cyB) / px_mm, zB))
    # le quattro alette: piegate sul laterale, finiscono nel piano del retro
    # (in alto) e del fronte (in basso), un filo piu' dentro
    striscia(cella(0, cyT, 0, cxL), "righe",
             lambda X, Y: (xL - (cyT - Y) / px_mm, (cxL - X) / px_mm, zT + DENTRO))
    striscia(cella(0, cyT, cxR, W), "righe",
             lambda X, Y: (xR + (cyT - Y) / px_mm, (X - cxR) / px_mm, zT + DENTRO))
    striscia(cella(cyB, H, 0, cxL), "righe",
             lambda X, Y: (xL - (Y - cyB) / px_mm, (cxL - X) / px_mm, zB - DENTRO))
    striscia(cella(cyB, H, cxR, W), "righe",
             lambda X, Y: (xR + (Y - cyB) / px_mm, (X - cxR) / px_mm, zB - DENTRO))

    return (np.array(V, float), np.array(UV, float), np.array(T, np.uint32))


def sagoma_e_creste(pdf, d, px_mm=4.0, page_no=0):
    """`(sagoma, creste, resa)` per costruire il vassoio.

    La sagoma della cartotecnica **non viene dal tracciato**. La penna della
    fustella ha interruzioni - sul display Milch-Schnitte sono da 3 mm, e
    riempiendola si prende solo la colonna centrale, perche' le cordonature
    chiudono quella cella e il contorno esterno no. Viene invece
    dall'**impronta di stampa**: su questi display la stampa arriva al
    taglio, e allora l'impronta E' la cartotecnica. Misurata sul Milch-
    Schnitte: 346,5 x 466,5 mm, cioe' esattamente le quote del disegno
    tecnico 34150.
    """
    import numpy as np
    from scipy.ndimage import binary_fill_holes, label

    from .dieline import render_page

    scala = px_mm * 25.4 / 72.0
    resa = render_page(pdf, page_no, scala).convert("RGB")
    a = np.asarray(resa)
    lab, quanti = label(a.astype(np.int16).max(2) < 246)
    if quanti == 0:
        return None, None, resa
    dim = np.bincount(lab.ravel())
    dim[0] = 0
    sagoma = binary_fill_holes(lab == int(np.argmax(dim)))
    gx = sorted({round(t, 1) for t in d.xs})
    gy = sorted({round(t, 1) for t in d.ys})
    creste = (int(round((gx[1] + gx[2]) / 2 * scala)),
              int(round((gx[3] + gx[4]) / 2 * scala)),
              int(round(gy[1] * scala)), int(round(gy[2] * scala)))
    return sagoma, creste, resa


def facce(v: Vassoio, textures: dict):
    """Fondo e quattro pareti come quad 3D, pronti per `folding.guscio`.

    Stessa convenzione degli astucci - **y in alto**, vedi `folding.corners` -
    cosi' rasterizzatore, guscio ed export non vedono differenza fra un
    vassoio e un astuccio. Il fondo sta a y=0 e le pareti salgono.

    **La piega gira il ritaglio, e la texture va girata con lei.** Il bordo
    del ritaglio attaccato al fondo finisce sempre in BASSO sulla parete
    alzata: per la parete a nord quel bordo e' gia' quello di sotto e non
    serve niente, per quella a sud e' quello di sopra e il ritaglio va
    ribaltato di 180 gradi, per le due laterali e' un fianco e il ritaglio
    ruota di 90. Non e' una correzione a occhio: e' la stessa rotazione che fa
    il cartoncino quando lo pieghi.
    """
    W, P = v.fondo_w, v.fondo_h
    hx, hz = W / 2.0, P / 2.0
    UV = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    a = v.pareti
    out = []

    def aggiungi(nome, quad, giro=None):
        t = textures.get(nome)
        if t is None:
            return
        if giro is not None:
            t = t.transpose(giro)
        out.append({"name": nome, "quad": quad, "uv": list(UV), "tex": t})

    from PIL import Image as _I

    # Fondo: visto da sopra, la riga alta del ritaglio confina con NORD.
    aggiungi("fondo", [(-hx, 0.0, -hz), (+hx, 0.0, -hz),
                       (+hx, 0.0, +hz), (-hx, 0.0, +hz)])
    # Nord, sul retro: il ritaglio e' gia' nel verso giusto.
    aggiungi("nord", [(+hx, a["nord"], -hz), (-hx, a["nord"], -hz),
                      (-hx, 0.0, -hz), (+hx, 0.0, -hz)])
    # Sud, davanti: il bordo attaccato al fondo e' quello alto, quindi 180.
    aggiungi("sud", [(-hx, a["sud"], +hz), (+hx, a["sud"], +hz),
                     (+hx, 0.0, +hz), (-hx, 0.0, +hz)], _I.ROTATE_180)
    # Est e ovest: il bordo attaccato al fondo e' un fianco, quindi 90.
    aggiungi("est", [(+hx, a["est"], +hz), (+hx, a["est"], -hz),
                     (+hx, 0.0, -hz), (+hx, 0.0, +hz)], _I.ROTATE_90)
    aggiungi("ovest", [(-hx, a["ovest"], -hz), (-hx, a["ovest"], +hz),
                       (-hx, 0.0, +hz), (-hx, 0.0, -hz)], _I.ROTATE_270)
    return out
