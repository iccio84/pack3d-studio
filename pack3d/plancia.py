"""
Il display con plancia: una scatola chiusa che, aperta, diventa espositore.

Il Tronky T48 - Ferrero CT4977, "Display con plancia per T48" - arriva come
una scatola CHIUSA. Si apre staccando dei pezzi, e diventa un espositore da
banco con un cartello in piedi dietro al prodotto: la **plancia**, che e' uno
dei pezzi della scatola. Dichiarato "vassoio" o "display" si costruiva come
niente - cinque colonne e dieci fasce, non e' un vassoio - e senza
dichiarazione usciva un FLOWPACK: un modello plausibile della famiglia
sbagliata, il difetto peggiore che questo progetto possa avere.

Sta accanto al vassoio, e ne riusa tutto quello che ha in comune: il fondo, le
quattro pareti e le alette agli angoli sono quelle di `vassoio`, stese dalla
stessa `vassoio.Maglia`. In piu' c'e' un **coperchio** grande quanto il fondo,
attaccato al bordo di un fianco, e le falde che ci si incollano sotto. Sul DT
del Tronky, in mm:

    colonne   15 | 116 | 134 | 117 | 133      falda, fianco, fondo, fianco,
    fasce     25 | 116 | 204 | 116 | 25       coperchio; falda, fronte, fondo,
                                               retro, falda

Come si apre, letto sul DT - dove il file NON ha un livello per le linee e
tutte le linee, tagli, cordonature e perforazioni, sono la stessa penna ciano:

  1. la **finestra** del fronte si strappa via. Il contorno e' perforato (sul
     file sono centinaia di tratti da un millimetro), parte dal bordo alto e
     ha in basso un mezzo tondo da spingere per metterci il dito. Resta una
     parete bassa, da cui si vede e si prende il prodotto;
  2. il coperchio si stacca dal fianco e dalla falda del fianco opposto -
     cordonature perforate anche quelle - e resta attaccato solo al **retro**,
     con la falda del retro incollata sotto: quella e' la cerniera;
  3. si alza in piedi sul retro, e la parte che stava davanti si ripiega in
     avanti sulla **doppia cordonatura** che attraversa il coperchio: due
     righe a 8,1 mm, la piega a 180 gradi di un cartone da 4 mm. Un taglio a
     onda, con i punti di tenuta, la stacca dall'altra parte fra le due
     righe;
  4. cosi' la parte di davanti finisce DAVANTI a quella di dietro, con la
     stampa verso chi guarda, e il suo piede - 20 mm piu' lungo - entra nella
     scatola davanti alla parete del retro e la blocca. La falda del fronte,
     incollata al piede, riempie gli 8 mm fra le due.

Non e' una lettura fra tante: e' l'UNICA piega in cui la plancia si legge
dritta da tutte e due le parti, e la grafica del file e' fatta per quella. La
parte davanti del coperchio sul foglio sta a testa in giu', e girata cosi' va
dritta; quella dietro sta dritta, e dritta la legge chi passa dietro al
banco. Il taglio a onda diventa la cresta della plancia, con la stampa verso
chi guarda. E ogni altra piega tradisce qualcosa: alzata dal lato del fronte
la plancia starebbe davanti al prodotto; alzata dal retro senza ripiegarla
guarderebbe il muro; ripiegata al contrario mostrerebbe davanti il rovescio
bianco della cresta.

Quello che la costruzione NON fa: le falde incollate sotto il coperchio non si
vedono piu' - stanno fra le due facce della plancia, o sono venute via con la
finestra - e non si costruiscono.

**Il coperchio sul retro.** Il secondo display del parco, un "ready to
display" da tre file di trenta pezzi, e' della stessa famiglia, montato in un
altro modo. E' un vassoio con il fronte basso, e il coperchio e' incernierato sul
bordo alto del RETRO, non su un fianco: sul foglio continua il retro, oltre
la sua riga esterna. Lo attraversa UNA riga sola, parallela alla cerniera -
un mezzo taglio, non la doppia cordonatura del Tronky - e oltre la riga c'e'
la parte con la grafica grande, con una linguetta che entra nella parte
attaccata al retro e ne esce col suo contorno perforato. In mm:

    colonne   103 | 174 | 103                 fianco, fondo, fianco
    fasce     65 | 215 | 104 | 99 | 113       fronte, fondo, retro, coperchio

A display montato, l'ha confermato chi lo monta (issue #3 dei casi): il
coperchio ruota di 90 gradi sulla cerniera e la parte attaccata al retro ne
diventa il prolungamento in alto, con la stampa verso dietro; l'altra si
ripiega di 180 gradi in avanti sulla riga e le scende davanti, con la stampa
verso chi guarda. La linguetta, che e' sua, spunta sopra la riga come
cresta, e il suo piede - 14 mm piu' lungo - entra nella scatola davanti al
retro. E' la plancia del Tronky con il dorso largo uno spessore e la cerniera
sul retro: si riconosce da li', ed e' l'unica lettura possibile, perche' il
coperchio sta su UNA sola delle due testate, quella alta. Il fronte e' la
testata bassa, e non ha finestra da strappare.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .dieline import PT2MM
from .vassoio import SPESSORE, Maglia, gira

MM = 1.0 / PT2MM          # punti in un millimetro

# Quanto possono ballare due righe per dirsi la stessa, in punti.
STESSA = 0.6
# Quanto puo' mancare fra due tratti di fila perche' siano una riga sola: le
# cordonature perforate il file le disegna a pezzi, tutti uno dietro l'altro.
DI_FILA = 1.2
# Le righe corte non fanno griglia: frecce, tacche, punti di tenuta.
RIGA_MINIMA = 15.0 * MM
# Quanto possono ballare due righe della griglia fra loro: il fondo e i
# fianchi del Tronky finiscono a 1,5 mm l'uno dagli altri, per lo spessore.
GRIGLIA = 1.5 * MM
# Un fondo piu' piccolo di cosi' non regge un espositore.
FONDO_MINIMO = 40.0 * MM
# Il bordo di una parete deve coprire almeno questa parte del lato del fondo.
COPRE = 0.9
# Il coperchio e' grande quanto il fondo, a meno di questo.
COPERCHIO = (0.9, 1.1)
# Le due righe della doppia cordonatura: fra una piega vera a 180 gradi e due
# righe che non c'entrano l'una con l'altra.
DOPPIA = (3.0 * MM, 20.0 * MM)
# Il coperchio sul retro: la riga che lo attraversa arriva ai suoi lati a meno
# di questo - fra la riga e il lato c'e' l'intaglio a V della piega...
PIEGA_BORDO = 10.0 * MM
# ...il fronte e' la testata bassa, al piu' questa parte del retro...
FRONTE_BASSO = 0.8
# ...e il bordo di un fianco ne copre almeno questa parte: gli angoli del
# fianco sono stondati, e sul display T3x30 la riga dritta e' l'83%.
COPRE_FIANCO = 0.75
# La linguetta si stacca dalla parte dietro su un contorno PERFORATO: per
# dividere le due parti i tratti si chiudono di tanto, in mm per lato. Copre i
# punti di tenuta da due millimetri.
CHIUDI = 1.25
# La finestra parte dal bordo alto della parete, a meno di questo...
FINESTRA_BORDO = 15.0 * MM
# ...e i suoi lati sono lunghi almeno questa parte della parete.
FINESTRA_LATO = 0.25


@dataclass
class Plancia:
    """Un display con plancia, in punti PDF con la y dall'alto.

    `bordi` e' il bordo esterno di ogni parete - cioe' la riga dove finisce la
    parete e comincia la falda, o il coperchio - e `fianchi` le due righe dove
    finiscono i fianchi, che non sono quelle del fondo: sul Tronky stanno 1,5
    mm piu' dentro, per lo spessore. `pieghe` sono le due righe della doppia
    cordonatura del coperchio, dall'alto.

    `cerniera` dice dove sta il coperchio: "fianco" (il Tronky) o "retro" (il
    display T3x30). Sul retro `lato_coperchio` e' la testata del retro, le
    due `pieghe` sono la stessa riga - il dorso e' largo uno spessore - e
    `finestra` e' None.
    """
    fondo: tuple              # (x0, y0, x1, y1)
    bordi: dict               # {"ovest": x, "est": x, "nord": y, "sud": y}
    fianchi: tuple            # (y0, y1)
    coperchio: tuple          # (x0, y0, x1, y1)
    lato_coperchio: str       # "est" o "ovest": la parete che lo porta
    pieghe: tuple             # (y, y)
    fronte: str               # "nord" o "sud": la parete con la finestra
    finestra: tuple           # (x0, y0, x1, y1): il riquadro della finestra
    warnings: list = field(default_factory=list)
    cerniera: str = "fianco"  # "fianco" o "retro": dove sta il coperchio

    @property
    def retro(self):
        return "sud" if self.fronte == "nord" else "nord"

    @property
    def pareti(self):
        """Le altezze delle quattro pareti, in mm, da nord in senso orario."""
        x0, y0, x1, y1 = self.fondo
        b = self.bordi
        return {"nord": (y0 - b["nord"]) * PT2MM, "est": (b["est"] - x1) * PT2MM,
                "sud": (b["sud"] - y1) * PT2MM, "ovest": (x0 - b["ovest"]) * PT2MM}

    @property
    def parti_coperchio(self):
        """`(davanti, dorso, dietro)` del coperchio in mm, dal lato del fronte.

        Davanti e' la faccia della plancia, dietro la parte che resta sulla
        cerniera del retro, il dorso la striscia fra le due righe.
        """
        _x0, y0, _x1, y1 = self.coperchio
        a, b = self.pieghe
        nord, dorso, sud = (a - y0) * PT2MM, (b - a) * PT2MM, (y1 - b) * PT2MM
        if self.cerniera == "retro":
            # la parte dietro e' quella attaccata al retro
            return (sud, dorso, nord) if self.retro == "sud" else (nord, dorso, sud)
        return (nord, dorso, sud) if self.fronte == "nord" else (sud, dorso, nord)

    @property
    def dims_mm(self):
        """Ingombro del display aperto: larghezza, profondita', altezza."""
        x0, y0, x1, y1 = self.fondo
        _davanti, _dorso, dietro = self.parti_coperchio
        return ((x1 - x0) * PT2MM, (y1 - y0) * PT2MM,
                self.pareti[self.retro] + dietro)


def _corse(pezzi):
    """I tratti collineari e di fila uniti in corse: `[(c, a, b)]` in punti.

    Una cordonatura perforata il file la disegna a pezzi: la cerniera del
    coperchio del Tronky e' 124 tratti da uno, due e tre millimetri, uno
    dietro l'altro. Per la griglia e' una riga sola, e cosi' va letta.
    """
    gruppi = []
    for c, a, b in sorted(pezzi):
        if gruppi and c - gruppi[-1][0][0] <= STESSA:
            gruppi[-1].append((c, a, b))
        else:
            gruppi.append([(c, a, b)])
    out = []
    for g in gruppi:
        c = sum(p[0] for p in g) / len(g)
        cur = None
        for _c, a, b in sorted(g, key=lambda p: p[1]):
            if cur is not None and a <= cur[1] + DI_FILA:
                cur[1] = max(cur[1], b)
            else:
                if cur is not None:
                    out.append((c, cur[0], cur[1]))
                cur = [a, b]
        out.append((c, cur[0], cur[1]))
    return [r for r in out if r[2] - r[1] >= RIGA_MINIMA]


def _copre(corsa, a, b, quota=COPRE):
    return min(b, corsa[2]) - max(a, corsa[1]) >= quota * (b - a)


def _su(corse, c, a, b, quota=COPRE):
    """La corsa sulla riga `c` che copre [a, b], o None."""
    for r in corse:
        if abs(r[0] - c) <= GRIGLIA and _copre(r, a, b, quota):
            return r
    return None


def _prima(corse, c, verso, a, b, quota=COPRE):
    """La prima corsa oltre `c` nel verso dato che copre [a, b], o None.

    Cosi' si trova il bordo esterno di una parete: la riga parallela piu'
    vicina al fondo che la attraversa tutta. Le righe che la attraversano solo
    in parte - il fondo della finestra, il riquadro della scadenza - non sono
    un bordo, e si saltano.
    """
    oltre = [r for r in corse
             if (r[0] - c) * verso > GRIGLIA and _copre(r, a, b, quota)]
    if not oltre:
        return None
    return min(oltre, key=lambda r: abs(r[0] - c))


def _pieghe(H, x0, y0, x1, y1):
    """Le due righe della doppia cordonatura del coperchio, o None.

    Una riga di piega attraversa il coperchio da un bordo all'altro, magari
    interrotta in mezzo - sul Tronky l'onda del taglio la spezza - quindi si
    cerca una riga che tocchi TUTTI E DUE i bordi, alla stessa quota.
    """
    livelli = []
    for r in H:
        if not (y0 + 5 * MM < r[0] < y1 - 5 * MM):
            continue
        if abs(r[1] - x0) > GRIGLIA:
            continue
        # la stessa riga dall'altra parte: puo' essere lei stessa, se e'
        # dritta da un bordo all'altro
        if not any(abs(s[0] - r[0]) <= GRIGLIA and abs(s[2] - x1) <= GRIGLIA
                   for s in H):
            continue
        if not any(abs(l - r[0]) <= GRIGLIA for l in livelli):
            livelli.append(r[0])
    livelli.sort()
    coppie = [(a, b) for a, b in zip(livelli, livelli[1:])
              if DOPPIA[0] <= b - a <= DOPPIA[1]]
    return coppie[0] if len(coppie) == 1 else None


def _finestra(V, H, x0, x1, bordo, fondo):
    """Il riquadro della finestra a strappo nella parete fra `bordo` e `fondo`.

    La finestra parte dal bordo alto della parete - e' quello che la fa una
    finestra e non un riquadro stampato, come quello della scadenza che sta
    sul fianco - e ha due lati lunghi dentro la parete. None se non c'e'.
    """
    alt = abs(fondo - bordo)
    lati = []
    for r in V:
        if not (x0 + 3 * MM < r[0] < x1 - 3 * MM):
            continue
        if r[2] - r[1] < FINESTRA_LATO * alt:
            continue
        lo, hi = min(bordo, fondo), max(bordo, fondo)
        if r[1] < lo - GRIGLIA or r[2] > hi + GRIGLIA:
            continue
        vicino = (r[1] - bordo) if bordo < fondo else (bordo - r[2])
        if 0 <= vicino <= FINESTRA_BORDO:
            lati.append(r)
    if len(lati) < 2:
        return None
    sx, dx = min(r[0] for r in lati), max(r[0] for r in lati)
    # il fondo della finestra: la riga fra i due lati piu' lontana dal bordo
    basse = [r[0] for r in H
             if r[1] >= sx - 10 * MM and r[2] <= dx + 10 * MM
             and min(bordo, fondo) < r[0] < max(bordo, fondo)]
    if bordo < fondo:
        giu = max(basse) if basse else max(r[2] for r in lati)
        return (sx, bordo, dx, giu)
    su = min(basse) if basse else min(r[1] for r in lati)
    return (sx, su, dx, bordo)


def riconosci(d):
    """`Plancia` dalla griglia della fustella, o `None` se non lo e'.

    `d` e' quello che restituisce `dieline.extract`. Come per il vassoio si
    guarda la griglia e basta, e niente si stima: il fondo e' il rettangolo di
    cordonature con una parete su ogni lato; il coperchio e' il pannello
    grande quanto il fondo oltre uno dei due fianchi; la doppia cordonatura lo
    attraversa; il fronte e' la parete con la finestra. Se manca un pezzo non
    e' un display con plancia, e lo si dice invece di costruire altro.
    """
    V = _corse(getattr(d, "vsegs", None) or [])
    H = _corse(getattr(d, "hsegs", None) or [])
    for i, h0 in enumerate(H):
        for h1 in H[i + 1:]:
            y0, y1 = sorted((h0[0], h1[0]))
            if y1 - y0 < FONDO_MINIMO:
                continue
            if abs(h0[1] - h1[1]) > GRIGLIA or abs(h0[2] - h1[2]) > GRIGLIA:
                continue
            x0, x1 = (h0[1] + h1[1]) / 2.0, (h0[2] + h1[2]) / 2.0
            if x1 - x0 < FONDO_MINIMO:
                continue
            if _su(V, x0, y0, y1) is None or _su(V, x1, y0, y1) is None:
                continue
            p = (_attorno(V, H, x0, y0, x1, y1)
                 or _sul_retro(V, H, x0, y0, x1, y1))
            if p is not None:
                return p
    return None


def _attorno(V, H, x0, y0, x1, y1):
    """Pareti, coperchio, pieghe e finestra attorno al fondo dato, o None."""
    ovest = _prima(V, x0, -1, y0, y1)
    est = _prima(V, x1, +1, y0, y1)
    nord = _prima(H, y0, -1, x0, x1)
    sud = _prima(H, y1, +1, x0, x1)
    if None in (ovest, est, nord, sud):
        return None
    # il coperchio: oltre uno dei due fianchi, largo quanto il fondo
    largo = x1 - x0
    cand = []
    for lato, bordo, verso in (("est", est, +1), ("ovest", ovest, -1)):
        oltre = _prima(V, bordo[0], verso, y0, y1)
        if oltre is None:
            continue
        if COPERCHIO[0] <= abs(oltre[0] - bordo[0]) / largo <= COPERCHIO[1]:
            cand.append((lato, bordo, oltre))
    if len(cand) != 1:
        return None
    lato, bordo, oltre = cand[0]
    cx0, cx1 = sorted((bordo[0], oltre[0]))
    cy0, cy1 = max(bordo[1], oltre[1]), min(bordo[2], oltre[2])
    pieghe = _pieghe(H, cx0, cy0, cx1, cy1)
    if pieghe is None:
        return None
    # il fronte e' la parete con la finestra, e deve essere una sola
    fin_n = _finestra(V, H, x0, x1, nord[0], y0)
    fin_s = _finestra(V, H, x0, x1, sud[0], y1)
    if (fin_n is None) == (fin_s is None):
        return None
    fronte, finestra = ("nord", fin_n) if fin_n is not None else ("sud", fin_s)
    # dove finiscono i fianchi: il bordo esterno del fianco senza coperchio
    altro = ovest if lato == "est" else est
    p = Plancia(fondo=(x0, y0, x1, y1),
                bordi={"ovest": ovest[0], "est": est[0], "nord": nord[0],
                       "sud": sud[0]},
                fianchi=(altro[1], altro[2]),
                coperchio=(cx0, cy0, cx1, cy1), lato_coperchio=lato,
                pieghe=pieghe, fronte=fronte, finestra=finestra)
    davanti, _dorso, dietro = p.parti_coperchio
    if davanti <= dietro:
        # Il piede della plancia e' la parte davanti che avanza sotto quella
        # dietro: se non avanza, la plancia non ha niente che la tenga in
        # piedi. Il modello si fa lo stesso, ma lo si dice.
        p.warnings.append(
            "la parte davanti del coperchio (%.1f mm) non e' piu' lunga di "
            "quella dietro (%.1f): la plancia non ha il piede che entra nella "
            "scatola, e non si vede cosa la tenga in piedi" % (davanti, dietro))
    return p


def _piega_sola(H, x0, y0, x1, y1):
    """La riga che attraversa il coperchio sul retro, o None.

    Come in `_pieghe` una riga che arriva a tutti e due i lati, magari
    interrotta in mezzo - qui la interrompe la linguetta - ma ai lati si
    ferma prima, sull'intaglio a V della piega: si accetta fino a
    `PIEGA_BORDO`. Ce ne deve essere UNA: due sono la doppia cordonatura del
    Tronky, e il suo coperchio sta sul fianco.
    """
    livelli = []
    for r in H:
        if not (y0 + 5 * MM < r[0] < y1 - 5 * MM):
            continue
        if not 0 <= r[1] - x0 <= PIEGA_BORDO:
            continue
        if not any(abs(s[0] - r[0]) <= GRIGLIA and 0 <= x1 - s[2] <= PIEGA_BORDO
                   for s in H):
            continue
        if not any(abs(l - r[0]) <= GRIGLIA for l in livelli):
            livelli.append(r[0])
    return livelli[0] if len(livelli) == 1 else None


# la cordonatura fra il fondo e una parete, in punti: vedi `vassoio`
CORDONATURA = 6.0 * MM


def _fine_fianco(H, c, verso, a, b):
    """La riga dove finisce il fianco fra le colonne [a, b], vicino a `c`.

    Il fianco e' piu' corto del fondo dello spessore di fronte e retro: sul
    display col coperchio sul retro finisce 2 mm prima, sulla cordonatura della sua aletta.
    Se non c'e' una riga cosi', finisce dove finisce il fondo.
    """
    vicine = [r for r in H if 0 <= (r[0] - c) * verso <= CORDONATURA
              and _copre(r, a, b, COPRE_FIANCO)]
    if not vicine:
        return c
    return min(vicine, key=lambda r: abs(r[0] - c))[0]


def _sul_retro(V, H, x0, y0, x1, y1):
    """Il display col coperchio sul RETRO attorno al fondo dato, o None.

    Vedi *Il coperchio sul retro* in cima al modulo. Il fondo ha i fianchi a
    ovest e a est e le testate a nord e a sud; oltre UNA sola testata c'e' un
    coperchio lungo quanto il fondo e largo quanto lui, attraversato da una
    riga sola. Quella testata e' il retro, l'altra il fronte, e il fronte
    deve essere basso: e' da li' che si prende il prodotto. Se manca un
    pezzo, o le testate sono alte uguali, non e' questa famiglia.
    """
    ovest = _prima(V, x0, -1, y0, y1, COPRE_FIANCO)
    est = _prima(V, x1, +1, y0, y1, COPRE_FIANCO)
    nord = _prima(H, y0, -1, x0, x1)
    sud = _prima(H, y1, +1, x0, x1)
    if None in (ovest, est, nord, sud):
        return None
    lungo = y1 - y0
    cand = []
    for lato, bordo, verso in (("nord", nord, -1), ("sud", sud, +1)):
        oltre = _prima(H, bordo[0], verso, x0, x1)
        if oltre is None:
            continue
        if COPERCHIO[0] <= abs(oltre[0] - bordo[0]) / lungo <= COPERCHIO[1]:
            cand.append((lato, bordo, oltre))
    if len(cand) != 1:
        return None
    retro, bordo, oltre = cand[0]
    cy0, cy1 = sorted((bordo[0], oltre[0]))
    cx0, cx1 = max(oltre[1], x0), min(oltre[2], x1)
    piega = _piega_sola(H, cx0, cy0, cx1, cy1)
    if piega is None:
        return None
    fronte = "nord" if retro == "sud" else "sud"
    ya = _fine_fianco(H, y0, +1, ovest[0], x0)
    yb = _fine_fianco(H, y1, -1, ovest[0], x0)
    p = Plancia(fondo=(x0, y0, x1, y1),
                bordi={"ovest": ovest[0], "est": est[0], "nord": nord[0],
                       "sud": sud[0]},
                fianchi=(ya, yb), coperchio=(cx0, cy0, cx1, cy1),
                lato_coperchio=retro, pieghe=(piega, piega), fronte=fronte,
                finestra=None, cerniera="retro")
    alt = p.pareti
    if alt[fronte] > FRONTE_BASSO * alt[retro]:
        return None
    davanti, _dorso, dietro = p.parti_coperchio
    if davanti <= dietro:
        p.warnings.append(
            "la parte davanti del coperchio (%.1f mm) non e' piu' lunga di "
            "quella dietro (%.1f): la plancia non ha il piede che entra nella "
            "scatola, e non si vede cosa la tenga in piedi" % (davanti, dietro))
    return p


def di_traverso(d):
    """`Plancia` dalla griglia TRASPOSTA, o None: il display girato di un quarto.

    Serve all'analisi senza dichiarazione, che il foglio non lo gira - costa
    un'estrazione per verso, e la pagherebbe ogni astuccio e ogni flowpack -
    e cosi' il Tronky messo di traverso sulla tavola usciva di nuovo
    flowpack. Scambiare righe e colonne della griglia gia' letta invece non
    costa niente, e dice se girato di un quarto il foglio e' un display: lo
    scambio e' uno specchio e non un giro, ma il riconoscimento non guarda la
    mano. Le coordinate che ne escono sono quelle del foglio trasposto, quindi
    valgono per le misure e per dire la famiglia, non per costruire: la
    costruzione gira il foglio davvero, con `riconosci_sulla_tavola`.
    """
    class _Trasposta:
        vsegs = list(getattr(d, "hsegs", None) or [])
        hsegs = list(getattr(d, "vsegs", None) or [])
    return riconosci(_Trasposta)


def riconosci_sulla_tavola(pdf):
    """`(pdf, dieline estratta, Plancia o None, giro, avviso)`.

    Come `vassoio.riconosci_sulla_tavola`: se nel verso del foglio non torna si
    prova il foglio girato di un quarto, prima di dire che non e' un display.
    Mezzo giro non serve, perche' il fronte lo dice la finestra e non la
    tavola.
    """
    from . import artwork, dieline
    d = dieline.extract(pdf)
    p = riconosci(d)
    if p is not None:
        return pdf, d, p, 0, None
    for giro in (90, 270):
        girato = artwork.pagina_girata(pdf, giro)
        if girato == pdf:
            break
        d2 = dieline.extract(girato)
        p2 = riconosci(d2)
        if p2 is not None:
            return girato, d2, p2, giro, (
                "foglio girato di %d gradi: sulla tavola il display stava di "
                "traverso" % giro)
    return pdf, d, None, 0, None


def dichiara(p):
    """Le righe che dicono cosa si e' riconosciuto, per chi guarda il modello."""
    x0, y0, x1, y1 = p.fondo
    davanti, dorso, dietro = p.parti_coperchio
    alt = p.pareti
    if p.cerniera == "retro":
        return [
            "display con plancia, coperchio sul retro",
            "fondo %.1f x %.1f mm, pareti %s mm"
            % ((x1 - x0) * PT2MM, (y1 - y0) * PT2MM,
               " / ".join("%s %.1f" % (k, a) for k, a in alt.items())),
            "aperto a espositore: il fronte e' la testata bassa, il coperchio "
            "alzato sul retro e ripiegato in avanti sulla riga che lo "
            "attraversa",
            "plancia alta %.1f mm sopra il retro, piu' la linguetta: davanti "
            "la parte oltre la riga (%.1f mm, il piede entra %.1f mm nella "
            "scatola), dietro quella attaccata al retro"
            % (dietro, davanti, davanti - dietro),
        ] + list(p.warnings)
    fx0, fy0, fx1, fy1 = p.finestra
    return [
        "display con plancia",
        "fondo %.1f x %.1f mm, pareti %s mm"
        % ((x1 - x0) * PT2MM, (y1 - y0) * PT2MM,
           " / ".join("%s %.1f" % (k, a) for k, a in alt.items())),
        "aperto a espositore: la finestra del fronte (%.1f x %.1f mm) "
        "strappata via, il coperchio staccato dal fianco %s e alzato sul "
        "retro, ripiegato sulla doppia cordonatura (%.1f mm fra le righe)"
        % ((fx1 - fx0) * PT2MM, (fy1 - fy0) * PT2MM, p.lato_coperchio, dorso),
        "plancia alta %.1f mm sopra il retro, piu' la cresta dell'onda: davanti "
        "la parte del coperchio che stava sul fronte (%.1f mm, il piede entra "
        "%.1f mm nella scatola), dietro quella che stava sul retro"
        % (dietro, davanti, davanti - dietro),
    ] + list(p.warnings)


# --------------------------------------------------------------------------- #
# i pezzi, dai tratti della fustella
# --------------------------------------------------------------------------- #
# Il margine attorno alla fustella, sulla griglia dei pezzi e sulla texture.
MARGINE = 2.0 * MM
# Lo spessore con cui si disegnano i tratti, in pixel: chiude i buchi piu'
# piccoli di mezzo millimetro fra un pezzo di riga e l'altro.
TRATTO_PX = 3


def _spiana(path):
    """Un tracciato di pdfplumber (`m`, `l`, `c`, `h`) in spezzate di punti."""
    out, cur, inizio = [], None, None
    for cmd in path:
        op = cmd[0]
        if op == "m":
            if cur and len(cur) > 1:
                out.append(cur)
            cur, inizio = [tuple(cmd[1])], tuple(cmd[1])
        elif op == "l" and cur is not None:
            cur.append(tuple(cmd[1]))
        elif op == "c" and cur is not None:
            p0 = cur[-1]
            p1, p2, p3 = (tuple(q) for q in cmd[1:4])
            lung = (math.dist(p0, p1) + math.dist(p1, p2) + math.dist(p2, p3))
            n = max(4, int(math.ceil(lung / 1.5)))
            for k in range(1, n + 1):
                t = k / n
                u = 1.0 - t
                cur.append(tuple(u * u * u * a + 3 * u * u * t * b
                                 + 3 * u * t * t * c + t * t * t * e
                                 for a, b, c, e in zip(p0, p1, p2, p3)))
        elif op == "h" and cur is not None and inizio is not None:
            cur.append(inizio)
    if cur and len(cur) > 1:
        out.append(cur)
    return out


def tratti(pdf, riquadro, page_no=0):
    """I tratti della fustella come spezzate, in punti con la y dall'alto.

    Linee, lati dei rettangoli e CURVE spianate: la griglia di `riconosci` si
    fa con i soli tratti dritti, ma la finestra e l'onda del coperchio sono
    curve, e da li' passano i tagli che fanno i pezzi. La penna e' quella che
    sceglie `dieline.extract`, e si tiene solo quello che sta nel riquadro
    della fustella: fuori ci sono quote, miniature e cartiglio.
    """
    import pdfplumber
    from . import dieline as dl

    x0, y0, x1, y1 = riquadro
    tol = 3.0
    dentro = lambda x, y: x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol
    out = []
    with pdfplumber.open(pdf) as doc:
        page = doc.pages[page_no]
        tutti = dl._segments(page)
        penne = dl._technical_pens(tutti, page.width, page.height)
        segs = [s for s in tutti if s[4] in penne] or tutti
        segs = dl._largest_cluster(segs)
        fustella = (dl.penne_di_fustella(segs, page.width, page.height)
                    or {s[4] for s in segs})
        for kind in ("line", "rect", "curve"):
            for o in page.objects.get(kind, []):
                if not o.get("stroke"):
                    continue
                st = (round(o.get("linewidth") or 0, 2), str(o.get("stroking_color")))
                if st not in fustella:
                    continue
                if kind == "rect":
                    a, b, c, e = o["x0"], o["top"], o["x1"], o["bottom"]
                    linee = [[(a, b), (c, b), (c, e), (a, e), (a, b)]]
                elif o.get("path"):
                    linee = _spiana(o["path"])
                else:
                    linee = [[tuple(q) for q in (o.get("pts") or [])]]
                for linea in linee:
                    if len(linea) > 1 and all(dentro(x, y) for x, y in linea):
                        out.append(linea)
    return out


@dataclass
class Pezzi:
    """Le maschere dei pezzi sulla griglia della sagoma, e la griglia stessa.

    La griglia copre il riquadro della fustella piu' `MARGINE`, e la texture
    si rende sullo STESSO riquadro: cosi' le UV sono la posizione sulla griglia
    divisa per la sua misura, come nel vassoio.
    """
    maschere: dict            # nome -> array bool (H, W)
    righe: dict               # le righe della plancia, in pixel della griglia
    origine: tuple            # (x, y) in punti: l'angolo in alto a sinistra
    scala: float              # pixel per punto
    lato: tuple               # (W, H)

    def riquadro(self):
        """Il riquadro in punti che la griglia copre: e' quello della texture."""
        W, H = self.lato
        ox, oy = self.origine
        return (ox, oy, ox + W / self.scala, oy + H / self.scala)


def _al_piu_vicino(tratto, lab):
    """Ogni pixel del tratto alla zona piu' vicina; a pari distanza, alla piu'
    grande.

    `distance_transform_edt`, a pari distanza, sceglie sempre dalla stessa
    parte della griglia. E la riga di mezzo di un tratto largo tre pixel e' a
    pari distanza dai due pezzi che divide: col foglio capovolto passava al
    pezzo di fronte, e sul Tronky la cresta della plancia saliva di un pixel.
    Si guarda anche la griglia capovolta: dove le due scelte non coincidono e'
    un pari merito, e vince la zona piu' grande, che e' la stessa comunque stia
    il foglio.
    """
    import numpy as np
    from scipy.ndimage import distance_transform_edt

    _d, (iy, ix) = distance_transform_edt(tratto, return_indices=True)
    a = lab[iy, ix]
    _d, (iy, ix) = distance_transform_edt(tratto[::-1, ::-1],
                                          return_indices=True)
    b = lab[::-1, ::-1][iy, ix][::-1, ::-1]
    quante = np.bincount(lab.ravel())
    return np.where(quante[a] >= quante[b], a, b)


def pezzi(pdf, p, d, px_mm=4.0, page_no=0):
    """Le maschere dei pezzi del display, da ritagliare e piegare.

    La sagoma NON viene dall'impronta di stampa, come nel vassoio: le falde di
    questo display non sono stampate e l'impronta non le vede, e i tagli che
    contano - la finestra, l'onda - stanno in mezzo alla stampa, che ci passa
    sopra senza interrompersi. Viene dai TRATTI della fustella: si disegnano, e
    ogni zona chiusa fra un tratto e l'altro e' un pezzo di cartone; quella
    che tocca il bordo e' il foglio attorno. I pixel del tratto vanno al pezzo
    piu' vicino, cosi' due pezzi che si toccano non lasciano la fessura.
    """
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy.ndimage import binary_dilation, label

    scala = px_mm * 25.4 / 72.0
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
    lab, _n = label(~tratto)
    zone = _al_piu_vicino(tratto, lab)
    bordo = np.unique(np.concatenate([zone[0], zone[-1], zone[:, 0], zone[:, -1]]))
    sagoma = ~np.isin(zone, bordo)

    P = lambda x: int(round((x - ox) * scala))
    Q = lambda y: int(round((y - oy) * scala))
    quante = np.bincount(zone.ravel())

    def rett(x0, y0, x1, y1):
        """Il cartone nel riquadro, a zone intere.

        Una zona che sta per lo piu' FUORI dal riquadro e' di un pezzo accanto:
        il tratto che li divide l'ha dato a lei, e il riquadro, che cade sulla
        riga, se ne prendeva un filo. Sul Tronky l'aletta nord-est si portava
        dietro il bordo destro di tutto il fronte, un pixel per 116 mm.
        """
        m = np.zeros((H, W), bool)
        m[max(Q(y0), 0):max(Q(y1), 0), max(P(x0), 0):max(P(x1), 0)] = True
        m &= sagoma
        z, dentro = np.unique(zone[m], return_counts=True)
        return m & np.isin(zone, z[dentro * 2 >= quante[z]])

    def zona(x, y):
        """L'etichetta della zona in (x, y) punti."""
        return int(zone[min(max(Q(y), 0), H - 1), min(max(P(x), 0), W - 1)])

    fx0, fy0, fx1, fy1 = p.fondo
    b = p.bordi
    ya, yb = p.fianchi
    top, bot = oy, oy + H / scala
    m = {
        "fondo": rett(fx0, fy0, fx1, fy1),
        "ovest": rett(b["ovest"], ya, fx0, yb),
        "est": rett(fx1, ya, b["est"], yb),
        "nord": rett(fx0, b["nord"], fx1, fy0),
        "sud": rett(fx0, fy1, fx1, b["sud"]),
        "aletta nord-ovest": rett(b["ovest"], top, fx0, ya),
        "aletta nord-est": rett(fx1, top, b["est"], ya),
        "aletta sud-ovest": rett(b["ovest"], yb, fx0, bot),
        "aletta sud-est": rett(fx1, yb, b["est"], bot),
    }

    righe = {
        "fondo": (P(fx0), P(fx1), Q(fy0), Q(fy1)),
        "bordi": {"ovest": P(b["ovest"]), "est": P(b["est"]),
                  "nord": Q(b["nord"]), "sud": Q(b["sud"])},
        "fianchi": (Q(ya), Q(yb)),
        "pieghe": (Q(p.pieghe[0]), Q(p.pieghe[1])),
    }
    cx0, cy0, cx1, cy1 = p.coperchio
    righe["coperchio"] = (P(cx0), Q(cy0), P(cx1), Q(cy1))
    if p.cerniera == "retro":
        _coperchio_sul_retro(m, p, tratto, rett(cx0, cy0, cx1, cy1), P, Q,
                             px_mm)
        return Pezzi(maschere=m, righe=righe, origine=(ox, oy), scala=scala,
                     lato=(W, H))

    # La finestra: la zona che sta sotto il bordo alto del fronte, a meta'
    # della finestra, e con lei le zone che la toccano e ci stanno dentro - il
    # mezzo tondo per il dito, che senza la finestra resta un buco.
    wx0, wy0, wx1, wy1 = p.finestra
    bordo_f = b[p.fronte]
    dentro_f = 3.0 * MM if p.fronte == "nord" else -3.0 * MM
    fin = zona((wx0 + wx1) / 2.0, bordo_f + dentro_f)
    finestra = zone == fin
    ys, xs = np.nonzero(finestra)
    if not len(xs):
        raise ValueError("display con plancia: la finestra del fronte non si "
                         "chiude sui tratti della fustella")
    tol = int(math.ceil(1.0 * px_mm))
    r0, r1 = ys.min() - tol, ys.max() + tol
    c0, c1 = xs.min() - tol, xs.max() + tol
    vicine = binary_dilation(finestra, iterations=TRATTO_PX + 1)
    for z in np.unique(zone[vicine]):
        if z == fin or z in bordo:
            continue
        zy, zx = np.nonzero(zone == z)
        if zy.min() >= r0 and zy.max() <= r1 and zx.min() >= c0 and zx.max() <= c1:
            finestra |= zone == z
    if (m["fondo"] & finestra).any():
        raise ValueError("display con plancia: la finestra del fronte arriva "
                         "fino al fondo, il suo contorno non si chiude")
    m[p.fronte] &= ~finestra

    # Il coperchio: la parte davanti, quella dietro, e fra le due il dorso,
    # che sono le strisce fra le due righe della doppia cordonatura.
    xm = (cx0 + cx1) / 2.0
    sopra, sotto = zona(xm, cy0 + 3.0 * MM), zona(xm, cy1 - 3.0 * MM)
    if sopra == sotto:
        raise ValueError("display con plancia: il taglio a onda non separa le "
                         "due parti del coperchio")
    cop = rett(cx0, cy0, cx1, cy1)
    nord_c, sud_c = cop & (zone == sopra), cop & (zone == sotto)
    davanti, dietro = (nord_c, sud_c) if p.fronte == "nord" else (sud_c, nord_c)
    m["plancia davanti"] = davanti
    m["plancia dietro"] = dietro
    m["plancia dorso"] = cop & ~nord_c & ~sud_c
    return Pezzi(maschere=m, righe=righe, origine=(ox, oy), scala=scala,
                 lato=(W, H))


def _coperchio_sul_retro(m, p, tratto, cop, P, Q, px_mm):
    """Le due parti del coperchio sul retro, in `m`: davanti e dietro.

    La riga le divide ai lati, ma in mezzo la linguetta - che e' della parte
    davanti - si stacca dalla parte dietro su un contorno PERFORATO: sui
    tratti cosi' come sono le due parti sono una zona sola. Si chiudono i
    tratti di `CHIUDI` per lato, quanto basta a chiudere la perforazione e i
    punti di tenuta, e la parte davanti e' la zona chiusa oltre la riga, con
    dentro la linguetta. Il resto del coperchio e' la parte dietro, col buco
    della linguetta.
    """
    import numpy as np
    from scipy.ndimage import binary_dilation, label

    chiuso = binary_dilation(tratto, iterations=max(1, int(round(CHIUDI * px_mm))))
    lab, _n = label(~chiuso)
    zone = _al_piu_vicino(chiuso, lab)
    cx0, cy0, cx1, cy1 = p.coperchio
    piega = p.pieghe[0]
    verso = +1 if p.retro == "sud" else -1     # dalla cerniera verso il bordo
    H, W = zone.shape

    def zona(x, y):
        return int(zone[min(max(Q(y), 0), H - 1), min(max(P(x), 0), W - 1)])

    xm = (cx0 + cx1) / 2.0
    oltre = zona(xm, piega + verso * 5.0 * MM)
    # la parte dietro si cerca accanto a un lato, dove non c'e' la linguetta
    x_lato = cx0 + 0.05 * (cx1 - cx0)
    if zona(x_lato, piega - verso * 5.0 * MM) == oltre:
        raise ValueError("display con plancia: la riga del coperchio non ne "
                         "separa le due parti")
    davanti = cop & (zone == oltre)
    m["plancia davanti"] = davanti
    m["plancia dietro"] = cop & ~davanti
    m["plancia dorso"] = np.zeros_like(cop)


# --------------------------------------------------------------------------- #
# la maglia del display aperto
# --------------------------------------------------------------------------- #
def mesh(p, pz, px_mm, spessore=SPESSORE, alt_texture=None, parti=None):
    """La maglia del display APERTO: vertici, UV sullo steso, triangoli.

    Il vassoio - fondo, pareti, alette - e' il BLOCCO di `vassoio.corpo`,
    senza feritoie, col fronte senza la finestra che e' stata strappata via.

    La plancia e' il coperchio, alzato sul retro e ripiegato, ed e' un
    elemento a se': sta in piedi sul retro, non e' incollata al blocco. Detto
    `t` quanto un punto del coperchio dista dal bordo che sta sulla cerniera
    del retro:

      - la parte DIETRO sta in piedi sul retro, nel suo piano, con la stampa
        verso fuori: altezza = retro + t;
      - il DORSO e' orizzontale in cima: la stessa altezza, e avanza verso il
        fronte di quanto e' largo, 8,1 mm sul Tronky;
      - la parte DAVANTI scende dal dorso con la stampa verso chi guarda. La
        cresta - l'onda, che sta oltre la piega - viene fuori sopra la cima,
        e il piede, piu' lungo della parte dietro, finisce dentro la scatola.

    Anche qui ogni pezzo si ancora alla sua piega, come nel blocco: la cima
    e' dove finisce la parte dietro, il dorso parte dal suo piano, e la parte
    davanti dal bordo del dorso. Presi dalla griglia di pixel, fra una parte
    e l'altra restava un quarto di millimetro.

    Il coperchio attraversa la scatola come quando era chiuso: il suo lato
    sulla cerniera del fianco va sopra quel fianco, e l'altro sopra l'altro.
    Se il fronte e' la parete sud, alla fine il display si gira di mezzo giro
    perche' guardi davanti, come il vassoio con la testata bassa a sud.
    """
    import numpy as np

    from .vassoio import _ingombro, _stira, corpo

    H, W = pz.maschere["fondo"].shape
    r = pz.righe
    maglia = Maglia(W, H, spessore, alt_texture, parti)
    mk = pz.maschere
    # il blocco sulle misure del DT, non sui pixel: vedi `corpo`
    fx0, fy0, fx1, fy1 = p.fondo
    telaio = corpo(maglia, mk, r["fondo"], px_mm, spessore, alte=p.pareti,
                   fondo_mm=((fx1 - fx0) * PT2MM, (fy1 - fy0) * PT2MM))
    xL, xR = telaio["xL"], telaio["xR"]
    if p.cerniera == "retro":
        _plancia_sul_retro(maglia, p, pz, telaio, spessore)
        V, UV, T = maglia.array()
        if p.fronte == "sud":
            V = gira(V)
        return V, UV, T

    # La plancia. `sgn` dice da che parte del foglio sta il retro: +1 se e' la
    # parete sud, e allora la cerniera e' l'ultima riga della parte dietro.
    davanti, dorso, dietro = (mk["plancia davanti"], mk["plancia dorso"],
                              mk["plancia dietro"])
    e_b, e_s = _ingombro(dietro, "colonne"), _ingombro(dorso, "righe")
    if e_b is None or e_s is None:
        raise ValueError("display con plancia: il coperchio non si divide in "
                         "parte davanti, dorso e parte dietro")
    sgn = 1 if p.retro == "sud" else -1
    z_r = telaio["zB"] if sgn > 0 else telaio["zT"]
    o = -1.0 if sgn > 0 else 1.0          # il verso di fuori del retro, in z
    base = telaio["alt"][p.retro]
    # fin dove arrivano le loro maglie, vedi `vassoio._ingombro`: la parte
    # dietro e' stesa per colonne, il dorso per righe
    rb0, rb1 = e_b[0], e_b[1]
    rs0, rs1 = e_s[0], e_s[1]
    cerniera, piega_b = (rb1, rb0) if sgn > 0 else (rb0, rb1)
    dietro_s, davanti_s = (rs1, rs0) if sgn > 0 else (rs0, rs1)
    # Le lunghezze vere, dal DT e non dai pixel: la parte dietro dalla
    # cerniera alla piega, il dorso fra le due righe, la parte davanti dalla
    # piega al bordo. Ogni pezzo si stira fra le sue due righe su quella
    # lunghezza, cosi' si attacca al vicino e la plancia esce uguale comunque
    # stia il foglio sulla tavola: prese dai pixel, la cima ballava di mezzo
    # millimetro fra un verso e l'altro.
    davanti_mm, dorso_mm, dietro_mm = p.parti_coperchio
    avanti = -o                              # verso il fronte, in z
    cima = base + dietro_mm
    z_a = z_r + avanti * dorso_mm
    h_b = _stira(cerniera, piega_b, base, cima)
    z_s = _stira(dietro_s, davanti_s, z_r, z_a)
    # La piega della parte davanti e' la riga dove lei e il dorso si toccano
    # PIU' A LUNGO. Non la sua ultima riga sopra il dorso: fra le due pieghe
    # l'onda tocca il dorso anche lei, di sbieco, e arriva fino all'altra
    # piega - ancorata li' la plancia scendeva di 8 mm, e la cresta con lei.
    sotto = np.zeros_like(davanti)
    if sgn > 0:
        sotto[:-1] = davanti[:-1] & dorso[1:]
    else:
        sotto[1:] = davanti[1:] & dorso[:-1]
    contatti = sotto.sum(1)
    if not contatti.any():
        raise ValueError("display con plancia: la parte davanti non tocca il "
                         "dorso")
    piega_a = int(np.argmax(contatti)) + (1 if sgn > 0 else 0)
    e_a = _ingombro(davanti, "colonne")
    piede = e_a[0] if sgn > 0 else e_a[1]
    h_a = _stira(piega_a, piede, cima, cima - davanti_mm)
    # In larghezza i tre pezzi si stirano sulla larghezza del coperchio, dal
    # fianco della cerniera all'altro: cosi' i lati della plancia combaciano,
    # anche se uno e' steso per righe e gli altri per colonne.
    largo = (p.coperchio[2] - p.coperchio[0]) * PT2MM
    x_h, x_f = (xR, xR - largo) if p.lato_coperchio == "est" else (xL, xL + largo)

    def xc(masc, verso):
        c0, c1 = _ingombro(masc, verso)[2:]
        if p.lato_coperchio == "est":
            return _stira(c0, c1, x_h, x_f)
        return _stira(c0, c1, x_f, x_h)

    xb, xs = xc(dietro, "colonne"), xc(dorso, "righe")
    xa = xc(davanti, "colonne")
    pezzo = maglia.pezzo
    pezzo(dietro, "colonne", lambda X, Y: (xb(X), h_b(Y), z_r),
          (0, 0, -o), [("Y", piega_b)], "plancia dietro")
    pezzo(dorso, "righe", lambda X, Y: (xs(X), cima, z_s(Y)), (0, -1, 0),
          [("Y", dietro_s), ("Y", davanti_s)], "plancia dorso")
    pezzo(davanti, "colonne", lambda X, Y: (xa(X), h_a(Y), z_a),
          (0, 0, o), [("Y", piega_a)], "plancia davanti")

    V, UV, T = maglia.array()
    if p.fronte == "sud":
        V = gira(V)
    return V, UV, T


def _plancia_sul_retro(maglia, p, pz, telaio, spessore):
    """La plancia del coperchio sul retro: vedi in cima al modulo.

    La parte dietro sta in piedi sul retro, nel suo piano, con la stampa
    verso dietro: dalla cerniera, all'altezza del retro, alla riga. La parte
    davanti scende dalla riga con la stampa verso chi guarda, uno spessore
    davanti alla parte dietro - la piega a 180 gradi di un cartone sottile,
    il dorso del Tronky largo uno spessore - e la linguetta, che sul foglio
    sta oltre la riga, spunta sopra come cresta. In larghezza il coperchio
    sta dove sta sul foglio rispetto al fondo: continua il retro.
    """
    from .vassoio import _ingombro, _stira

    mk, r = pz.maschere, pz.righe
    davanti, dietro = mk["plancia davanti"], mk["plancia dietro"]
    e_b, e_a = _ingombro(dietro, "colonne"), _ingombro(davanti, "colonne")
    if e_b is None or e_a is None:
        raise ValueError("display con plancia: il coperchio non si divide in "
                         "parte davanti e parte dietro")
    sgn = 1 if p.retro == "sud" else -1
    z_r = telaio["zB"] if sgn > 0 else telaio["zT"]
    o = -1.0 if sgn > 0 else 1.0          # il verso di fuori del retro, in z
    base = telaio["alt"][p.retro]
    davanti_mm, _dorso, dietro_mm = p.parti_coperchio
    cima = base + dietro_mm
    z_a = z_r - o * 2.0 * spessore
    cerniera, piega_b = (e_b[0], e_b[1]) if sgn > 0 else (e_b[1], e_b[0])
    h_b = _stira(cerniera, piega_b, base, cima)
    piega_a = r["pieghe"][0]
    piede = e_a[1] if sgn > 0 else e_a[0]
    h_a = _stira(piega_a, piede, cima, cima - davanti_mm)
    c0, c1 = r["fondo"][0], r["fondo"][1]
    fx = _stira(c0, c1, telaio["xL"], telaio["xR"])
    # Le righe sulla piega NON sono pieghe per `pezzo`: le due parti stanno
    # su due piani, e la cima di ognuna e' un taglio con la sua costa.
    maglia.pezzo(dietro, "colonne", lambda X, Y: (fx(X), h_b(Y), z_r),
                 (0, 0, -o), [], "plancia dietro")
    maglia.pezzo(davanti, "colonne", lambda X, Y: (fx(X), h_a(Y), z_a),
                 (0, 0, o), [], "plancia davanti")
