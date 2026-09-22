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
    """Il pezzo riga per riga, coi TRATTI pieni di ciascuna.

    Non basta prendere il primo e l'ultimo pixel pieno: su un fianco del
    display Milch-Schnitte, all'altezza dell'angolo, la riga ha **due**
    tratti - il pezzo rosa dell'aletta e il rosso della parete - separati da
    bianco che non e' cartoncino, e' foglio. Prendendo gli estremi la
    striscia faceva ponte e ci stendeva sopra il bianco: e' il difetto che si
    vedeva come "bianco sulla texture dei laterali".

    Torna `[(riga, [(a, b), ...]), ...]`.
    """
    import numpy as np

    m = maschera if verso == "righe" else maschera.T
    fuori = []
    for i in range(m.shape[0]):
        x = np.flatnonzero(m[i])
        if not x.size:
            continue
        tagli = np.flatnonzero(np.diff(x) > 1)
        inizio = np.concatenate(([0], tagli + 1))
        fine = np.concatenate((tagli, [len(x) - 1]))
        fuori.append((i, [(int(x[a]), int(x[b]) + 1) for a, b in zip(inizio, fine)]))
    return fuori


# Lo spessore del cartoncino di un display: piu' di un astuccio, perche' e'
# solid board e deve reggere la pila. Misurato sulle cordonature doppie del
# Milch-Schnitte, che sono 2,0 mm fra le due righe.
SPESSORE = 1.0
INTERNO = (238, 235, 229)
TAGLIO = (212, 203, 188)
# le due righe di colore piatto che si attaccano in fondo allo steso: servono
# a dare interno e taglio con UNA texture sola, senza un secondo materiale
CODA = 6


def con_coda(steso):
    """Lo steso con in fondo due strisce: colore dell'interno e del taglio."""
    import numpy as np
    from PIL import Image

    a = np.asarray(steso.convert("RGB"))
    h, w, _ = a.shape
    coda = np.zeros((CODA, w, 3), np.uint8)
    coda[:CODA // 2] = INTERNO
    coda[CODA // 2:] = TAGLIO
    return Image.fromarray(np.concatenate([a, coda], 0))


def mesh(v: Vassoio, sagoma, px_mm, creste, spessore=SPESSORE):
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

    Una texture sola - lo steso con in fondo due righe di colore piatto, vedi
    `con_coda` - e le UV prese dalla posizione nel piano: la piega sposta i
    vertici e la grafica se li porta dietro, quindi non c'e' nessun ritaglio
    da ruotare. Le facce interne e le coste pescano dalle due righe in fondo.

    Con `spessore` ogni pezzo diventa un guscio: faccia esterna, faccia
    interna spostata lungo la normale entrante e avvolta al contrario, e la
    costa sui bordi che confinano col taglio - non su quelli che confinano
    con una cordonatura, dove il cartoncino continua.
    """
    import numpy as np

    H, W = sagoma.shape
    cxL, cxR, cyT, cyB = creste
    Xc, Yc = (cxL + cxR) / 2.0, (cyT + cyB) / 2.0
    # UNO specchio, e uno solo. Piegando lo steso cosi' com'e' la stampa
    # finisce DENTRO - il marchio si legge mirror, cioe' attraverso il
    # cartone - perche' la faccia stampata guardava in su e piegando in su
    # va a guardare l'interno. Ci vuole uno specchio per rimetterla fuori, e
    # uno solo: con due (x e z) e' una rotazione, e torna mirror.
    #
    # Si specchia la **z**, non la x. Le due scelte leggono uguale, ma
    # cambiano quale banda va davanti: sullo steso quella di sopra legge
    # dritta e quella di sotto e' ruotata di 180, e chi monta il display
    # chiama FRONTE quella di sotto.
    mx = lambda X: (X - Xc) / px_mm
    mz = lambda Y: (Yc - Y) / px_mm
    xL, xR, zT, zB = mx(cxL), mx(cxR), mz(cyT), mz(cyB)
    DENTRO = 0.5

    Ht = H + CODA                       # la texture ha la coda in fondo
    vI = (H + CODA * 0.25) / Ht         # riga dell'interno
    vT = (H + CODA * 0.75) / Ht         # riga del taglio

    V, UV, T = [], [], []

    def quad(p0, p1, p2, p3, uv):
        k = len(V)
        V.extend([p0, p1, p2, p3])
        UV.extend([uv] * 4)
        T.append((k, k + 2, k + 1))
        T.append((k, k + 3, k + 2))

    def pezzo(masc, verso, punto, dentro, su_cordone):
        """Un pezzo col suo spessore: esterna, interna e coste.

        Due righe consecutive si cuciono solo se hanno lo stesso numero di
        tratti: dove il conto cambia - li' la sagoma si apre o si chiude -
        resta una riga scucita alta un pixel, cioe' un quarto di millimetro,
        e cucirla a indovinare farebbe di nuovo il ponte sul bianco.
        """
        righe = _strisce(masc, verso)
        if len(righe) < 2:
            return
        d = np.array(dentro, float) * spessore
        prec = None
        for i, tratti in righe:
            corr = []
            for a, b in tratti:
                XY = ((a, i), (b, i)) if verso == "righe" else ((i, a), (i, b))
                fuori = [np.array(punto(X, Y), float) for X, Y in XY]
                dentro_p = [q + d for q in fuori]
                k = len(V)
                for (X, Y), q in zip(XY, fuori):
                    V.append(tuple(q)); UV.append((X / float(W), Y / float(Ht)))
                for q in dentro_p:
                    V.append(tuple(q)); UV.append((0.5, vI))
                corr.append((k, fuori, dentro_p, XY))
            if prec is not None and len(prec) == len(corr):
                for (pk, pf, pd, pXY), (k, fuori, dentro_p, XY) in zip(prec, corr):
                    # faccia esterna
                    T.append((pk, k, pk + 1)); T.append((k, k + 1, pk + 1))
                    # faccia interna, avvolta al contrario
                    T.append((pk + 2, pk + 3, k + 2)); T.append((k + 2, pk + 3, k + 3))
                    # coste, solo dove il bordo e' taglio e non cordonatura
                    for lato in (0, 1):
                        if su_cordone(*pXY[lato]) and su_cordone(*XY[lato]):
                            continue
                        if lato == 0:
                            quad(tuple(pf[0]), tuple(fuori[0]),
                                 tuple(dentro_p[0]), tuple(pd[0]), (0.5, vT))
                        else:
                            quad(tuple(fuori[1]), tuple(pf[1]),
                                 tuple(pd[1]), tuple(dentro_p[1]), (0.5, vT))
            prec = corr

    def cella(y0, y1, x0, x1):
        m = np.zeros((H, W), bool)
        m[y0:y1, x0:x1] = True
        return m & sagoma

    TOL = 3
    vicino = lambda a, b: abs(a - b) <= TOL

    # base: il bordo e' tutto cordonatura, niente coste
    pezzo(cella(cyT, cyB, cxL, cxR), "righe",
          lambda X, Y: (mx(X), 0.0, mz(Y)), (0, 1, 0),
          lambda X, Y: True)
    # laterali: la cordonatura e' quella verticale
    pezzo(cella(cyT, cyB, 0, cxL), "righe",
          lambda X, Y: (xL, (cxL - X) / px_mm, mz(Y)), (1, 0, 0),
          lambda X, Y: vicino(X, cxL))
    pezzo(cella(cyT, cyB, cxR, W), "righe",
          lambda X, Y: (xR, (X - cxR) / px_mm, mz(Y)), (-1, 0, 0),
          lambda X, Y: vicino(X, cxR))
    # retro e fronte: la cordonatura e' quella orizzontale
    pezzo(cella(0, cyT, cxL, cxR), "colonne",
          lambda X, Y: (mx(X), (cyT - Y) / px_mm, zT), (0, 0, -1),
          lambda X, Y: vicino(Y, cyT))
    pezzo(cella(cyB, H, cxL, cxR), "colonne",
          lambda X, Y: (mx(X), (Y - cyB) / px_mm, zB), (0, 0, 1),
          lambda X, Y: vicino(Y, cyB))
    # le alette: piegate sul laterale, finiscono nel piano di retro e fronte
    pezzo(cella(0, cyT, 0, cxL), "righe",
          lambda X, Y: (xL + (cyT - Y) / px_mm, (cxL - X) / px_mm, zT - DENTRO),
          (0, 0, -1), lambda X, Y: vicino(Y, cyT))
    pezzo(cella(0, cyT, cxR, W), "righe",
          lambda X, Y: (xR - (cyT - Y) / px_mm, (X - cxR) / px_mm, zT - DENTRO),
          (0, 0, -1), lambda X, Y: vicino(Y, cyT))
    pezzo(cella(cyB, H, 0, cxL), "righe",
          lambda X, Y: (xL + (Y - cyB) / px_mm, (cxL - X) / px_mm, zB + DENTRO),
          (0, 0, 1), lambda X, Y: vicino(Y, cyB))
    pezzo(cella(cyB, H, cxR, W), "righe",
          lambda X, Y: (xR - (Y - cyB) / px_mm, (X - cxR) / px_mm, zB + DENTRO),
          (0, 0, 1), lambda X, Y: vicino(Y, cyB))

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
