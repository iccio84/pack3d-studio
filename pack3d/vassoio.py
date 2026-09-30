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

Le alette angolari invece si costruiscono, e sono DEI LATERALI: piegano di 90
gradi rispetto al fianco, e quando il fianco a sua volta piega di 90 rispetto
alla base si ritrovano in posizione frontale e posteriore, a fare lo strato
interno del fronte e del retro. Su questo display sporgono sopra la parete
davanti, che e' bassa, quindi si vedono eccome.

Il contorno non e' un rettangolo: si sagoma sull'impronta della cartotecnica,
vedi `_foglio` e `sagoma_e_creste`. Il modello e' una maglia sola con una
texture sola - lo steso - e lo spessore del cartoncino gliela mette `mesh`.
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


def riconosci_sulla_tavola(pdf):
    """`(pdf, dieline estratta, Vassoio o None, giro, avviso)`.

    `riconosci` legge la griglia in un verso solo - cinque colonne e tre
    fasce - e il KMS Display girato di 90 gradi sulla tavola ne ha tre e
    cinque: non si costruiva. Se la griglia nel verso del foglio non torna si
    prova il foglio girato di un quarto (`artwork.pagina_girata`), prima di
    dire che non e' un vassoio. Mezzo giro non serve: il vassoio si legge
    uguale, e quale testata va davanti lo decide `testata_davanti` dalle
    altezze.
    """
    from . import artwork, dieline
    d = dieline.extract(pdf)
    v = riconosci(d)
    if v is not None:
        return pdf, d, v, 0, None
    for giro in (90, 270):
        girato = artwork.pagina_girata(pdf, giro)
        if girato == pdf:
            break
        d2 = dieline.extract(girato)
        v2 = riconosci(d2)
        if v2 is not None:
            return girato, d2, v2, giro, (
                "foglio girato di %d gradi: sulla tavola la griglia del "
                "vassoio - cinque colonne e tre fasce - stava di traverso"
                % giro)
    return pdf, d, None, 0, None


def _fasce_comuni(m, i):
    """I tratti che le righe `i-1` e `i` hanno IN COMUNE, e i loro capi.

    Il cartoncino fra due righe vicine c'e' dove c'e' su tutte e due: la
    fascia di superficie che le unisce e' l'INTERSEZIONE, non l'una o
    l'altra. Presa cosi' non serve piu' che le due righe abbiano lo stesso
    numero di tratti, ed e' quello che conta: sul fronte del display la
    sagoma si apre - l'aletta si stacca dalla parete - il conto cambiava, e
    la vecchia regola "si cuce solo a conti pari" lasciava li' una colonna
    scucita larga un pixel. Un quarto di millimetro, che nel modello si
    vedeva come una **feritoia** in mezzo all'aletta del fronte.

    E non fa ponti: l'intersezione di due righe non copre mai il foglio che
    sta fra due tratti, perche' li' non c'e' cartoncino su nessuna delle due.

    Per ogni tratto torna `(a, b, capo_a, capo_b)`, dove i capi dicono se il
    bordo e' un TAGLIO - fuori non c'e' cartoncino su nessuna delle due
    righe - oppure un taglio finto, cioe' un punto in cui la fascia finisce
    solo perche' l'altra riga e' piu' corta. Sul taglio finto la costa non va
    messa: sarebbe una riga di spessore in mezzo al pezzo.
    """
    import numpy as np

    su, giu = m[i - 1], m[i]
    comune = su & giu
    x = np.flatnonzero(comune)
    if not x.size:
        return []
    tagli = np.flatnonzero(np.diff(x) > 1)
    inizio = np.concatenate(([0], tagli + 1))
    fine = np.concatenate((tagli, [len(x) - 1]))
    larghezza = m.shape[1]
    out = []
    for s_, e_ in zip(inizio, fine):
        a, b = int(x[s_]), int(x[e_]) + 1
        capo_a = True if a == 0 else not (su[a - 1] or giu[a - 1])
        capo_b = True if b >= larghezza else not (su[b] or giu[b])
        out.append((a, b, capo_a, capo_b))
    return out


# Lo spessore del cartoncino di un display: piu' di un astuccio, perche' e'
# solid board e deve reggere la pila. Misurato sulle cordonature doppie del
# Milch-Schnitte, che sono 2,0 mm fra le due righe.
SPESSORE = 1.0
INTERNO = (238, 235, 229)
TAGLIO = (212, 203, 188)
# le due righe di colore piatto che si attaccano in fondo allo steso: servono
# a dare interno e taglio con UNA texture sola, senza un secondo materiale
CODA = 6


def testata_davanti(v: Vassoio):
    """Quale testata va davanti: la piu' bassa.

    Su un espositore il davanti e' basso perche' il prodotto si deve vedere,
    e il dietro, se e' piu' alto, regge il cartello. E' una misura del DT,
    non una scelta.

    Anche quando le due testate sono alte quasi uguali - sul Milch-Schnitte
    40,5 e 40,6 - decide la piu' bassa, e non la nord. Nord e sud sono il
    sopra e il sotto del FOGLIO: con la nord di serie, lo stesso steso girato
    di mezzo giro sulla tavola metteva davanti l'altra testata. Il decimo di
    millimetro non dice niente del progetto, ma sta nel disegno e non nella
    tavola, quindi da' lo stesso vassoio comunque sia messo il foglio. Solo a
    pari altezza resta la nord.
    """
    n, s = v.pareti["nord"], v.pareti["sud"]
    return "sud" if s < n else "nord"


def gira(V):
    """Mezzo giro attorno alla verticale: la testata sud passa davanti."""
    import numpy as np
    W = np.array(V, float, copy=True)
    W[:, 0] *= -1.0
    W[:, 2] *= -1.0
    return W


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


# quanto un lato puo' stare lontano da una cordonatura ed esserci sopra, in
# pixel della sagoma
PIEGA_TOL = 3


def _meno(A, B):
    """Gli intervalli di A che B non copre, `[(a, b)]`, su una riga di pixel."""
    def unione(I):
        out = []
        for a, b in sorted(I):
            if out and a <= out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out
    resta = []
    for a, b in unione(A):
        cur = a
        for c, e in unione(B):
            if e <= cur or c >= b:
                continue
            if c > cur:
                resta.append((cur, c))
            cur = max(cur, e)
        if cur < b:
            resta.append((cur, b))
    return resta


class Maglia:
    """La maglia che si sta stendendo: vertici, UV sullo steso e triangoli.

    Si riempie un pezzo alla volta con `pezzo`, ognuno col suo spessore. Sta
    fuori da `mesh` perche' la usa anche il display con plancia
    (`plancia.mesh`): ha pezzi in piu', ma li stende allo stesso modo, e due
    copie dello stesso codice prima o poi divergono.

    `W` e `H` sono le misure della sagoma, cioe' della griglia su cui stanno
    le maschere dei pezzi; `alt_texture` quella della texture con la coda.
    """

    def __init__(self, W, H, spessore=SPESSORE, alt_texture=None, parti=None):
        self.W, self.H = W, H
        self.spessore = spessore
        self.parti = parti
        # Le UV si misurano sulla TEXTURE, non sulla sagoma. La coda e' CODA
        # righe in fondo alla texture (vedi `con_coda`), e la sagoma ha
        # un'altezza tutta sua - 4 px/mm contro i 2,4 della texture sul
        # Milch-Schnitte. Prendendo `H + CODA` come altezza totale la riga
        # dell'interno cascava su quella del taglio, e tutto il dentro del
        # vassoio usciva del colore del taglio.
        ht = float(alt_texture) if alt_texture else float(H + CODA)
        self.q = (ht - CODA) / ht                # la frazione con la grafica
        self.vI = (ht - CODA * 0.75) / ht        # riga dell'interno
        self.vT = (ht - CODA * 0.25) / ht        # riga del taglio
        self.V, self.UV, self.T = [], [], []

    def quad(self, p0, p1, p2, p3, uv):
        V, T = self.V, self.T
        k = len(V)
        V.extend([p0, p1, p2, p3])
        self.UV.extend([uv] * 4)
        T.append((k, k + 2, k + 1))
        T.append((k, k + 3, k + 2))

    def faccia(self, A, B, C, D, uv, fuori):
        """Il quad A-B-C-D in giro, avvolto perche' guardi verso `fuori`.

        Il verso lo decide la geometria e non l'ordine dei vertici: glTF scarta
        le facce voltate, e una costa girata al contrario e' un buco.
        """
        import numpy as np
        n = np.cross(np.subtract(C, A), np.subtract(B, A))
        if float(np.dot(n, fuori)) < 0:
            B, D = D, B
        self.quad(tuple(A), tuple(B), tuple(C), tuple(D), uv)

    def pezzo(self, masc, verso, punto, dentro, pieghe=(), nome=None,
              punto_dentro=None):
        """Un pezzo col suo spessore: esterna, interna e coste.

        `punto(X, Y)` porta un pixel della sagoma sulla faccia esterna, in mm;
        `dentro` e' la direzione della faccia interna, e `punto_dentro`, se
        c'e', la faccia interna stessa - il blocco la fa rientrare di uno
        spessore dove il pezzo incontra gli altri, vedi *Un blocco unico,
        senza feritoie* nelle regole. `pieghe` sono le cordonature del pezzo,
        `("X", x)` o `("Y", y)` in pixel del foglio: un lato che ci sta sopra
        e' cartoncino che continua nel pezzo accanto, e la costa non ci va.

        Si procede a FASCE: due righe vicine e il cartoncino che hanno in
        comune, vedi `_fasce_comuni`. Cosi' il pezzo esce uno solo anche dove
        la sagoma si apre o si chiude, e le coste restano sui tagli veri.

        La COSTA va su OGNI taglio. Prima andava solo sui capi delle fasce, e
        i lati che corrono nel verso delle fasce - le teste dei fianchi, i
        lati del fronte, i gradini di un contorno curvo - restavano aperti: da
        vicino, fra la faccia esterna e quella interna si vedeva il vuoto. Sono
        le feritoie che si vedevano sugli spigoli dei vassoi.
        """
        import numpy as np
        from collections import defaultdict

        V, UV, T = self.V, self.UV, self.T
        W, H, q, vI, vT = self.W, self.H, self.q, self.vI, self.vT
        m = masc if verso == "righe" else masc.T
        if m.shape[0] < 2:
            return
        primo = len(T)
        d = np.array(dentro, float) * self.spessore
        if punto_dentro is None:
            punto_dentro = lambda X, Y: tuple(np.array(punto(X, Y), float) + d)
        # Il verso dell'avvolgimento non si indovina: si MISURA. La faccia
        # esterna deve guardare dalla parte opposta a `dentro`, e il piano lo
        # dice da solo - basta chiedere a `punto` dove vanno un passo in X e
        # uno in Y. Se la normale che ne esce punta dentro, i triangoli vanno
        # girati. Succede ai pezzi presi per colonne, dove la riga corre in X
        # e il tratto in Y: e' l'ordine scambiato rispetto a "righe", e la
        # normale esce rovesciata. Fuori si vedeva la faccia interna, cioe'
        # il cartoncino, e la stampa restava nascosta - il fronte e il retro
        # uscivano bianchi mentre i fianchi erano giusti.
        o = np.array(punto(0.0, 0.0), float)
        ex = np.array(punto(1.0, 0.0), float) - o
        ey = np.array(punto(0.0, 1.0), float) - o
        n = np.cross(ey, ex) if verso == "righe" else np.cross(ex, ey)
        rovescio = float(np.dot(n, np.array(dentro, float))) > 0

        # Lungo la fascia un pixel va da bordo a bordo, di traverso una riga
        # e' il suo CENTRO. Presa sul suo bordo alto, di traverso l'ultima riga
        # si perdeva, e sempre dalla stessa parte del foglio: girato il foglio
        # di mezzo giro la grafica scivolava di un pixel sul cartone.
        def dove(t, riga):
            return (t, riga + 0.5) if verso == "righe" else (riga + 0.5, t)

        def in_piega(P0, P1):
            for asse, val in pieghe:
                i = 0 if asse == "X" else 1
                if abs(P0[i] - val) <= PIEGA_TOL and abs(P1[i] - val) <= PIEGA_TOL:
                    return True
            return False

        def costa(P0, P1, verso_fuori):
            """La costa sul lato P0-P1 del foglio, che guarda `verso_fuori`.

            `verso_fuori` e' un passo sul foglio, (dt, driga), da dentro il
            pezzo verso fuori: portato in 3D dice dove deve guardare la costa.
            """
            if P0 == P1 or in_piega(P0, P1):
                return
            M = ((P0[0] + P1[0]) / 2.0, (P0[1] + P1[1]) / 2.0)
            # un passo, non un punto: senza il mezzo pixel di `dove`
            dt, driga = verso_fuori
            passo = (dt, driga) if verso == "righe" else (driga, dt)
            fuori = (np.array(punto(M[0] + passo[0], M[1] + passo[1]), float)
                     - np.array(punto(*M), float))
            self.faccia(punto(*P0), punto(*P1), punto_dentro(*P1),
                        punto_dentro(*P0), (0.5, vT), fuori)

        fasce = []

        def stendi(fascia, r0, r1):
            """Una fascia dalla riga `r0` alla `r1`, col suo spessore."""
            a, b, capo_a, capo_b = fascia
            fasce.append((a, b, r0, r1))
            # coste sui capi: solo sui tagli veri, non dove la fascia finisce
            # perche' l'altra riga e' piu' corta
            if capo_a:
                costa(dove(a, r0), dove(a, r1), (-1, 0))
            if capo_b:
                costa(dove(b, r0), dove(b, r1), (+1, 0))
            if rovescio:
                a, b = b, a
            XY = [dove(a, r0), dove(b, r0), dove(a, r1), dove(b, r1)]
            fuori = [np.array(punto(X, Y), float) for X, Y in XY]
            dentro_p = [np.array(punto_dentro(X, Y), float) for X, Y in XY]
            k = len(V)
            for (X, Y), f in zip(XY, fuori):
                V.append(tuple(f))
                UV.append((X / float(W), Y / float(H) * q))
            for pt in dentro_p:
                V.append(tuple(pt)); UV.append((0.5, vI))
            # faccia esterna
            T.append((k, k + 2, k + 1)); T.append((k + 2, k + 3, k + 1))
            # faccia interna, avvolta al contrario
            T.append((k + 4, k + 5, k + 6)); T.append((k + 6, k + 5, k + 7))

        # Le fasce che non cambiano si stendono in UNA sola: su un display la
        # base e buona parte delle pareti hanno lo stesso tratto per centinaia
        # di righe, e farne un quad per riga e' geometria pagata per niente.
        # Si uniscono solo se il tratto e i capi coincidono, quindi la
        # superficie che esce e' la stessa - verificato al pixel sul render.
        aperta, inizio = None, 0
        for i in range(1, m.shape[0]):
            fasce_i = _fasce_comuni(m, i)
            sola = fasce_i[0] if len(fasce_i) == 1 else None
            if aperta is not None and sola == aperta:
                continue
            if aperta is not None:
                stendi(aperta, inizio, i - 1)
            for f in fasce_i:
                if f is not sola:
                    stendi(f, i - 1, i)
            aperta, inizio = sola, i - 1
        if aperta is not None:
            stendi(aperta, inizio, m.shape[0] - 1)

        # Le coste lungo le righe: dove da una parte della riga c'e' una fascia
        # e dall'altra no, il lato e' un taglio - la testa di un fianco, il
        # lato di un fronte, il gradino di un contorno curvo.
        dopo, prima = defaultdict(list), defaultdict(list)
        for a, b, r0, r1 in fasce:
            dopo[r0].append((a, b))
            prima[r1].append((a, b))
        for r in sorted(set(dopo) | set(prima)):
            for s0, s1 in _meno(dopo[r], prima[r]):
                costa(dove(s0, r), dove(s1, r), (0, -1))
            for s0, s1 in _meno(prima[r], dopo[r]):
                costa(dove(s0, r), dove(s1, r), (0, +1))
        if self.parti is not None and nome:
            self.parti[nome] = (primo, len(T))

    def array(self):
        """`(V, UV, T)` come array, come li vuole l'esportatore."""
        import numpy as np
        return (np.array(self.V, float), np.array(self.UV, float),
                np.array(self.T, np.uint32))


def _ingombro(masc, verso):
    """`(r0, r1, c0, c1)`: fin dove arriva DAVVERO il pezzo che `Maglia.pezzo`
    stende da `masc` in quel `verso`, sulla griglia del foglio. None se non ha
    fasce.

    Non e' l'ingombro dei pixel. Una fascia c'e' dove due righe vicine hanno il
    cartoncino in comune, vedi `_fasce_comuni`, e lungo la riga arriva al bordo
    del suo ultimo pixel: un pixel da solo sul contorno - l'antialias di un
    angolo - allarga i pixel ma non la maglia. Ancorato ai pixel, il fianco
    ovest del KMS usciva un quarto di millimetro piu' basso del DT; e sul
    fondo, o sulla testa di un fianco, lo stesso quarto e' una feritoia.
    """
    import numpy as np
    m = masc if verso == "righe" else masc.T
    comune = m[:-1] & m[1:]
    fra = np.flatnonzero(comune.any(1))          # da una riga all'altra
    lungo = np.flatnonzero(comune.any(0))        # lungo la fascia
    if not len(fra):
        return None
    # di traverso dal centro della prima riga a quello dell'ultima, lungo la
    # fascia da bordo a bordo: vedi `dove` in `Maglia.pezzo`
    fra = (int(fra[0]) + 0.5, int(fra[-1]) + 1.5)
    lungo = (int(lungo[0]), int(lungo[-1]) + 1)
    return fra + lungo if verso == "righe" else lungo + fra


def _stira(a0, a1, b0, b1):
    """La mappa lineare che porta [a0, a1] su [b0, b1]."""
    if a1 == a0:
        return lambda v: b0
    k = (b1 - b0) / float(a1 - a0)
    return lambda v: b0 + (v - a0) * k


def corpo(maglia, mk, creste, px_mm, spessore=SPESSORE, dentro_alette=0.5,
          alte=None, fondo_mm=None):
    """Il BLOCCO del vassoio: fondo, quattro pareti e alette, senza feritoie.

    `mk` sono le maschere dei pezzi - fondo, ovest, est, nord, sud e le
    quattro alette - e `creste` le cordonature del fondo sulla sagoma,
    `(cxL, cxR, cyT, cyB)`. Riempie `maglia` e restituisce il telaio: dove
    stanno le quattro pareti e quanto sono alte, in mm.

    Le pareti si piegano come prima - lo specchio sulla z, uno solo, vedi
    `mesh` - ma si incontrano senza lasciare fessure, per tre regole:

      - ogni pezzo si ANCORA alla sua cordonatura: la riga di pixel del pezzo
        che sta sulla piega va esattamente sulla piega. Prese dalla griglia di
        pixel, le celle lasciavano un quarto di millimetro fra il fondo e
        alcune pareti, lungo tutta la piega;
      - fianchi, fronte e retro si STIRANO fino agli spigoli: la loro faccia
        esterna arriva sulla faccia esterna della parete accanto, e la pelle
        del blocco e' continua. Sul Tronky i fianchi sono 3 mm piu' corti del
        fondo - lo spessore, compensato dal DT - e lasciavano una feritoia
        di un millimetro e mezzo su ogni spigolo; stirati, la grafica si
        allunga dell'1,5%, che non si vede;
      - la faccia interna RIENTRA di uno spessore dove il pezzo incontra gli
        altri: cosi' agli spigoli le coste si incontrano a 45 gradi e il
        bordo alto gira l'angolo chiuso, come un blocco solo.

    Le alette restano dentro, incollate a fronte e retro: `dentro_alette` e'
    quanto stanno dietro la faccia esterna.

    `alte` (le altezze delle pareti, in mm) e `fondo_mm` (larghezza e
    profondita') sono le misure del DT: se ci sono, ogni pezzo si stira dalla
    sua piega al suo bordo su quelle, e non sui pixel. Il blocco esce allora
    uguale comunque stia il foglio sulla tavola - girando il foglio i pixel di
    un bordo cambiano, e sul Tronky la cima della plancia, che sta sul retro,
    ballava di mezzo millimetro fra un verso e l'altro.
    """
    t = spessore
    cxL, cxR, cyT, cyB = creste
    if fondo_mm is not None:
        xR, zT = fondo_mm[0] / 2.0, fondo_mm[1] / 2.0
    else:
        xR = (cxR - cxL) / 2.0 / px_mm
        zT = (cyB - cyT) / 2.0 / px_mm
    xL, zB = -xR, -zT

    def altezza(nome, piega, bordo):
        """Dalla piega (altezza 0) al bordo: sull'altezza del DT, se c'e'."""
        if alte and alte.get(nome):
            return _stira(piega, bordo, 0.0, float(alte[nome]))
        return _stira(piega, bordo, 0.0, abs(bordo - piega) / px_mm)
    pezzo = maglia.pezzo
    fra = lambda v, a, b: min(max(v, a), b)
    xin = lambda x: fra(x, xL + t, xR - t)
    zin = lambda z: fra(z, zB + t, zT - t)
    hin = lambda h: max(h, t)
    alt = {}

    # Ogni pezzo si ancora a fin dove arriva la sua maglia, vedi `_ingombro`:
    # lungo la fascia al BORDO dell'ultimo pixel, di traverso dal centro della
    # prima riga a quello dell'ultima. Ancorato ai pixel e non alla maglia
    # restava fuori un quarto di millimetro, ed e' stata la verifica del blocco
    # a dirlo.
    e = _ingombro(mk["fondo"], "righe")
    if e is not None:
        r0, r1, c0, c1 = e
        fx, fz = _stira(c0, c1, xL, xR), _stira(r0, r1, zT, zB)
        pezzo(mk["fondo"], "righe", lambda X, Y: (fx(X), 0.0, fz(Y)), (0, 1, 0),
              [("X", c0), ("X", c1), ("Y", r0), ("Y", r1)], "fondo",
              lambda X, Y: (xin(fx(X)), t, zin(fz(Y))))
    # i fianchi: la cordonatura e' la colonna verso il fondo, e si stirano
    # sulla lunghezza del fondo
    ancora = {}
    for nome, x_p, lato in (("ovest", xL, -1), ("est", xR, +1)):
        e = _ingombro(mk[nome], "righe")
        if e is None:
            continue
        r0, r1, c0, c1 = e
        piega, bordo = (c1, c0) if lato < 0 else (c0, c1)
        h = altezza(nome, piega, bordo)
        ancora[nome] = h
        fz = _stira(r0, r1, zT, zB)
        xi = x_p - lato * t
        alt[nome] = h(bordo)
        pezzo(mk[nome], "righe",
              lambda X, Y, h=h, fz=fz, x_p=x_p: (x_p, h(X), fz(Y)),
              (-lato, 0, 0), [("X", piega)], nome,
              lambda X, Y, h=h, fz=fz, xi=xi: (xi, hin(h(X)), zin(fz(Y))))
    # fronte e retro: la cordonatura e' la riga verso il fondo, e si stirano
    # sulla larghezza del fondo
    for nome, z_p, lato in (("nord", zT, +1), ("sud", zB, -1)):
        e = _ingombro(mk[nome], "colonne")
        if e is None:
            continue
        r0, r1, c0, c1 = e
        piega, bordo = (r1, r0) if lato > 0 else (r0, r1)
        h = altezza(nome, piega, bordo)
        fx = _stira(c0, c1, xL, xR)
        zi = z_p - lato * t
        alt[nome] = h(bordo)
        pezzo(mk[nome], "colonne",
              lambda X, Y, h=h, fx=fx, z_p=z_p: (fx(X), h(Y), z_p),
              (0, 0, -lato), [("Y", piega)], nome,
              lambda X, Y, h=h, fx=fx, zi=zi: (xin(fx(X)), hin(h(Y)), zi))
    # Le alette: piegate sul fianco, finiscono dentro fronte e retro. La loro
    # piega e' la riga verso il fianco, e l'altezza e' quella del fianco.
    for nome, fianco, x_p, z_p, dz in (
            ("aletta nord-ovest", "ovest", xL, zT, -1),
            ("aletta nord-est", "est", xR, zT, -1),
            ("aletta sud-ovest", "ovest", xL, zB, +1),
            ("aletta sud-est", "est", xR, zB, +1)):
        e = _ingombro(mk[nome], "righe")
        if e is None or fianco not in ancora:
            continue
        r0, r1, c0, c1 = e
        piega = r1 if dz < 0 else r0
        # lineare, e col segno giusto: il verso dell'avvolgimento `pezzo` lo
        # misura in (0, 0), lontano dall'aletta, e con un valore assoluto
        # le alette di sud uscivano specchiate
        verso_x = 1.0 if fianco == "ovest" else -1.0
        passo = -dz * verso_x
        h = ancora[fianco]              # l'altezza e' quella del suo fianco
        # L'aletta sta DENTRO lo spessore della parete a cui e' incollata: la
        # faccia esterna mezzo spessore dietro quella della parete, e quella
        # interna sulla faccia interna della parete, stesso colore. Cosi' dove
        # c'e' la parete l'aletta non si vede, e i suoi bordi stanno chiusi
        # nello spessore: con l'aletta mezzo millimetro in fuori, all'interno
        # del Tronky i suoi bordi disegnavano due righe a trattini sul retro.
        # Dove la parete e' piu' bassa - il fronte del KMS - l'aletta sporge
        # sopra ed e' un pannello a se', chiuso dalle sue coste.
        pezzo(mk[nome], "righe",
              lambda X, Y, h=h, piega=piega, x_p=x_p, passo=passo, z_p=z_p, dz=dz:
              (x_p + passo * (piega - Y) / px_mm, h(X),
               z_p + dz * dentro_alette),
              (0, 0, dz), [("Y", piega)], nome,
              lambda X, Y, h=h, piega=piega, x_p=x_p, passo=passo, z_p=z_p, dz=dz:
              (x_p + passo * (piega - Y) / px_mm, h(X), z_p + dz * t))
    return {"xL": xL, "xR": xR, "zT": zT, "zB": zB, "alt": alt}


def misure_blocco(v: Vassoio):
    """`(fondo_mm, alte)` del blocco dal DT, prese sulle stesse pieghe della
    maglia.

    Non sono `fondo_w` e `pareti`: quelle sono le fasce della griglia, e sulle
    colonne la piega sta a META' della cordonatura, come in `sagoma_e_creste`.
    Sul KMS le fasce danno un fondo di 145,5 mm, e fra le due meta' di
    cordonatura ci sono 147,5 mm: stirato sulle fasce il blocco usciva stretto
    di due millimetri e i fianchi bassi di uno.
    """
    r = v.riquadri
    cL = (r["ovest"][2] + r["fondo"][0]) / 2.0
    cR = (r["fondo"][2] + r["est"][0]) / 2.0
    cT, cB = r["fondo"][1], r["fondo"][3]
    fondo_mm = ((cR - cL) * PT2MM, (cB - cT) * PT2MM)
    alte = {"ovest": (cL - r["ovest"][0]) * PT2MM,
            "est": (r["est"][2] - cR) * PT2MM,
            "nord": (cT - r["nord"][1]) * PT2MM,
            "sud": (r["sud"][3] - cB) * PT2MM}
    return fondo_mm, alte


def mesh(v: Vassoio, sagoma, px_mm, creste, spessore=SPESSORE,
         alt_texture=None, parti=None):
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

    `parti`, se c'e', si riempie con i triangoli di ogni pezzo - `{nome:
    (primo, ultimo + 1)}` con i nomi della griglia, fondo, nord, est, sud,
    ovest e le alette - perche' le verifiche li possano confrontare col DT.
    """
    import numpy as np

    H, W = sagoma.shape
    cxL, cxR, cyT, cyB = creste
    # UNO specchio, e uno solo. Piegando lo steso cosi' com'e' la stampa
    # finisce DENTRO - il marchio si legge mirror, cioe' attraverso il
    # cartone - perche' la faccia stampata guardava in su e piegando in su
    # va a guardare l'interno. Ci vuole uno specchio per rimetterla fuori, e
    # uno solo: con due (x e z) e' una rotazione, e torna mirror.
    #
    # Si specchia la **z**, non la x. Le due scelte leggono uguale - il
    # marchio sta dritto su tutte e quattro le pareti - e cambiano solo quale
    # testata guarda la camera. Sul Milch-Schnitte le due testate portano la
    # stessa grafica, quindi da qui non si decide: se arriva un display con
    # fronte e retro diversi, quello e' il file su cui verificarlo. Lo
    # specchio sta in `corpo`: la riga di sopra del foglio va verso +z.
    maglia = Maglia(W, H, spessore, alt_texture, parti)

    def cella(y0, y1, x0, x1):
        m = np.zeros((H, W), bool)
        m[y0:y1, x0:x1] = True
        return m & sagoma

    mk = {"fondo": cella(cyT, cyB, cxL, cxR),
          "ovest": cella(cyT, cyB, 0, cxL), "est": cella(cyT, cyB, cxR, W),
          "nord": cella(0, cyT, cxL, cxR), "sud": cella(cyB, H, cxL, cxR),
          "aletta nord-ovest": cella(0, cyT, 0, cxL),
          "aletta nord-est": cella(0, cyT, cxR, W),
          "aletta sud-ovest": cella(cyB, H, 0, cxL),
          "aletta sud-est": cella(cyB, H, cxR, W)}
    fondo_mm, alte = misure_blocco(v)
    corpo(maglia, mk, creste, px_mm, spessore, alte=alte, fondo_mm=fondo_mm)
    return maglia.array()


# piu' chiaro di cosi', e attaccato al bordo del foglio, non e' cartoncino
FOGLIO_CHIARO = 150


def _foglio(a):
    """Il foglio attorno alla cartotecnica, come maschera.

    Non e' "dove non c'e' inchiostro". Attorno al display Milch-Schnitte il
    file ha un'OMBRA SFUMATA - un abbellimento della presentazione, che in
    macchina non ci va - e scende da 253 a 170 su quattro millimetri e mezzo.
    Una soglia sull'inchiostro se la prende tutta: la cartotecnica usciva 4,5
    mm piu' larga del vero, e quella fascia, che sulla texture pulita e' foglio
    bianco, finiva stesa sul bordo dei fianchi. E' il "bianco sui laterali".

    Il foglio si riconosce invece da DOVE STA: e' il chiaro che si raggiunge
    partendo dal bordo della pagina. Un chiaro circondato dalla grafica - il
    bianco dentro le lettere di kinder, un pannello chiaro in mezzo - non si
    raggiunge e resta cartoncino, e non serve piu' tapparlo a posteriori. E il
    tratto della fustella, che e' colorato, ferma la macchia da solo: dove la
    penna c'e', anche un cartoncino stampato chiaro fino al taglio si salva.
    """
    import numpy as np
    from scipy.ndimage import label

    lab, _ = label(a.min(2) > FOGLIO_CHIARO)
    bordo = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return np.isin(lab, bordo[bordo > 0])


def sagoma_e_creste(pdf, d, px_mm=4.0, page_no=0, note=None):
    """`(sagoma, creste, resa)` per costruire il vassoio.

    La sagoma della cartotecnica **non viene dal tracciato**. La penna della
    fustella ha interruzioni - sul display Milch-Schnitte sono da 3 mm, e
    riempiendola si prende solo la colonna centrale, perche' le cordonature
    chiudono quella cella e il contorno esterno no. Viene invece
    dall'**impronta di stampa**: su questi display la stampa arriva al
    taglio, e allora l'impronta E' la cartotecnica. Misurata sul Milch-
    Schnitte: 346,5 x 466,5 mm, cioe' esattamente le quote del disegno
    tecnico 34150.

    E l'impronta non e' "dove c'e' inchiostro": vedi `_foglio`.
    """
    import numpy as np
    from scipy.ndimage import binary_fill_holes, label

    from .dieline import PT2MM, render_page

    scala = px_mm * 25.4 / 72.0
    resa = render_page(pdf, page_no, scala).convert("RGB")
    a = np.asarray(resa)
    lab, quanti = label(~_foglio(a))
    if quanti == 0:
        return None, None, resa
    dim = np.bincount(lab.ravel())
    dim[0] = 0
    sagoma = binary_fill_holes(lab == int(np.argmax(dim)))
    # Mai oltre il taglio: la forma la da' l'impronta, l'ingombro la fustella.
    # Prima le misure, poi il contenuto - e un'ombra o una sbavatura fuori
    # dalla fustella non e' cartoncino, per quanto sia attaccata alla stampa.
    marg = 0.5 * px_mm
    x0, y0, x1, y1 = (int(round(d.bbox[0] * scala - marg)), int(round(d.bbox[1] * scala - marg)),
                      int(round(d.bbox[2] * scala + marg)), int(round(d.bbox[3] * scala + marg)))
    dentro = np.zeros_like(sagoma)
    dentro[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
    sagoma &= dentro
    if note is not None:
        ys, xs = np.nonzero(sagoma)
        mis = ((xs.max() - xs.min() + 1) / px_mm, (ys.max() - ys.min() + 1) / px_mm)
        dt = ((d.bbox[2] - d.bbox[0]) * PT2MM, (d.bbox[3] - d.bbox[1]) * PT2MM)
        if max(abs(m - q) for m, q in zip(mis, dt)) > 2.0:
            note.append("l'impronta della cartotecnica misura %.1f x %.1f mm ma "
                        "la fustella ne misura %.1f x %.1f: la stampa non arriva "
                        "al taglio, oppure e' chiara e si confonde col foglio"
                        % (mis + dt))
    gx = sorted({round(t, 1) for t in d.xs})
    gy = sorted({round(t, 1) for t in d.ys})
    creste = (int(round((gx[1] + gx[2]) / 2 * scala)),
              int(round((gx[3] + gx[4]) / 2 * scala)),
              int(round(gy[1] * scala)), int(round(gy[2] * scala)))
    return sagoma, creste, resa
