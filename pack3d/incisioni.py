"""
Le incisioni: i tagli della fustella che stanno DENTRO le facce di un astuccio
chiuso, modellati come sono sul cartone.

Il primo e' il T5 a strappo "with frontal opening": sul fronte c'e'
una finestra che si apre a strappo. Chi la guarda chiusa, in mano, ne vede i
tagli - due lati e due diagonali, la linguetta che gira sotto il fondo, la
mezzaluna per il dito - e il modello li deve far vedere allo stesso modo: come
SOLCHI nella faccia, che la luce fa leggere, non come righe disegnate sopra la
grafica. La grafica resta quella del file, intera: il taglio sul cartone non
e' stampato.

Quali tagli, lo dice la fustella:

- sono tratti della penna del disegno tecnico (`dieline._technical_pens`) che
  stanno dentro un pannello di una faccia del solido, non sul suo bordo: il
  bordo e' una piega o il contorno;
- un rettangolo chiuso dentro un pannello non e' un taglio, e' il riquadro di
  un'area (scadenza, codice a barre, vernice): lo spegne gia' la pulizia;
- un tratto con le SPUNTE - trattini corti che lo attraversano a intervalli -
  e' il taglio parziale dal rovescio: nella legenda dei disegni cliente e'
  proprio la riga con le stanghette. Sta sulla faccia interna del cartone e da
  fuori non si vede: non si incide;
- le spunte stesse non sono tagli.

Il resto si incide: un solco a V largo `LARGHEZZA` e profondo `PROFONDITA`,
mai piu' di meta' dello spessore del cartoncino.

Il solco tiene la grafica: le sue pareti hanno la texture della faccia, con le
stesse coordinate, e il taglio si legge dall'ombra, non da un colore. Col
solco nella tinta della costa (`folding.TAGLIO`) la finestra a strappo del
T2x25 Kinder Cards (caso 88976a700d) usciva contornata da un filetto bianco
sopra la grafica, e chi l'ha caricato l'ha respinta: sul cartone stampato la
perforazione non si vede bianca. La costa resta della tinta del cartoncino
solo dove il taglio si apre (`apertura`).
"""
from __future__ import annotations

import math

import numpy as np

from .dieline import PT2MM

MM = 1.0 / PT2MM          # punti in un millimetro

# Il solco, in mm: quanto e' largo in superficie e quanto scende. Su un
# astuccio da 168 mm, a schermo pieno un millimetro sono cinque pixel: un solco
# di tre decimi si legge come il filo di un taglio, e da vicino e' un taglio.
LARGHEZZA = 0.35
PROFONDITA = 0.22
# Ogni quanto si campiona il solco lungo il taglio, in mm. Piu' fitto della
# larghezza: cosi' la triangolazione non scavalca mai il solco.
PASSO = 0.15
# Una spunta: un tratto piu' corto di cosi' che ne attraversa un altro.
SPUNTA = 2.6 * MM
# Quante spunte fanno di un tratto un taglio dal rovescio.
SPUNTE_MIN = 2
# Due estremi piu' vicini di cosi', in punti, sono lo stesso punto.
CUCI = 0.3
# Quanto dentro il pannello deve stare un tratto per non essere il suo bordo.
DENTRO = 0.6
# Un taglio piu' corto di cosi', in mm, non si incide.
CORTO = 1.0
# Per quanti mm un taglio deve correre accanto a quello dal rovescio per
# essere il bordo di un'apertura a strappo, e quanto lontano da un'apertura
# puo' stare un taglio che le appartiene (la mezzaluna per il dito).
ACCANTO = 10.0
VICINO = 3.0
# La seconda firma, la PERFORAZIONE: una fila di trattini - sul T10 al lampone 13 mm
# di taglio e 1,7 di ponticello - che parte da una piega, gira attorno alla
# finestra e torna sulla stessa piega. Il ponticello piu' lungo fra due
# trattini, in mm; quanti ponticelli almeno; quanto e' lunga almeno, in mm;
# e di quanti gradi al piu' gira la fila da un trattino al successivo.
PONTE = 2.5
PONTI_MIN = 8
PERFORATA_MIN = 80.0
SVOLTA = 60.0
# la cerniera minima di un contorno chiuso sul lato (`_chiusa_sul_lato`), mm
CERNIERA_MIN = 20.0
# La linguetta di chiusura: il taglio del bordo libero di una faccia che
# entra nella faccia - le due tacche e il lobo fra loro - almeno di tanti mm.
# Meno e' il bordo stesso, appena storto (i lati obliqui di una falda).
LINGUETTA_MIN = 2.0


def _tratti_tecnici(pdf, page_no=0, curve=False):
    """I sottopercorsi della penna del disegno tecnico: liste di punti, in
    punti PDF col telaio della MediaBox (y dall'alto), come `tracciati`. Con
    `curve` i tratti di Bezier sono campionati sulla curva
    (`tracciati._cammina`)."""
    import pypdfium2 as pdfium
    from . import dieline, strati, tracciati

    segs, larga, alta = tracciati.segmenti(pdf, page_no)
    penne = set(dieline._technical_pens(segs, larga, alta))
    # e quelle disegnate a pezzi corti (`strati._penne_a_pezzi`): col DT in
    # pezzi di 3 mm la perforazione dello strappo non stava piu' su una penna
    # tecnica, e l'astuccio chiesto aperto usciva chiuso
    penne |= strati._penne_a_pezzi(segs, larga, alta, penne)
    if not penne:
        return []
    doc = pdfium.PdfDocument(pdf)
    try:
        page = doc[page_no]
        pieni, tratti = [], []
        tracciati._cammina(page, pieni, tratti, curve=curve)
    finally:
        doc.close()
    out = []
    for sp, r, st in tratti:
        if st not in penne or r is not None:
            continue            # un rettangolo chiuso e' il riquadro di un'area
        punti = [(float(x), float(y)) for x, y in sp]
        if len(punti) >= 2:
            out.append(punti)
    return out


def _segmenti(percorsi):
    """I tratti come segmenti ((x0, y0), (x1, y1)), senza quelli nulli."""
    out = []
    for p in percorsi:
        for a, b in zip(p, p[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.05:
                out.append((a, b))
    return out


def _dentro_pannello(seg, p):
    """La parte di `seg` dentro il pannello `p`, o None: il bordo non conta.

    Liang-Barsky sul riquadro stretto di DENTRO: un tratto che corre lungo il
    bordo - la piega fra due facce - ne esce tutto; uno che parte dal bordo e
    scende dentro la faccia - il lato della finestra - perde il primo mezzo
    millimetro, che si rimette allungandolo fino al bordo vero.
    """
    (x0, y0), (x1, y1) = seg
    lo = [p.x0 + DENTRO, p.y0 + DENTRO]
    hi = [p.x1 - DENTRO, p.y1 - DENTRO]
    d = (x1 - x0, y1 - y0)
    t0, t1 = 0.0, 1.0
    for k, (o, dk) in enumerate(((x0, d[0]), (y0, d[1]))):
        if abs(dk) < 1e-12:
            if o < lo[k] or o > hi[k]:
                return None
            continue
        a, b = (lo[k] - o) / dk, (hi[k] - o) / dk
        if a > b:
            a, b = b, a
        t0, t1 = max(t0, a), min(t1, b)
        if t0 >= t1:
            return None
    pa = (x0 + d[0] * t0, y0 + d[1] * t0)
    pb = (x0 + d[0] * t1, y0 + d[1] * t1)
    return _al_bordo(pa, d, p, -1 if t0 > 0 else 0), _al_bordo(pb, d, p, 1 if t1 < 1 else 0)


def _al_bordo(q, d, p, verso):
    """`q` spinto lungo `d` fino al bordo vero del pannello, se il segmento ci
    arrivava (verso -1 all'indietro, 1 in avanti, 0 resta dov'e')."""
    if not verso:
        return q
    lung = math.hypot(*d)
    ux, uy = d[0] / lung * verso, d[1] / lung * verso
    passi = []
    for o, u, a, b in ((q[0], ux, p.x0, p.x1), (q[1], uy, p.y0, p.y1)):
        if abs(u) > 1e-9:
            passi.append(((b if u > 0 else a) - o) / u)
    t = min([s for s in passi if s >= 0] or [0.0])
    t = min(t, DENTRO * 1.5)
    return (q[0] + ux * t, q[1] + uy * t)


def _catene(segmenti):
    """I segmenti cuciti in linee: si cuce solo attraverso i punti in cui si
    incontrano due tratti e due soli. Un incrocio a tre - dove il taglio dal
    rovescio raggiunge quello davanti - spezza le linee, cosi' ognuna si
    giudica da se'."""
    nodi, idx = [], {}

    def nodo(q):
        k = (round(q[0] / CUCI), round(q[1] / CUCI))
        for dk in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (1, -1), (-1, 1), (-1, -1)):
            j = idx.get((k[0] + dk[0], k[1] + dk[1]))
            if j is not None and math.hypot(nodi[j][0] - q[0], nodi[j][1] - q[1]) <= CUCI:
                return j
        idx[k] = len(nodi)
        nodi.append(q)
        return len(nodi) - 1

    archi = [(nodo(a), nodo(b)) for a, b in segmenti]
    vicini = {}
    for k, (i, j) in enumerate(archi):
        if i == j:
            continue
        vicini.setdefault(i, []).append((k, j))
        vicini.setdefault(j, []).append((k, i))
    usati = set()
    linee = []

    def segui(i, k, j):
        linea = [nodi[i], nodi[j]]
        usati.add(k)
        while len(vicini.get(j, ())) == 2:
            prossimi = [(kk, jj) for kk, jj in vicini[j] if kk not in usati]
            if not prossimi:
                break
            k, jj = prossimi[0]
            usati.add(k)
            linea.append(nodi[jj])
            j = jj
        return linea

    for i, vv in vicini.items():          # prima dagli estremi e dagli incroci
        if len(vv) != 2:
            for k, j in vv:
                if k not in usati:
                    linee.append(segui(i, k, j))
    for i, vv in vicini.items():          # poi gli anelli chiusi
        for k, j in vv:
            if k not in usati:
                linee.append(segui(i, k, j))
    return linee


def _lunghezza(linea):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(linea, linea[1:]))


def _attraversa(spunta, linea):
    """La spunta taglia la linea vicino alla sua meta', quasi di traverso."""
    (ax, ay), (bx, by) = spunta[0], spunta[-1]
    mx, my = (ax + bx) / 2, (ay + by) / 2
    du = (bx - ax, by - ay)
    ls = math.hypot(*du) or 1.0
    for (px, py), (qx, qy) in zip(linea, linea[1:]):
        dv = (qx - px, qy - py)
        lv = math.hypot(*dv)
        if lv < 1e-9:
            continue
        t = max(0.0, min(1.0, ((mx - px) * dv[0] + (my - py) * dv[1]) / lv ** 2))
        cx, cy = px + dv[0] * t, py + dv[1] * t
        if math.hypot(mx - cx, my - cy) > ls * 0.4:
            continue
        coseno = abs(du[0] * dv[0] + du[1] * dv[1]) / (ls * lv)
        if coseno < 0.5:                  # piu' di 60 gradi
            return True
    return False


def _tratti_per_penna(pdf, page_no=0):
    """{penna: [sottopercorso]} dei tratti sottili della pagina, come
    `_tratti_tecnici` ma con tutte le penne sottili non bianche e divisi per
    penna: il taglio a vista e quello dal rovescio di un'apertura possono
    stare su penne fuori dalle tecniche - sul T2x12 a strappo il verde e il
    viola da 0,6 - e si toccano agli angoli: cuciti insieme diventavano un
    taglio dal rovescio solo, e l'apertura non si trovava."""
    import pypdfium2 as pdfium
    from . import dieline, tracciati

    segs, larga, alta = tracciati.segmenti(pdf, page_no)
    penne = dieline._technical_pens(segs, larga, alta)
    penne |= {s[4] for s in segs if s[4][0] <= 1.2 and s[4][1] != "(255, 255, 255)"}
    if not penne:
        return {}
    doc = pdfium.PdfDocument(pdf)
    try:
        page = doc[page_no]
        pieni, tratti = [], []
        tracciati._cammina(page, pieni, tratti)
    finally:
        doc.close()
    out = {}
    for sp, r, st in tratti:
        if st not in penne or r is not None:
            continue
        punti = [(float(x), float(y)) for x, y in sp]
        if len(punti) >= 2:
            out.setdefault(st, []).append(punti)
    return out


def firma(pdf, panels, facce, page_no=0, larga=False):
    """(aperture, vicini, rovescio) dell'apertura a strappo, o None.

    `panels` sono i pannelli dell'astuccio risolto, `facce` i nomi di quelli
    che sul solido sono facce (non alette ne' lembi incollati). Tutto in punti
    PDF, sul foglio intero: `aperture` sono i gruppi di tagli sul lato
    stampato che hanno accanto il taglio dal rovescio, con quelli che li
    continuano; `vicini` i gruppi a un passo, come la mezzaluna per il dito;
    `rovescio` i tagli dal rovescio. Vedi `tagli` per come si riconosce.
    """
    # `larga`: con tutte le penne sottili, ognuna per se' (`_tratti_per_penna`);
    # si prova solo quando ne' la firma sulle penne tecniche ne' la
    # perforazione trovano l'apertura, cosi' i casi di prima non cambiano
    if larga:
        per_penna = _tratti_per_penna(pdf, page_no)
    else:
        tecnici = _tratti_tecnici(pdf, page_no)
        per_penna = {None: tecnici} if tecnici else {}
    if not per_penna:
        return None
    quadri = [panels[n] for n in facce if n in panels]
    if not quadri:
        return None
    # i tratti che stanno dentro almeno una faccia, interi: le linee si cuciono
    # sul foglio, attraverso le pieghe, e si tagliano alle facce solo alla
    # fine; ognuna con la sua penna
    linee, penna = [], {}
    for st, percorsi in per_penna.items():
        segmenti = [sg for sg in _segmenti(percorsi)
                    if any(_dentro_pannello(sg, p) is not None for p in quadri)]
        for l in _catene(segmenti):
            penna[id(l)] = st
            linee.append(l)
    if not linee:
        return None
    corta = [len(l) == 2 and _lunghezza(l) < SPUNTA for l in linee]
    spunte = [l for l, c in zip(linee, corta) if c]
    resto = [l for l, c in zip(linee, corta) if not c]
    rovescio = [l for l in resto
                if sum(1 for sp in spunte if _attraversa(sp, l)) >= SPUNTE_MIN]
    visibili = [l for l in resto if not any(l is r for r in rovescio)]
    if not rovescio or not visibili:
        return None
    gruppi = _gruppi(visibili)
    aperture = [g for g in gruppi if any(_accanto(l, rovescio) for l in g)]
    if not aperture:
        return None
    vicini = [g for g in gruppi if not any(g is a for a in aperture)
              and any(_distanza_gruppi(g, a) <= VICINO * MM for a in aperture)]
    # a un passo dall'apertura stanno anche le pieghe (che sono il bordo di
    # una faccia) e le quote: un vicino e' un taglio della penna dell'apertura,
    # dentro una faccia. Sul T2x12 l'apertura corre a 2 mm dalla piega del
    # cielo, e senza questo si incidevano le pieghe e la linea di una quota
    if larga:
        sue = {penna.get(id(l)) for g in aperture for l in g}
        vicini = [g for g in vicini
                  if all(penna.get(id(l)) in sue and not _di_bordo(l, quadri) for l in g)]
    return aperture, vicini, rovescio


def _di_bordo(linea, quadri, tol=1.0 * MM):
    """La linea corre tutta lungo un lato di un pannello: e' una piega."""
    for p in quadri:
        for (ax, ay), (bx, by) in (((p.x0, p.y0), (p.x1, p.y0)), ((p.x0, p.y1), (p.x1, p.y1)),
                                   ((p.x0, p.y0), (p.x0, p.y1)), ((p.x1, p.y0), (p.x1, p.y1))):
            if all(_distanza_punto(q, [(ax, ay), (bx, by)]) <= tol for q in linea):
                return True
    return False


def _sul_lato(q, quadri, tol=0.5 * MM):
    """(indice del pannello, lato) dei lati su cui sta il punto."""
    out = set()
    for k, p in enumerate(quadri):
        for lato, (a, b) in enumerate((((p.x0, p.y0), (p.x1, p.y0)), ((p.x0, p.y1), (p.x1, p.y1)),
                                       ((p.x0, p.y0), (p.x0, p.y1)), ((p.x1, p.y0), (p.x1, p.y1)))):
            if _distanza_punto(q, [a, b]) <= tol:
                out.add((k, lato))
    return out


def _direzione(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def perforata(pdf, panels, facce, page_no=0):
    """L'apertura a strappo PERFORATA, o None: {"catena": il contorno intero,
    i ponticelli colmati, in punti PDF; "pezzi": i trattini, come sono;
    "vicini": i tagli attaccati al contorno coi due capi, come la mezzaluna
    per il dito}.

    Sul T10 al lampone l'apertura non ha il taglio dal rovescio: e' una fila di
    trattini che parte dalla piega fra fronte e cielo, scende sui due lati,
    passa sul fondo e torna. La fila si segue di trattino in trattino - il
    prossimo e' quello il cui capo sta a meno di PONTE mm e che gira di meno -
    e vale come apertura solo se ha almeno PONTI_MIN ponticelli veri, e' lunga
    almeno PERFORATA_MIN mm e i due capi stanno sulla stessa piega: una riga
    tratteggiata qualunque dentro una faccia - il riquadro di un'area, una
    piega di servizio - non torna sulla piega da cui parte.
    """
    percorsi = _tratti_tecnici(pdf, page_no)
    quadri = [panels[n] for n in facce if n in panels]
    if not percorsi or not quadri:
        return None
    segmenti = [sg for sg in _segmenti(percorsi)
                if any(_dentro_pannello(sg, p) is not None for p in quadri)]
    pezzi = [l for l in _catene(segmenti) if not _di_bordo(l, quadri)]
    if len(pezzi) < PONTI_MIN:
        return None
    ponte = PONTE * MM

    def segui(i, capo):
        """La fila dal capo `capo` (0 o -1) del pezzo i, che sta su una piega."""
        primo = pezzi[i] if capo == 0 else pezzi[i][::-1]
        fila, usati, ponti = [primo], {i}, 0
        while True:
            q = fila[-1][-1]
            u = _direzione(fila[-1][-2], q)
            best = None
            for j, l in enumerate(pezzi):
                if j in usati:
                    continue
                for e in (0, -1):
                    d = math.hypot(l[e][0] - q[0], l[e][1] - q[1])
                    if d > ponte:
                        continue
                    m = l if e == 0 else l[::-1]
                    v = _direzione(m[0], m[1])
                    giro = math.degrees(math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1]))))
                    if giro > SVOLTA:
                        continue
                    if best is None or (giro, d) < best[0]:
                        best = ((giro, d), j, m, d)
            if best is None:
                return fila, usati, ponti
            _k, j, m, d = best
            usati.add(j)
            ponti += d > 0.5 * MM
            fila.append(m)

    migliore = None
    for i, l in enumerate(pezzi):
        for capo in (0, -1):
            lati = _sul_lato(l[capo], quadri)
            if not lati:
                continue
            fila, usati, ponti = segui(i, capo)
            fine = fila[-1][-1]
            lunga = sum(_lunghezza(m) for m in fila) * PT2MM
            if (ponti >= PONTI_MIN and lunga >= PERFORATA_MIN
                    and lati & _sul_lato(fine, quadri)
                    and (migliore is None or lunga > migliore[0])):
                migliore = (lunga, fila, usati)
    if migliore is None:
        return _perforata_continua(percorsi, pezzi, quadri)
    _lunga, fila, usati = migliore
    catena = list(fila[0])
    for m in fila[1:]:
        catena += m if math.hypot(m[0][0] - catena[-1][0], m[0][1] - catena[-1][1]) > CUCI else m[1:]
    vicini = [l for j, l in enumerate(pezzi) if j not in usati
              and _distanza_punto(l[0], catena) <= 1.5 and _distanza_punto(l[-1], catena) <= 1.5]
    return {"catena": catena, "pezzi": [list(m) for m in fila], "vicini": vicini}


def _perforata_continua(percorsi, pezzi, quadri, sul_lato=False):
    """La perforazione disegnata CONTINUA, senza trattini, o None: sul T2x25
    i due rami partono dalla piega fra cielo e fronte, scendono nel fronte e
    nella falda del fondo e si fermano a 1,5 mm dalle tacche della
    linguetta, la cui punta e' il taglio del bordo libero.

    Un RAMO e' una linea dentro le facce con un capo su una PIEGA - il lato
    comune a due facce, mai un bordo libero - e l'altro su nessun lato. Due rami che partono dallo stesso lato, in punti diversi, fanno il
    contorno se un tratto solo del disegno - la punta della linguetta,
    anche se esce dalla faccia - passa con due suoi vertici a meno di PONTE
    mm dai loro capi liberi, ed e' piu' corta di ciascun ramo; il contorno
    intero e' lungo almeno PERFORATA_MIN mm. Gli smussi agli angoli di una
    falda uniti dal contorno della fustella non sono rami e punta: la
    "punta" sarebbe tutto il bordo della falda, piu' lunga dei rami. Due righe qualunque che partono da una piega (i
    richiami di una quota) non hanno un tratto che le unisca capo a capo.
    I tagli che toccano il contorno coi due capi qui non contano: senza
    trattini a separarli, sono le quote disegnate sopra la finestra.
    """
    ponte = PONTE * MM
    rami = []
    for l in pezzi:
        for capo in (0, -1):
            lati = _sul_lato(l[capo], quadri)
            # il capo sta su una piega: sul lato di due facce
            if len({k for k, _l in lati}) >= 2 and not _sul_lato(l[-1 - capo], quadri):
                rami.append((lati, l if capo == 0 else l[::-1]))
    migliore = None
    for i, (la, a) in enumerate(rami):
        for lb, b in rami[i + 1:]:
            if not la & lb or math.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]) <= ponte:
                continue
            for s in percorsi:
                da = [math.hypot(q[0] - a[-1][0], q[1] - a[-1][1]) for q in s]
                db = [math.hypot(q[0] - b[-1][0], q[1] - b[-1][1]) for q in s]
                ia, ib = int(np.argmin(da)), int(np.argmin(db))
                if ia == ib or da[ia] > ponte or db[ib] > ponte:
                    continue
                punta = list(s[ia:ib + 1]) if ia < ib else list(s[ib:ia + 1])[::-1]
                if _lunghezza(punta) >= min(_lunghezza(a), _lunghezza(b)):
                    continue        # la punta e' il pezzo corto del contorno
                catena = list(a) + punta + list(b[::-1])
                lunga = _lunghezza(catena) * PT2MM
                if lunga >= PERFORATA_MIN and (migliore is None or lunga > migliore[0]):
                    migliore = (lunga, catena, [list(a), punta, list(b)])
            # `sul_lato` (`continua_per_penna`): senza una punta, i capi
            # liberi si chiudono lungo il lato della faccia a cui arrivano
            chiusura = _chiusa_sul_lato(a, b, la, quadri) if sul_lato else None
            if chiusura is not None:
                catena = list(a) + chiusura[1:-1] + list(b[::-1])
                lunga = _lunghezza(catena) * PT2MM
                if lunga >= PERFORATA_MIN and (migliore is None or lunga > migliore[0]):
                    migliore = (lunga, catena, [list(a), list(b)], chiusura)
    if migliore is None:
        return None
    _lunga, catena, linee = migliore[:3]
    out = {"catena": catena, "pezzi": linee, "vicini": []}
    if len(migliore) > 3:
        out["chiusura"] = migliore[3]
    return out


def _lati_quadri(p):
    return (((p.x0, p.y0), (p.x1, p.y0)), ((p.x0, p.y1), (p.x1, p.y1)),
            ((p.x0, p.y0), (p.x0, p.y1)), ((p.x1, p.y0), (p.x1, p.y1)))


def _chiusa_sul_lato(a, b, la, quadri):
    """Il tratto che chiude i due rami `a` e `b` lungo un lato di faccia, o
    None: i loro capi liberi stanno a meno di PONTE mm dallo stesso lato -
    non quello della piega da cui partono - e il tratto fra le due
    proiezioni e' piu' corto dei due rami insieme. E' il contorno che sul
    fronte finisce sulla piega con una falda che non e' una faccia: la
    linguetta gira li', e del solido la finestra arriva fino al lato."""
    ponte = PONTE * MM
    A, B = a[-1], b[-1]
    # la finestra va da una piega al lato opposto della stessa faccia, e la
    # cerniera e' una cerniera, non due tagli quasi attaccati: sul parco una
    # coppia di tratti a 5,5 mm sul fondo di un astuccio passava per apertura
    if math.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]) * PT2MM < CERNIERA_MIN:
        return None
    opposti = {(k, lato ^ 1) for k, lato in la}
    for k, p in enumerate(quadri):
        for lato, (u, v) in enumerate(_lati_quadri(p)):
            if (k, lato) not in opposti:
                continue
            if _distanza_punto(A, [u, v]) > ponte or _distanza_punto(B, [u, v]) > ponte:
                continue
            dx, dy = v[0] - u[0], v[1] - u[1]
            l2 = dx * dx + dy * dy
            if l2 < 1e-12:
                continue

            def su(q):
                t = max(0.0, min(1.0, ((q[0] - u[0]) * dx + (q[1] - u[1]) * dy) / l2))
                return (u[0] + dx * t, u[1] + dy * t)
            chiusura = [A, su(A), su(B), B]
            # piu' corto dei due rami insieme: sul T25 (caso ab4fa8dad8) la
            # finestra e' larga 162 mm e i rami lunghi 144, e la chiusura e'
            # piu' lunga di ciascuno
            if _lunghezza(chiusura) < _lunghezza(a) + _lunghezza(b):
                return chiusura
    return None


def continua_per_penna(pdf, panels, facce, page_no=0):
    """L'apertura a strappo disegnata CONTINUA su una penna sottile fuori
    dalle tecniche, o None: come `_perforata_continua`, ma penna per penna
    (`_tratti_per_penna`), e i due rami si chiudono anche lungo il lato della
    faccia a cui arrivano (`_chiusa_sul_lato`).

    Sull'astuccio di biscotti T10 (caso e88a907c54) il contorno e'
    verde da 0,55, senza ponticelli e senza taglio dal rovescio: due rami
    dalla piega fra cielo e fronte, giu' per il fronte, che si fermano a 1,4
    mm dalla piega con la falda sotto il fronte - una falda, non una faccia -
    dove la linguetta continua in nero fino alla tacca per il dito. Si prova
    solo quando la firma, la firma larga e la perforazione non trovano
    niente: i casi di prima non cambiano strada.
    """
    quadri = [panels[n] for n in facce if n in panels]
    if not quadri:
        return None
    migliore = None
    for _st, percorsi in _tratti_per_penna(pdf, page_no).items():
        segmenti = [sg for sg in _segmenti(percorsi)
                    if any(_dentro_pannello(sg, p) is not None for p in quadri)]
        pezzi = [_fino_al_lato(l, quadri)
                 for l in _catene(segmenti) if not _di_bordo(l, quadri)]
        if len(pezzi) < 2:
            continue
        t = _perforata_continua(percorsi, pezzi, quadri, sul_lato=True)
        if t is not None:
            lunga = _lunghezza(t["catena"])
            if migliore is None or lunga > migliore[0]:
                migliore = (lunga, t)
    if migliore is None:
        return None
    t = migliore[1]
    if t.get("chiusura") is not None:
        oltre = linguetta_oltre(pdf, quadri, t["chiusura"], page_no)
        if oltre is not None:
            t["linguetta"] = oltre
    return t


# Quanto prima del lato si ferma un ramo che lo attraversa, in mm: il ramo
# finisce come quello del T10, che il disegno ferma a 1,4 mm dalla piega.
STACCO = 1.0


def _fino_al_lato(l, quadri):
    """Il ramo `l` fino al lato da cui esce dalle facce, o `l` com'e'.

    Sull'astuccio di biscotti T25 (caso ab4fa8dad8) il contorno verde
    dell'apertura non si ferma prima della piega fra il fronte e la falda
    sotto, come sul T10: la attraversa e continua sulla falda, dove gira
    attorno alla linguetta. Un capo del ramo sta in una faccia, l'altro
    fuori da tutte: il ramo si taglia dove esce dalla sua faccia, STACCO mm
    prima del lato - il contorno della finestra si chiude sul lato
    (`_chiusa_sul_lato`), e quello che c'e' oltre e' la linguetta
    (`linguetta_oltre`). Un ramo che passa in un'altra faccia resta com'e'.
    """
    tol = 0.5 * MM

    def dentro(q, p):
        return (p.x0 - tol <= q[0] <= p.x1 + tol
                and p.y0 - tol <= q[1] <= p.y1 + tol)

    def in_una(q):
        return any(dentro(q, p) for p in quadri)
    if len(l) < 2 or in_una(l[0]) == in_una(l[-1]):
        return l
    giro = not in_una(l[0])
    c = list(l[::-1]) if giro else list(l)
    m = ((c[0][0] + c[1][0]) / 2.0, (c[0][1] + c[1][1]) / 2.0)
    p = next((p for p in quadri if dentro(m, p)), None)
    if p is None:
        return l
    for i in range(len(c) - 1):
        a, b = c[i], c[i + 1]
        if dentro(b, p):
            continue
        if in_una(b):
            return l            # passa in un'altra faccia: non e' questo
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = 1.0
        for o, dk, lo, hi in ((a[0], dx, p.x0, p.x1), (a[1], dy, p.y0, p.y1)):
            if dk > 1e-12:
                t = min(t, (hi - o) / dk)
            elif dk < -1e-12:
                t = min(t, (lo - o) / dk)
        lungo = math.hypot(dx, dy) * t
        if lungo <= STACCO * MM:
            return l
        t *= (lungo - STACCO * MM) / lungo
        taglio = c[:i + 1] + [(a[0] + dx * t, a[1] + dy * t)]
        return taglio[::-1] if giro else taglio
    return l


def linguetta_oltre(pdf, quadri, chiusura, page_no=0):
    """La linguetta che continua la finestra OLTRE il lato su cui il
    contorno si chiude (`_chiusa_sul_lato`), su una falda che non e' una
    faccia: il poligono chiuso, in punti PDF, dal capo `chiusura[1]` sul lato
    giu' per la linguetta e su fino al capo `chiusura[2]` - il lato lo chiude
    - o None.

    E' il percorso piu' corto fra i due capi sui tratti sottili di qualunque
    penna fuori da tutte le facce, senza quelli che corrono sul lato: due
    tratti che non si toccano per meno di `PONTE` si cuciono (un capo libero
    va sul punto piu' vicino di un altro tratto). Sull'astuccio di biscotti
    T10 (caso e88a907c54) la linguetta e' nera da 0,55 sulla falda sotto il
    fronte, 44,4 mm larga e lunga 31, e finisce sul bordo della falda (nero
    da 1,0), con due salti da 0,3 e 1,2 mm fra un tratto e l'altro."""
    import heapq
    _a, U, V, _b = chiusura
    ux, uy = V[0] - U[0], V[1] - U[1]
    lato = math.hypot(ux, uy)
    if lato < 1e-6:
        return None
    tx, ty = ux / lato, uy / lato
    # verso fuori: dalla parte opposta alla faccia del contorno
    fx, fy = -ty, tx
    gx, gy = (U[0] + V[0]) / 2.0, (U[1] + V[1]) / 2.0
    cx, cy = (_a[0] + _b[0]) / 2.0, (_a[1] + _b[1]) / 2.0
    if (cx - gx) * fx + (cy - gy) * fy > 0:
        fx, fy = -fx, -fy
    ponte = PONTE * MM
    portata = 2.0 * lato + 50.0 * MM

    def fuori(q):
        return (q[0] - U[0]) * fx + (q[1] - U[1]) * fy

    def lungo(q):
        return (q[0] - U[0]) * tx + (q[1] - U[1]) * ty

    segs = []
    for percorsi in _tratti_per_penna(pdf, page_no).values():
        for sg in _segmenti(percorsi):
            # il tratto che attraversa il lato (`_fino_al_lato`): conta la
            # parte oltre, dal lato in fuori
            fa, fb = fuori(sg[0]), fuori(sg[1])
            if fa * fb < 0 and max(fa, fb) > 0.3 * MM:
                a, b = sg if fb > 0 else sg[::-1]
                t = fuori(a) / (fuori(a) - fuori(b))
                X = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                if -0.5 * MM <= lungo(X) <= lato + 0.5 * MM:
                    sg = (X, b)
            if any(_dentro_pannello(sg, p) is not None for p in quadri):
                continue
            if max(abs(fuori(q)) for q in sg) < 0.3 * MM:
                continue        # sul lato: e' la piega, non la linguetta
            if min(fuori(q) for q in sg) < -0.3 * MM:
                continue
            if any(fuori(q) > portata or not -portata < lungo(q) < lato + portata
                   for q in sg):
                continue
            segs.append(sg)
    if not segs:
        return None
    # i nodi: i capi dei tratti, e i punti dove un capo libero si cuce
    grado = {}

    def chiave(q):
        return (round(q[0] / 0.05), round(q[1] / 0.05))
    for a, b in segs:
        for q in (a, b):
            grado[chiave(q)] = grado.get(chiave(q), 0) + 1
    tagli = {i: [] for i in range(len(segs))}
    ponti = []
    for i, (a, b) in enumerate(segs):
        for q in (a, b):
            if grado[chiave(q)] != 1:
                continue
            meglio = None
            for j, (c, d) in enumerate(segs):
                # non il tratto stesso, ne' quello che gli e' attaccato: sulla
                # curva della linguetta del T25 (caso ab4fa8dad8) il tratto
                # dopo sulla stessa linea e' piu' vicino del taglio nero
                if j == i or {chiave(c), chiave(d)} & {chiave(a), chiave(b)}:
                    continue
                dx, dy = d[0] - c[0], d[1] - c[1]
                l2 = dx * dx + dy * dy
                t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((q[0] - c[0]) * dx + (q[1] - c[1]) * dy) / l2))
                r = (c[0] + dx * t, c[1] + dy * t)
                dist = math.hypot(r[0] - q[0], r[1] - q[1])
                if 1e-6 < dist <= ponte and chiave(r) != chiave(q) and (meglio is None or dist < meglio[0]):
                    meglio = (dist, j, t, r)
            if meglio is not None:
                tagli[meglio[1]].append((meglio[2], meglio[3]))
                ponti.append((q, meglio[3]))
    archi = {}

    def arco(p, q):
        kp, kq = chiave(p), chiave(q)
        if kp == kq:
            return
        w = math.hypot(q[0] - p[0], q[1] - p[1])
        archi.setdefault(kp, []).append((w, kq, q))
        archi.setdefault(kq, []).append((w, kp, p))
    for i, (a, b) in enumerate(segs):
        punti = [a] + [r for _t, r in sorted(tagli[i])] + [b]
        for p, q in zip(punti, punti[1:]):
            arco(p, q)
    for p, q in ponti:
        arco(p, q)
    pos = {}
    for k, lst in archi.items():
        for _w, k2, q in lst:
            pos.setdefault(k2, q)

    def vicino(X):
        cand = [(math.hypot(q[0] - X[0], q[1] - X[1]), k) for k, q in pos.items()]
        d, k = min(cand) if cand else (None, None)
        return k if d is not None and d <= ponte else None
    s, e = vicino(U), vicino(V)
    if s is None or e is None or s == e:
        return None
    dist, prima = {s: 0.0}, {}
    coda = [(0.0, s)]
    while coda:
        d, k = heapq.heappop(coda)
        if k == e:
            break
        if d > dist.get(k, float("inf")):
            continue
        for w, k2, _q in archi.get(k, []):
            if d + w < dist.get(k2, float("inf")):
                dist[k2] = d + w
                prima[k2] = k
                heapq.heappush(coda, (d + w, k2))
    if e not in dist:
        return None
    cammino = [e]
    while cammino[-1] != s:
        cammino.append(prima[cammino[-1]])
    cammino = [pos[k] for k in reversed(cammino)]
    # una linguetta e' un pezzo che esce dal lato, non un tratto lungo la piega
    if max(fuori(q) for q in cammino) < 2.0 * PONTE * MM:
        return None
    return [tuple(U)] + [tuple(q) for q in cammino] + [tuple(V)]


def tagli(pdf, panels, facce, page_no=0):
    """{faccia: [linea, ...]} i tagli d'apertura da incidere, in punti PDF.

    Si incide solo un'APERTURA A STRAPPO, e la si riconosce dalla sua firma:
    un taglio sul lato stampato con accanto, a pochi millimetri, il taglio dal
    rovescio con le spunte. E' quello che fa staccare il cartone pulito fra i
    due. Con lui vanno i tagli che lo continuano - la linguetta, anche quando
    gira su un'altra faccia - e quelli che gli stanno a un passo, come la
    mezzaluna per il dito. Un altro tratto dentro una faccia - il riquadro di
    un'area, una piega di servizio, un taglio di cui la fustella non dice a
    cosa serve - resta come oggi: senza la firma non si sa cos'e', e un solco
    sbagliato e' peggio di nessun solco.

    Ogni linea esce tagliata alla sua faccia: la linguetta che gira sotto il
    fondo esce in due pezzi, uno sul fronte e uno sul fondo.
    """
    trovata = firma(pdf, panels, facce, page_no)
    if trovata is not None:
        aperture, vicini, _rovescio = trovata
        scelte = [l for g in aperture + vicini for l in g]
    else:
        # la perforazione si incide trattino per trattino: i ponticelli sono
        # cartone intero
        # prima la firma larga, che segue il taglio dal rovescio («devi
        # seguire la linea viola»): sul T2x12 con la finestra la perforazione
        # continua prendeva il taglio a vista, 3 mm fuori dalla linea viola
        larga = firma(pdf, panels, facce, page_no, larga=True)
        p = perforata(pdf, panels, facce, page_no) if larga is None else None
        if p is not None:
            scelte = p["pezzi"] + p["vicini"]
        elif larga is None and (c := continua_per_penna(pdf, panels, facce, page_no)) is not None:
            scelte = c["pezzi"]
        elif larga is not None:
            # l'apertura su penne sottili si incide sul taglio DAL ROVESCIO,
            # la linea con le spunte: e' quella che il proprietario guarda
            # («devi seguire la linea viola per modellare la fustella di
            # apertura», T2x12 a strappo). Il taglio a vista corre sulla
            # piega e sullo spigolo non si vedeva
            aperture, vicini, rovescio = larga
            # con lui i tagli dentro una faccia attaccati a lui coi due capi:
            # l'arco della tacca per il dito sul fianco
            altri = [l for g in aperture + vicini for l in g]
            quadri = [panels[n] for n in facce if n in panels]
            def attaccato(q):
                return min(_distanza_punto(q, r) for r in rovescio) <= 1.5 * MM
            scelte = list(rovescio) + [
                l for l in altri if not _di_bordo(l, quadri)
                and not _accanto(l, rovescio)
                and attaccato(l[0]) and attaccato(l[-1])]
        else:
            return {}
    out = {}
    for nome in facce:
        p = panels.get(nome)
        if p is None:
            continue
        pezzi = [d for l in scelte for a, b in zip(l, l[1:])
                 for d in [_dentro_pannello((a, b), p)] if d is not None]
        linee_f = [l for l in _catene(pezzi) if _lunghezza(l) * PT2MM >= CORTO]
        if linee_f:
            out[nome] = linee_f
    return out


def _lati_liberi(p, quadri, tol=1.0 * MM):
    """I lati di `p` (indici come `_sul_lato`) che non toccano un altro
    pannello: il bordo libero della faccia, non una piega."""
    lati = (((p.x0, p.y0), (p.x1, p.y0)), ((p.x0, p.y1), (p.x1, p.y1)),
            ((p.x0, p.y0), (p.x0, p.y1)), ((p.x1, p.y0), (p.x1, p.y1)))
    liberi = set()
    for k, (a, b) in enumerate(lati):
        m = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        if not any(q is not p and _sul_lato(m, [q], tol) for q in quadri):
            liberi.add(k)
    return liberi


def chiusura(pdf, panels, facce, page_no=0):
    """{faccia: [linea, ...]} la linguetta di chiusura da incidere, in punti.

    Il caso: un astuccio di cioccolatini da 16 chiude il fondo con una falda il cui
    bordo libero ha due tacche e, fra loro, la linguetta che si infila nella
    fessura dell'altra falda. La faccia del modello e' il rettangolo pieno
    del pannello, e quel taglio - una catena di 47 mm su 34 di bordo, che
    entra nella faccia di 6,6 mm - spariva: chi l'aveva caricata ha respinto
    il modello perche' la linguetta non c'era.

    La regola: un tratto della fustella che parte da un lato LIBERO della
    faccia (non una piega con un'altra faccia), entra nella faccia almeno di
    `LINGUETTA_MIN` mm e torna sullo stesso lato e' il taglio di una
    chiusura - tacca, linguetta - e sul cartone chiuso si vede: si incide
    come i tagli dell'apertura. I lati obliqui di una falda partono da un
    lato e arrivano su un altro, e il bordo appena storto non entra: restano
    come sono.
    """
    tratti = _segmenti(_tratti_tecnici(pdf, page_no))
    if not tratti:
        return {}
    quadri = list(panels.values())
    out = {}
    for nome in facce:
        p = panels.get(nome)
        if p is None:
            continue
        liberi = _lati_liberi(p, quadri)
        if not liberi:
            continue
        pezzi = [d for s in tratti for d in [_dentro_pannello(s, p)] if d is not None]
        scelte = []
        for l in _catene(pezzi):
            if _lunghezza(l) * PT2MM < CORTO:
                continue
            capi = [{k for _i, k in _sul_lato(q, [p], 1.0 * MM)} for q in (l[0], l[-1])]
            comuni = capi[0] & capi[1] & liberi
            for k in comuni:
                fondo = max((abs(q[1] - (p.y0, p.y1)[k]) if k < 2 else
                             abs(q[0] - (p.x0, p.x1)[k - 2])) for q in l)
                if fondo * PT2MM >= LINGUETTA_MIN:
                    scelte.append(l)
                    break
        if scelte:
            out[nome] = scelte
    return out


def _distanza_punto(q, linea):
    best = float("inf")
    for (px, py), (qx, qy) in zip(linea, linea[1:]):
        dx, dy = qx - px, qy - py
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((q[0] - px) * dx + (q[1] - py) * dy) / l2))
        best = min(best, math.hypot(q[0] - px - dx * t, q[1] - py - dy * t))
    return best


def _campioni(linea, passo):
    """Punti lungo la linea, uno ogni `passo` punti PDF."""
    out = [linea[0]]
    for (px, py), (qx, qy) in zip(linea, linea[1:]):
        lung = math.hypot(qx - px, qy - py)
        n = max(1, int(lung / passo))
        out += [(px + (qx - px) * k / n, py + (qy - py) * k / n) for k in range(1, n + 1)]
    return out


def _accanto(linea, rovescio):
    """La linea corre accanto a un taglio dal rovescio, fra 1,5 e 5 mm, per
    almeno ACCANTO mm della sua lunghezza."""
    passo = 1.0 * MM
    for r in rovescio:
        n = sum(1 for q in _campioni(linea, passo)
                if 1.5 * MM <= _distanza_punto(q, r) <= 5.0 * MM)
        if n * 1.0 >= ACCANTO:
            return True
    return False


def _distanza_gruppi(a, b):
    return min(_distanza_punto(q, lb) for la in a for q in _campioni(la, 1.0 * MM)
               for lb in b)


def _gruppi(linee):
    """Le linee raccolte per estremi in comune: il lato di una finestra e il
    lato della sua linguetta si toccano nel collo, e vanno giudicati insieme."""
    gruppo = list(range(len(linee)))

    def radice(i):
        while gruppo[i] != i:
            gruppo[i] = gruppo[gruppo[i]]
            i = gruppo[i]
        return i

    estremi = [(l[0], l[-1]) for l in linee]
    for i in range(len(linee)):
        for j in range(i + 1, len(linee)):
            if any(math.hypot(a[0] - b[0], a[1] - b[1]) <= CUCI
                   for a in estremi[i] for b in estremi[j]):
                gruppo[radice(i)] = radice(j)
    out = {}
    for i, l in enumerate(linee):
        out.setdefault(radice(i), []).append(l)
    return list(out.values())


# --------------------------------------------------------------------------- #
# il solco nella faccia
# --------------------------------------------------------------------------- #
# Le rotazioni con cui `artwork.gira_sulla_grafica` gira le texture
# (Image.ROTATE_*, antiorarie): dove finisce, nella texture girata, un punto
# (u, v) di quella presa dal foglio.
_GIRO_UV = {
    0: lambda u, v: (u, v),
    90: lambda u, v: (v, 1.0 - u),
    180: lambda u, v: (1.0 - u, 1.0 - v),
    270: lambda u, v: (1.0 - v, u),
}


def _uv_faccia(linea, p, gradi):
    """La linea dal foglio alle coordinate della texture della faccia."""
    gira = _GIRO_UV[int(gradi) % 360]
    w, h = (p.x1 - p.x0) or 1.0, (p.y1 - p.y0) or 1.0
    return [gira((x - p.x0) / w, (y - p.y0) / h) for x, y in linea]


def _ricampiona(linea, passo):
    """(punti, tangenti) lungo una linea in mm, uno ogni `passo` mm."""
    pts, tan = [], []
    for k, (a, b) in enumerate(zip(linea, linea[1:])):
        d = np.subtract(b, a)
        lung = float(np.hypot(*d))
        if lung < 1e-9:
            continue
        t = d / lung
        n = max(1, int(math.ceil(lung / passo)))
        for i in range(0 if not pts else 1, n + 1):
            pts.append(np.add(a, d * (i / n)))
            tan.append(t)
    return pts, tan


def _distanze(P, linee):
    """La distanza di ogni punto di P dalla linea piu' vicina, vettoriale."""
    best = np.full(len(P), np.inf)
    for linea in linee:
        A = np.asarray(linea[:-1], float)
        B = np.asarray(linea[1:], float)
        D = B - A
        L2 = np.maximum((D ** 2).sum(1), 1e-12)
        for a, d, l2 in zip(A, D, L2):
            t = np.clip(((P - a) @ d) / l2, 0.0, 1.0)
            q = a + t[:, None] * d
            best = np.minimum(best, np.hypot(*(P - q).T))
    return best


def maglia_incisa(quad, linee_uv, profondita=PROFONDITA, larghezza=LARGHEZZA):
    """La faccia `quad` col solco delle linee: (superficie, solco).

    `linee_uv` sono nelle coordinate della texture, [0, 1] x [0, 1]. Ognuna
    delle due parti e' (V, N, UV, T): vertici 3D, normali, coordinate texture
    e triangoli. La superficie resta nel piano della faccia, con la sua
    texture; il solco e' a V, scende di `profondita` sulla linea e risale a
    zero a `larghezza / 2` di distanza.

    La triangolazione e' di Delaunay sui punti del solco - la linea e i suoi
    due bordi, ogni PASSO mm - piu' gli angoli della faccia: i campioni lungo
    il solco sono piu' fitti della sua larghezza, e un triangolo che lo
    scavalcasse avrebbe nel cerchio circoscritto i punti della linea, quindi
    Delaunay non lo fa.
    """
    from scipy.spatial import Delaunay

    q = np.asarray(quad, float)
    es, et = q[1] - q[0], q[3] - q[0]
    W, H = float(np.linalg.norm(es)), float(np.linalg.norm(et))
    es, et = es / W, et / H
    n = -np.cross(q[1] - q[0], q[3] - q[0])
    n /= np.linalg.norm(n)
    a = larghezza / 2.0
    linee = [[(u * W, v * H) for u, v in l] for l in linee_uv]
    punti = [(0.0, 0.0), (W, 0.0), (W, H), (0.0, H)]
    for linea in linee:
        P, T = _ricampiona(linea, PASSO)
        for k, (p, t) in enumerate(zip(P, T)):
            nn = np.array([-t[1], t[0]])
            punti += [tuple(p), tuple(p + nn * a), tuple(p - nn * a)]
            if k in (0, len(P) - 1):          # la punta: il solco si chiude
                verso = -t if k == 0 else t
                punti.append(tuple(p + verso * a))
    S = np.clip(np.array(punti, float), [0.0, 0.0], [W, H])
    S = np.unique(np.round(S / 0.002).astype(np.int64), axis=0) * 0.002
    prof = profondita * np.clip(1.0 - _distanze(S, linee) / a, 0.0, 1.0)
    # I bordi del solco stanno a fior di faccia: l'arrotondamento dei punti li
    # sposta di un millesimo e gli dava una profondita' di qualche micron, e
    # allora ogni triangolo grande che li tocca - mezza faccia - finiva nel
    # solco, grigio e storto.
    prof[prof < 0.2 * profondita] = 0.0
    tri = Delaunay(S).simplices
    V = q[0] + S[:, :1] * es + S[:, 1:] * et - prof[:, None] * n
    UV = np.column_stack([S[:, 0] / W, S[:, 1] / H])
    # il verso dei triangoli: la normale fuori dalla faccia
    a3, b3, c3 = V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]]
    rovesci = (np.cross(b3 - a3, c3 - a3) @ n) < 0
    tri[rovesci] = tri[rovesci][:, [0, 2, 1]]
    nel_solco = (prof[tri] > 1e-6).any(1)

    def parte(T, piatta):
        if not len(T):
            return None
        if piatta:
            usati, inv = np.unique(T, return_inverse=True)
            N = np.tile(n, (len(usati), 1))
            return V[usati], N, UV[usati], inv.reshape(-1, 3)
        # le pareti del solco a facce piatte: un vertice per triangolo
        Vt = V[T].reshape(-1, 3)
        UVt = UV[T].reshape(-1, 2)
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        Nf = np.cross(b - a, c - a)
        Nf /= np.maximum(np.linalg.norm(Nf, axis=1, keepdims=True), 1e-12)
        return Vt, np.repeat(Nf, 3, axis=0), UVt, np.arange(len(Vt)).reshape(-1, 3)

    return parte(tri[~nel_solco], True), parte(tri[nel_solco], False)


def incidi(faces, tagli_faccia, panels, girate=None, spessore=None):
    """Mette il solco nelle facce che hanno tagli d'apertura. In place.

    `tagli_faccia` e' quello che torna `tagli`; `girate` le facce girate da
    `artwork.gira_sulla_grafica` e di quanto. Si chiama sulle facce finite -
    dopo `folding.gira_facce` - perche' il solco segua il quad cosi' com'e'.
    La faccia tiene il suo quad, che serve a tutto il resto (verifiche,
    guscio, viste): l'esportatore, se c'e' `maglia`, scrive quella.
    """
    girate = girate or {}
    prof = PROFONDITA if not spessore else min(PROFONDITA, 0.5 * spessore)
    n = 0
    for f in faces:
        linee = tagli_faccia.get(f["name"])
        p = panels.get(f["name"])
        if not linee or p is None:
            continue
        uv = [_uv_faccia(l, p, girate.get(f["name"], 0)) for l in linee]
        f["maglia"] = maglia_incisa(f["quad"], uv, prof)
        n += len(linee)
    return n
