"""Il display a scatola: una scatola chiusa con la plancia ricavata dal
coperchio.

Arriva chiusa, come un astuccio: fronte, coperchio, fianchi attaccati al
coperchio, retro e fondo. Nel coperchio un contorno di tagli (due fessure
lungo i fianchi, la cima sul fronte) stacca un pannello che resta attaccato
solo a una cordonatura tratteggiata verso il retro: la cerniera. Si alza di
90 gradi sulla cerniera e una riga a meta' lo piega in due: la parte verso
la cerniera sta in piedi con la stampa verso il retro, la parte verso il
fronte si ripiega in avanti e scende davanti a lei, con la stampa verso chi
guarda. Nel coperchio resta la finestra da cui si vede il prodotto. Vedi REGOLE.md, *Il display a
scatola*.

Diverso dal display con plancia (`pack3d.plancia`): li' la scatola perde il
coperchio e diventa un vassoio aperto; qui resta chiusa, e la plancia e' un
pezzo del coperchio.

La forma si legge dai tratti della fustella, nei quattro versi del foglio
sulla tavola: nessuna misura cucita, tutto viene dalle righe del DT.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import dieline as dl
from . import folding

PT2MM = dl.PT2MM

# due tratti sulla stessa riga, se la loro coordinata differisce meno di cosi'
RIGA = 0.3
# due pezzi della stessa riga, se fra loro c'e' meno di cosi' (mm)
BUCO = 4.0
# combaciano: estremi e posizioni uguali entro (mm)
TOL = 1.6
# la cerniera e' tratteggiata: almeno tanti pezzi
TRATTI_CERNIERA = 5
# i ponticelli di un taglio a strappo: interruzioni non piu' larghe di tanto
# (mm), dove il taglio si salta e si legge la riga dietro
PONTICELLO = 2.0
# mm: un foro nella plancia (la presa, l'occhiello) ha i tagli piu' corti di
# cosi' e piu' vicini di cosi': `_profilo` non lo prende per il bordo
FORO = 15.0


@dataclass
class ScatolaPlancia:
    regione: tuple      # ingombro della fustella, in punti PDF
    giro: int           # quarti di giro dal foglio al telaio di lettura
    centro: tuple       # (cx, cy) del foglio, in mm: il perno del giro
    uL: float           # coperchio: colonna, in mm nel telaio di lettura
    uR: float
    vF: float           # coperchio: bordo sul fronte e bordo sul retro
    vB: float
    H: float            # altezza della scatola (la larghezza dei fianchi)
    fronte: float       # altezza del fronte sul foglio
    fondo: tuple        # (v0, v1): il fondo, dal retro al fronte
    pl_u: tuple         # plancia: bordi (fessure interne)
    buco_u: tuple       # finestra: bordi (fessure esterne)
    vT: float           # cima della plancia (verso il fronte)
    vM: float           # la riga di mezzo
    vH: float           # la cerniera
    taglio: tuple = ()  # il bordo alto del fronte dentro la finestra: (u, v)
    # La variante col fondo attaccato a un fianco (`_leggi_fianco`); vuoti
    # nella scatola col fondo dopo il retro.
    # profilo: la plancia sagomata, a passi lungo v: (v, plancia da, a,
    # finestra da, a); vuoto se la plancia e' un rettangolo fra le fessure
    profilo: tuple = ()
    # i fianchi: (u della piega lontana a sinistra, a destra) sul foglio
    fianchi: tuple = ()
    # il fondo attaccato al fianco: (u della piega col fianco, u del bordo
    # lontano); il fianco da quella parte e' piu' alto della scatola e il
    # di piu' va sotto, sul fondo
    fondo_u: tuple = ()
    # la striscia del fianco senza fondo che si piega dentro, sul fondo:
    # (u da, u a)
    striscia: tuple = ()

    @property
    def W(self):
        return self.uR - self.uL

    @property
    def D(self):
        return self.vB - self.vF


def _ruota(P, k, c):
    """Il punto del foglio nel telaio girato di k quarti attorno a c."""
    x, y = P[..., 0] - c[0], P[..., 1] - c[1]
    for _ in range(k % 4):
        x, y = -y, x
    return np.stack([x + c[0], y + c[1]], axis=-1)


def _righe(tratti):
    """Le righe orizzontali e verticali: [(posizione, da, a, pezzi)]."""
    oriz, vert = {}, {}
    for p in tratti:
        for a, b in zip(p[:-1], p[1:]):
            d = b - a
            lun = float(np.hypot(*d))
            if lun < 0.3:
                continue
            if abs(d[1]) <= 0.02 * lun:
                oriz.setdefault(float((a[1] + b[1]) / 2), []).append(
                    (min(a[0], b[0]), max(a[0], b[0])))
            elif abs(d[0]) <= 0.02 * lun:
                vert.setdefault(float((a[0] + b[0]) / 2), []).append(
                    (min(a[1], b[1]), max(a[1], b[1])))

    def unisci(diz):
        out = []
        chiavi = sorted(diz)
        gruppi = []
        for k in chiavi:
            if gruppi and k - gruppi[-1][-1] <= RIGA:
                gruppi[-1].append(k)
            else:
                gruppi.append([k])
        for g in gruppi:
            pos = float(np.mean(g))
            seg = sorted(s for k in g for s in diz[k])
            corsa = None
            for a, b in seg:
                if corsa and a <= corsa[1] + BUCO:
                    corsa[1] = max(corsa[1], b)
                    corsa[2] += 1
                else:
                    if corsa:
                        out.append((pos, corsa[0], corsa[1], corsa[2]))
                    corsa = [a, b, 1]
            if corsa:
                out.append((pos, corsa[0], corsa[1], corsa[2]))
        return out

    return unisci(oriz), unisci(vert)


def _copre(r, a, b, tol=TOL):
    return r[1] <= a + tol and r[2] >= b - tol


def _leggi(H, V):
    """La forma nel telaio di lettura, o None. Il fronte sta in alto (v
    piccole), il coperchio sotto, poi il retro e il fondo.

    Il bordo dietro del coperchio e' una riga sola da un fianco all'altro;
    quello davanti no, perche' le fessure della plancia lo interrompono. Il
    coperchio e i fianchi si leggono dal bordo dietro e dai lati dei fianchi,
    che scendono fino a lui."""
    for rB in H:
        a, b, vB = rB[1], rB[2], rB[0]
        Wt = b - a
        if Wt < 100:
            continue
        fuori = [r for r in V if abs(r[2] - vB) < TOL
                 and (abs(r[0] - a) < TOL or abs(r[0] - b) < TOL)]
        for rA in fuori:
            vF = rA[1]
            D = vB - vF
            if D < 40 or D > 1.5 * Wt:
                continue
            if not any(abs(r[0] - (a + b - rA[0])) < TOL and abs(r[1] - vF) < TOL
                       and abs(r[2] - vB) < TOL for r in fuori):
                continue
            # le pieghe dei fianchi: alla stessa distanza dai due lati
            for rL in V:
                if not (a + 10 < rL[0] < (a + b) / 2 and abs(rL[1] - vF) < TOL
                        and abs(rL[2] - vB) < TOL):
                    continue
                Hs = rL[0] - a
                rR = [r for r in V if abs(r[0] - (b - Hs)) < TOL
                      and abs(r[1] - vF) < TOL and abs(r[2] - vB) < TOL]
                if not rR:
                    continue
                uL, uR = rL[0], rR[0][0]
                W = uR - uL
                if W < 40 or Hs > 1.5 * W:
                    continue
                f = _scatola(H, V, vF, vB, uL, uR, Hs)
                if f is not None:
                    return (uL, uR, vF, vB, Hs) + f
    return None


def _scatola(H, V, vF, vB, uL, uR, Hs):
    W, D = uR - uL, vB - vF

    def larga(r):
        return r[1] >= uL - 3 and r[2] <= uR + 3 and r[2] - r[1] >= 0.9 * W

    # il fronte: una riga della colonna a un'altezza di scatola sopra
    fr = [r for r in H if larga(r) and 0.85 * Hs <= vF - r[0] <= 1.15 * Hs]
    if not fr:
        return None
    fronte = vF - min(fr, key=lambda r: abs(vF - r[0] - Hs))[0]
    # il fondo: l'ultima riga intera della colonna, e la riga prima di lei
    # lontana quanto il coperchio e' profondo
    intere = sorted(r[0] for r in H if r[1] >= uL - 3 - 2 * Hs and r[2] <= uR + 3 + 2 * Hs
                    and r[2] - r[1] >= W - 2 * TOL and r[1] <= uL + TOL
                    and r[2] >= uR - TOL and vB + 0.8 * Hs < r[0] <= vB + 2.0 * Hs + 1.1 * D)
    fondo = None
    if intere:
        v1 = intere[-1]
        v0 = [v for v in intere if 0.93 * D <= v1 - v <= 1.05 * D]
        if v0:
            fondo = (min(v0, key=lambda v: abs(v1 - v - D)), v1)
    if fondo is None:
        return None
    # la plancia: fessure dentro la colonna, a coppie attorno al centro
    uc = (uL + uR) / 2
    dentro = [r for r in V if uL + 3 < r[0] < uR - 3 and r[2] - r[1] >= 0.4 * D
              and r[1] < vB and r[2] > vF]
    coppie = []
    for r in dentro:
        if r[0] >= uc:
            continue
        for s in dentro:
            if s[0] > uc and abs(r[0] + s[0] - 2 * uc) < 3:
                coppie.append((r, s))
    if not coppie:
        return None
    interna = min(coppie, key=lambda c: c[1][0] - c[0][0])
    esterna = max(coppie, key=lambda c: c[1][0] - c[0][0])
    pl_u = (interna[0][0], interna[1][0])
    buco_u = (esterna[0][0], esterna[1][0])
    vT = min(interna[0][1], interna[1][1])
    largo = pl_u[1] - pl_u[0]
    if largo < 0.3 * W or vT >= vF + 0.5 * D:
        return None
    # la cerniera: una riga tratteggiata fra le fessure, verso il retro
    cern = [r for r in H if r[3] >= TRATTI_CERNIERA
            and r[1] <= pl_u[0] + 2 and r[2] >= pl_u[1] - 2
            and vF + 0.3 * D < r[0] < vB]
    if not cern:
        return None
    vH = max(r[0] for r in cern)
    # la riga di mezzo: intera, da fessura a fessura
    mezzo = [r for r in H if r[3] <= 3 and vT + 10 < r[0] < vH - 10
             and r[1] <= pl_u[0] + 2 and r[2] >= pl_u[1] - 2
             and r[2] - r[1] <= buco_u[1] - buco_u[0] + 2]
    if not mezzo:
        return None
    vM = min(mezzo, key=lambda r: abs(r[0] - (vT + vH) / 2))[0]
    return (fronte, fondo, pl_u, buco_u, vT, vM, vH)


def _vicina(V, u, lun, tol=3.0):
    """La riga verticale lunga almeno `lun` piu' vicina a u, entro tol."""
    c = [r for r in V if abs(r[0] - u) < tol and r[2] - r[1] >= lun]
    return min(c, key=lambda r: abs(r[0] - u))[0] if c else None


def _profilo(tratti, uL, uR, v0, v1, passo=1.0, centro=8.0, corto=3.0):
    """La plancia sagomata e la sua finestra, a passi lungo v fra v0 e v1:
    [(v, plancia da, a, finestra da, a)].

    A ogni v si cercano i tagli che la attraversano dentro la colonna del
    coperchio (non i suoi bordi): da ogni parte del centro il piu' vicino al
    centro e' il bordo della plancia, il piu' lontano quello della
    finestra (un taglio a strappo e' una fessura, due righe vicine). I tagli
    a meno di `centro` mm dal mezzo (la presa per il dito) e i tratti corti
    (le crocette dei ponticelli, le scritte) non contano. Un foro nella
    plancia (la presa, l'occhiello) taglia lo stesso v due volte dalla
    stessa parte con due tratti corti: non e' il suo bordo, si salta
    (`FORO`). Un v dove manca un lato non e' plancia. Vedi regole/vassoi.md, *Il display a scatola col
    fondo sul fianco*."""
    uc = (uL + uR) / 2
    seg = []
    for t in tratti:
        t = np.asarray(t, float)
        lun = float(np.hypot(*np.diff(t, axis=0).T).sum()) if len(t) >= 2 else 0.0
        if lun < corto:
            continue
        for a, b in zip(t[:-1], t[1:]):
            if abs(b[1] - a[1]) < 1e-6:
                continue
            if min(a[0], b[0]) < uL + 1 or max(a[0], b[0]) > uR - 1:
                continue
            seg.append((a, b, lun))

    def senza_fori(xs):
        # dal centro verso fuori: un taglio corto piu' dentro, e il suo
        # compagno se e' corto e vicino, e' un foro se fuori ne restano altri
        # due (il bordo della plancia e quello della finestra)
        xs = sorted(xs, key=lambda q: abs(q[0] - uc))
        while len(xs) > 2 and xs[0][1] < FORO:
            due = (len(xs) > 3 and xs[1][1] < FORO
                   and abs(xs[1][0] - xs[0][0]) < FORO)
            xs = xs[2:] if due else xs[1:]
        return [q[0] for q in xs]

    out = []
    for v in np.arange(v0 + passo / 2, v1, passo):
        xs = []
        for a, b, lun in seg:
            if min(a[1], b[1]) <= v <= max(a[1], b[1]):
                xs.append((a[0] + (b[0] - a[0]) * (v - a[1]) / (b[1] - a[1]), lun))
        sx = senza_fori([q for q in xs if q[0] < uc - centro])
        dx = senza_fori([q for q in xs if q[0] > uc + centro])
        if sx and dx:
            out.append((float(v), max(sx), min(dx), min(sx), max(dx)))
    return out


def _leggi_fianco(H, V, tratti):
    """La variante col fondo attaccato a un fianco, nel telaio di lettura
    (fronte in alto), o None.

    Fronte e retro alti uguali, attaccati al coperchio; da una parte il
    fianco porta il fondo (largo quanto il coperchio), dall'altra il fianco
    finisce con una striscia che va sul fondo. La scatola e' alta quanto il
    fronte: il fianco col fondo puo' essere piu' lungo, e il di piu' va
    sotto. La plancia e' sagomata (`_profilo`): la cerniera e' la riga
    tratteggiata, se c'e', o il bordo dietro del coperchio, dove i tagli
    arrivano. Vedi regole/vassoi.md, *Il display a scatola col fondo sul
    fianco*."""
    for rT in H:
        a, b = rT[1], rT[2]
        if b - a < 60:
            continue
        for rR in H:
            if not (rR[0] > rT[0] + 100 and abs(rR[1] - a) < 3
                    and abs(rR[2] - b) < 3):
                continue
            uL = _vicina(V, (a + rR[1]) / 2, 0.4 * (rR[0] - rT[0]))
            uR = _vicina(V, (b + rR[2]) / 2, 0.4 * (rR[0] - rT[0]))
            if uL is None or uR is None or uR - uL < 60:
                continue
            W = uR - uL
            dentro = sorted(r[0] for r in H if rT[0] + 10 < r[0] < rR[0] - 10
                            and r[1] <= uL + 2 and r[2] >= uR - 2)
            if len(dentro) < 2:
                continue
            vF, vB = dentro[0], dentro[-1]
            Hs, Hr = vF - rT[0], rR[0] - vB
            D = vB - vF
            if abs(Hs - Hr) > 2.0 or Hs < 15 or D < 40 or D > 2.5 * W:
                continue
            f = _fianchi(V, uL, uR, vF, vB, Hs)
            if f is None:
                continue
            fianchi, fondo_u, striscia = f
            sp = _plancia_sagomata(H, tratti, uL, uR, vF, vB, Hs)
            if sp is None:
                continue
            return dict(uL=uL, uR=uR, vF=vF, vB=vB, H=Hs, fronte=Hs,
                        fianchi=fianchi, fondo_u=fondo_u, striscia=striscia,
                        **sp)
    return None


def _fianchi(V, uL, uR, vF, vB, Hs, tol=2.5):
    """I fianchi e il fondo attaccato a uno di loro, o None."""
    W = uR - uL

    def piega(r):
        return abs(r[1] - vF) < tol and abs(r[2] - vB) < tol

    def copre(r):
        return r[1] <= vF + tol and r[2] >= vB - tol

    pieghe = sorted(r[0] for r in V if piega(r))
    for lato in (-1, 1):
        bordo = uL if lato < 0 else uR
        for f in pieghe:
            larga = (bordo - f) * -lato
            if larga < Hs - 2 or larga > 2 * Hs:
                continue
            lontano = [r[0] for r in V if copre(r)
                       and 0.95 * W <= (r[0] - f) * lato <= 1.05 * W]
            if not lontano:
                continue
            far = min(lontano, key=lambda u: abs(abs(u - f) - W))
            # dall'altra parte, il fianco: la prima piega a un'altezza
            # di scatola, e la striscia fino alla piega dopo
            altro = uR if lato < 0 else uL
            dist = sorted((u - altro) * -lato for u in pieghe
                          if (u - altro) * -lato > 0)
            parete = [d for d in dist if 0.85 * Hs <= d <= 1.15 * Hs]
            fp = parete[0] if parete else Hs
            dopo = [d for d in dist if fp + 8 <= d <= fp + Hs]
            striscia = ()
            if dopo:
                striscia = tuple(sorted((altro - lato * fp,
                                         altro - lato * dopo[0])))
            pa = altro - lato * fp
            fianchi = (f, pa) if lato < 0 else (pa, f)
            return fianchi, (f, far), striscia
    return None


def _plancia_sagomata(H, tratti, uL, uR, vF, vB, Hs):
    """La plancia sagomata nel coperchio: profilo, cerniera, riga di mezzo,
    cima; o None."""
    # dentro il coperchio; la cima che entra nel fronte la legge `_taglio`
    prof = _profilo(tratti, uL, uR, vF, vB)
    nel = prof
    D = vB - vF
    if len(nel) < 0.8 * D:
        return None
    larga = max(q[2] - q[1] for q in nel)
    if larga < 0.3 * (uR - uL):
        return None
    # la cerniera: tratteggiata, o il bordo dietro dove i tagli arrivano
    cern = [r for r in H if r[3] >= TRATTI_CERNIERA and vF + 0.3 * D < r[0] < vB
            and r[2] - r[1] >= 0.3 * larga]
    if cern:
        vH = max(r[0] for r in cern)
    elif nel[-1][0] >= vB - 2:
        vH = vB
    else:
        return None
    # il profilo e' continuo dalla cerniera verso il fronte: la cima e'
    # dove si interrompe
    tenuti = []
    for q in reversed(prof):
        if q[0] > vH:
            continue
        if tenuti and tenuti[-1][0] - q[0] > 2.0:
            break
        tenuti.append(q)
    tenuti.reverse()
    if not tenuti:
        return None
    vT = tenuti[0][0] - 0.5
    mezzo = []
    for r in H:
        if not (r[3] <= 3 and vT + 10 < r[0] < vH - 10):
            continue
        q = min(tenuti, key=lambda q: abs(q[0] - r[0]))
        if r[1] <= q[1] + 2 and r[2] >= q[2] - 2 and r[2] - r[1] <= q[4] - q[3] + 2:
            mezzo.append(r[0])
    if not mezzo:
        return None
    vM = min(mezzo, key=lambda v: abs(v - (vT + vH) / 2))
    a = min(q[1] for q in tenuti)
    b = max(q[2] for q in tenuti)
    fr = min((q for q in tenuti if q[0] >= vF), key=lambda q: q[0])
    return dict(profilo=tuple(tenuti), pl_u=(a, b), buco_u=(fr[3], fr[4]),
                vT=vT, vM=vM, vH=vH)


def _taglio(tratti, p):
    """Il bordo alto del fronte dove la plancia ci entra: [(u, v)] da una
    fessura esterna all'altra, o () se la plancia comincia sul bordo del
    coperchio.

    I tagli della cima della plancia proseguono dentro il fronte (le spalle,
    la presa per il dito): alzata la plancia, quel pezzo di fronte va via
    con lei. A ogni u fra le fessure esterne il fronte resta fin dove arriva
    il taglio piu' lontano dal coperchio (v piu' piccola): li' passa il
    contorno esterno, e nella presa per il dito il suo arco. Si leggono i
    tratti, nessuna forma cucita. Vedi REGOLE.md, *Il display a scatola*."""
    b0, b1 = p.buco_u
    alto, basso = p.vF - 1.0, p.vF - p.fronte + 2.0
    seg = []
    for t in tratti:
        for a, b in zip(t[:-1], t[1:]):
            if abs(b[0] - a[0]) < 1e-6:
                continue
            if max(a[1], b[1]) < basso or min(a[1], b[1]) > alto:
                continue
            if max(a[0], b[0]) < b0 or min(a[0], b[0]) > b1:
                continue
            seg.append((a, b))
    if not seg:
        return ()
    us = sorted({float(u) for a, b in seg for u in (a[0], b[0]) if b0 < u < b1}
                | set(np.linspace(b0, b1, int((b1 - b0) / 2.0) + 2)[1:-1].tolist()))
    us = [b0 + 0.05] + [u for u in us if b0 + 0.05 < u < b1 - 0.05] + [b1 - 0.05]
    out = []
    for u in us:
        vv = []
        for a, b in seg:
            if min(a[0], b[0]) <= u <= max(a[0], b[0]):
                v = a[1] + (b[1] - a[1]) * (u - a[0]) / (b[0] - a[0])
                if basso <= v <= alto:
                    vv.append(v)
        out.append((u, min(vv) if vv else p.vF))
    if all(v >= p.vF for _, v in out):
        return ()
    return _senza_ponticelli(out)


def _senza_ponticelli(out, largo=PONTICELLO, salto=1.0):
    """Il profilo del taglio senza i ponticelli.

    Un taglio a strappo ha dei ponticelli, interruzioni di meno di un
    millimetro che tengono la plancia attaccata finche' non la si strappa.
    Nel ponticello il taglio piu' lontano dal coperchio non c'e', e `_taglio`
    prendeva la riga dietro di lui: sul T15, ai due lati della presa per il
    dito, a 6,5 mm dal centro, il fronte saliva per 0,7 mm da 29 a 24 mm dal
    bordo, due spuntoni sottili di cartone dentro la presa. Una corsa di
    campioni piu' vicina al coperchio di quelli che la chiudono, di piu' di
    `salto`, su non piu' di `largo` mm, e' un ponticello: il taglio ci passa
    dritto, fra i due campioni che la chiudono."""
    u = [a for a, _ in out]
    v = [b for _, b in out]
    i = 1
    while i < len(v) - 1:
        j = i
        while j < len(v) and u[j] - u[i - 1] <= largo and v[j] > v[i - 1] + salto:
            j += 1
        if (i < j < len(v) and u[j] - u[i - 1] <= largo
                and min(v[i:j]) > v[j] + salto):
            for k in range(i, j):
                t = (u[k] - u[i - 1]) / ((u[j] - u[i - 1]) or 1.0)
                v[k] = v[i - 1] + (v[j] - v[i - 1]) * t
            i = j
        else:
            i += 1
    return tuple(zip(u, v))


def riconosci(pdf, page_no=0):
    """Il display a scatola, o None se la fustella non e' la sua."""
    from .ballotin import tratti_fustella
    tratti = tratti_fustella(pdf, page_no)
    if not tratti:
        return None
    tutti = np.vstack(tratti)
    lo, hi = tutti.min(axis=0), tutti.max(axis=0)
    c = tuple(((lo + hi) / 2).tolist())
    for k in range(4):
        girati = [_ruota(p, k, c) for p in tratti]
        H, V = _righe(girati)
        f = _leggi(H, V)
        if f is None:
            continue
        uL, uR, vF, vB, Hs, fronte, fondo, pl_u, buco_u, vT, vM, vH = f
        regione = (lo[0] / PT2MM, lo[1] / PT2MM, hi[0] / PT2MM, hi[1] / PT2MM)
        sp = ScatolaPlancia(regione=regione, giro=k, centro=c, uL=uL, uR=uR,
                            vF=vF, vB=vB, H=Hs, fronte=fronte, fondo=fondo,
                            pl_u=pl_u, buco_u=buco_u, vT=vT, vM=vM, vH=vH)
        sp.taglio = _taglio(girati, sp)
        return sp
    # la variante col fondo attaccato a un fianco e la plancia sagomata
    for k in range(4):
        girati = [_ruota(p, k, c) for p in tratti]
        H, V = _righe(girati)
        f = _leggi_fianco(H, V, girati)
        if f is None:
            continue
        regione = (lo[0] / PT2MM, lo[1] / PT2MM, hi[0] / PT2MM, hi[1] / PT2MM)
        f0, f1 = f["vB"], f["vB"] + f["H"]
        sp = ScatolaPlancia(regione=regione, giro=k, centro=c, fondo=(f0, f1),
                            **f)
        sp.taglio = _taglio(girati, sp)
        return sp
    return None


# la prima riga di `dichiara`: il riempimento la riconosce
TITOLO = "display a scatola: scatola chiusa con la plancia ricavata dal coperchio"


def dichiara(p):
    basso = p.vH - p.vM
    return [TITOLO,
            "scatola %.1f x %.1f x %.1f mm (larga x profonda x alta)"
            % (p.W, p.D, p.H),
            "plancia %.1f mm, alta %.1f mm sul coperchio, la parte verso il "
            "fronte (%.1f mm) ripiegata davanti; finestra nel coperchio "
            "%.1f x %.1f mm"
            % (p.pl_u[1] - p.pl_u[0], basso, p.vM - p.vT,
               p.buco_u[1] - p.buco_u[0], p.vH - max(p.vT, p.vF))] + (
        ["il fondo attaccato al fianco (%.1f mm: %.1f di parete, il resto "
         "sotto il fondo); dall'altra parte la striscia sul fondo; plancia "
         "sagomata, cerniera %s"
         % (abs(p.fondo_u[0] - (p.uL if p.fondo_u[0] < p.uL else p.uR)), p.H,
            "sul bordo del retro" if p.vH >= p.vB - 0.5 else "tratteggiata")]
        if p.fondo_u else [])


def maglia(p, origine_mm, px_mm, misura_tex, spessore=None, dove_plancia=None):
    """(V, UV, T, inizio_plancia) del display aperto, in mm, con la texture
    del DT intero e sotto le strisce del rovescio (`ballotin.con_interno`).
    Il fronte guarda +Z, la cima +Y, il fondo sta a Y = 0. I triangoli della
    plancia vengono per ultimi, da `inizio_plancia`: nel GLB sono un nodo a
    parte, e il riempimento misura il vano senza di lei.

    `dove_plancia`, scelta del pack: "fondo" mette il piede della plancia
    negli incastri sul fondo, dentro il retro, invece che sul bordo del
    retro sopra il coperchio (regole/riempimenti.md, *La plancia sul
    fondo*)."""
    from .ballotin import STRISCIA
    sp = folding.SPESSORE_CRT if spessore is None else spessore
    W, D, H = p.W, p.D, p.H
    Wt, Ht = misura_tex
    uv_interno = (0.5, (Ht - 1.5 * STRISCIA) / Ht)
    uv_taglio = (0.5, (Ht - 0.5 * STRISCIA) / Ht)
    ox, oy = origine_mm
    indietro = (4 - p.giro) % 4

    def uv(u, v):
        sx, sy = _ruota(np.array([u, v], float), indietro, p.centro)
        return ((sx - ox) * px_mm / Wt, (sy - oy) * px_mm / Ht)

    V, UV, T = [], [], []

    def quad(P3, S2, fuori, interno=True, coste=()):
        """Un pezzo piano: quattro angoli 3D e i loro punti (u, v) sul foglio.
        `coste`: i lati (i, i+1) che sono bordi liberi, col taglio."""
        P3 = np.asarray(P3, float)
        n = np.cross(P3[1] - P3[0], P3[2] - P3[0])
        tri = [(0, 1, 2), (0, 2, 3)]
        if float(n @ np.asarray(fuori, float)) < 0:
            tri = [(i, k, j) for i, j, k in tri]
            n = -n
        n = n / (np.linalg.norm(n) or 1.0)
        b = len(V)
        V.extend(P3.tolist())
        UV.extend([uv(*q) for q in S2])
        T.extend([(b + i, b + j, b + k) for i, j, k in tri])
        if interno:
            b = len(V)
            V.extend((P3 - n * sp).tolist())
            UV.extend([uv_interno] * 4)
            T.extend([(b + i, b + k, b + j) for i, j, k in tri])
        centro = P3.mean(axis=0)
        for i in coste:
            A, B = P3[i], P3[(i + 1) % 4]
            Q = np.array([A, B, B - n * sp, A - n * sp])
            m = (A + B) / 2 - centro
            nq = np.cross(Q[1] - Q[0], Q[2] - Q[0])
            b = len(V)
            V.extend(Q.tolist())
            UV.extend([uv_taglio] * 4)
            if float(nq @ m) < 0:
                T.extend([(b, b + 2, b + 1), (b, b + 3, b + 2)])
            else:
                T.extend([(b, b + 1, b + 2), (b, b + 2, b + 3)])

    uc = (p.uL + p.uR) / 2

    def X(u):
        # il foglio si guarda dalla parte stampata, col fronte in alto: chi
        # sta davanti alla scatola ha la destra dove il foglio ha la sinistra
        return uc - u

    def Zc(v):                      # sul coperchio
        return D / 2 - (v - p.vF)

    # il coperchio, attorno alla finestra: dal fronte alla cerniera la
    # finestra, larga quanto le fessure esterne
    b0, b1 = p.buco_u
    vh = p.vH
    if p.profilo:
        _sagomata(p, quad, X, Zc, H, D, sp)
    pezzi_cop = [] if p.profilo else [((p.uL, p.vF), (b0, p.vB), (2,)),       # a sinistra
                 ((b1, p.vF), (p.uR, p.vB), (0,)),       # a destra
                 ((b0, vh), (b1, p.vB), ())]             # dietro la cerniera
    for (u0, v0), (u1, v1), coste in pezzi_cop:
        quad([(X(u0), H, Zc(v1)), (X(u0), H, Zc(v0)), (X(u1), H, Zc(v0)),
              (X(u1), H, Zc(v1))],
             [(u0, v1), (u0, v0), (u1, v0), (u1, v1)], (0, 1, 0),
             coste=coste)

    # il fronte: si piega giu' dal bordo del coperchio. Dove la plancia
    # parte dentro il fronte, fra le fessure esterne il suo bordo alto segue
    # i tagli della fustella (`_taglio`): le spalle, e al centro la presa per
    # il dito. Alzata la plancia, quel pezzo di fronte va via con lei
    def Yf(v):
        return H - (p.vF - v) * H / p.fronte

    v0 = p.vF - p.fronte
    taglio = list(p.taglio)
    if not taglio and p.vT < p.vF:
        # la cima della plancia dritta dentro il fronte: la tacca
        taglio = [(b0 + 0.05, p.vT), (b1 - 0.05, p.vT)]
    if taglio:
        for u0, u1 in ((p.uL, b0), (b1, p.uR)):
            quad([(X(u0), 0, D / 2), (X(u1), 0, D / 2),
                  (X(u1), H, D / 2), (X(u0), H, D / 2)],
                 [(u0, v0), (u1, v0), (u1, p.vF), (u0, p.vF)], (0, 0, 1),
                 coste=((1,) if u1 == b0 else (3,)))
        for (ua, va), (ub, vb) in zip(taglio[:-1], taglio[1:]):
            quad([(X(ua), 0, D / 2), (X(ub), 0, D / 2),
                  (X(ub), Yf(vb), D / 2), (X(ua), Yf(va), D / 2)],
                 [(ua, v0), (ub, v0), (ub, vb), (ua, va)], (0, 0, 1),
                 coste=(2,))
        # da una fessura esterna al taglio: la riga sotto il primo e l'ultimo
        for ue, (ut, vt_) in ((b0, taglio[0]), (b1, taglio[-1])):
            quad([(X(ue), 0, D / 2), (X(ut), 0, D / 2),
                  (X(ut), Yf(vt_), D / 2), (X(ue), Yf(vt_), D / 2)],
                 [(ue, v0), (ut, v0), (ut, vt_), (ue, vt_)], (0, 0, 1))
    else:
        quad([(X(p.uL), 0, D / 2), (X(p.uR), 0, D / 2), (X(p.uR), H, D / 2),
              (X(p.uL), H, D / 2)],
             [(p.uL, v0), (p.uR, v0), (p.uR, p.vF), (p.uL, p.vF)], (0, 0, 1))

    # i fianchi, giu' dai lati del coperchio; nella variante col fondo sul
    # fianco la piega lontana del fianco senza fondo e' la sua
    lati = ((p.uL - H, p.uL), (p.uR + H, p.uR))
    if p.fondo_u:
        # dalla parte del fondo la parete e' alta quanto la scatola
        lati = tuple((fu if p.fianchi[i] == p.fondo_u[0] else p.fianchi[i], piega)
                     for i, (fu, piega) in enumerate(lati))
    for fuori_u, piega_u in lati:
        xx = X(piega_u)
        verso = np.sign(xx)
        quad([(xx, 0, Zc(p.vF)), (xx, 0, Zc(p.vB)), (xx, H, Zc(p.vB)),
              (xx, H, Zc(p.vF))],
             [(fuori_u, p.vF), (fuori_u, p.vB), (piega_u, p.vB), (piega_u, p.vF)],
             (verso, 0, 0))

    # il retro, giu' dal bordo dietro del coperchio
    quad([(X(p.uL), H, -D / 2), (X(p.uR), H, -D / 2), (X(p.uR), 0, -D / 2),
          (X(p.uL), 0, -D / 2)],
         [(p.uL, p.vB), (p.uR, p.vB), (p.uR, p.vB + H), (p.uL, p.vB + H)],
         (0, 0, -1))

    # il fondo, dal retro al fronte
    f0, f1 = p.fondo
    if not p.fondo_u:
        quad([(X(p.uL), 0, -D / 2), (X(p.uR), 0, -D / 2), (X(p.uR), 0, D / 2),
              (X(p.uL), 0, D / 2)],
             [(p.uL, f0), (p.uR, f0), (p.uR, f1), (p.uL, f1)], (0, -1, 0))
    else:
        _fondo_sul_fianco(p, quad, X, Zc, H, sp)

    inizio = len(T)
    # il piede della plancia: sul coperchio, o sul fondo dentro il retro,
    # sopra le strisce piegate sul fondo e staccata dalla parete
    piede, zh = H, Zc(vh)
    if dove_plancia == "fondo":
        # poggia sul fondo l'estremo piu' basso: la cerniera, o la cima
        # della parte ripiegata davanti, col pezzo di fronte che viene via
        # con lei, se e' piu' lunga della parte in piedi
        vmin = min([p.vT] + [v for _, v in p.taglio]
                   + ([_righe_plancia(p)[0][0], p.vF] if p.profilo else []))
        scende = max(0.0, (p.vM - vmin) - (vh - p.vM))
        piede, zh = 3.0 * sp + scende, max(zh, -D / 2 + 1.5 * sp)
    if p.profilo:
        _plancia_su(p, quad, X, zh, piede, sp)
        return np.array(V, float), np.array(UV, float), np.array(T, int), inizio
    # la plancia. Alzata sulla cerniera, che sta verso il retro, la parte
    # verso la cerniera sta in piedi e mostra la stampa a chi sta DIETRO, col
    # fronte del foglio in alto: la sua scritta, dritta sul foglio, si legge
    # da dietro. La parte verso il fronte si ripiega in avanti sulla riga di
    # mezzo e scende davanti, con la stampa verso chi guarda: la sua
    # scritta, capovolta sul foglio, si legge dritta. Il piede scende nella
    # finestra. Vedi REGOLE.md, *Il display a scatola*.
    a0, a1 = p.pl_u
    H = piede
    alto = vh - p.vM
    quad([(X(a0), H, zh), (X(a1), H, zh), (X(a1), H + alto, zh),
          (X(a0), H + alto, zh)],
         [(a0, vh), (a1, vh), (a1, p.vM), (a0, p.vM)], (0, 0, -1),
         coste=(1, 3))
    lun = p.vM - p.vT
    zd = zh + 2 * sp
    quad([(X(a0), H + alto, zd), (X(a1), H + alto, zd),
          (X(a1), H + alto - lun, zd), (X(a0), H + alto - lun, zd)],
         [(a0, p.vM), (a1, p.vM), (a1, p.vT), (a0, p.vT)], (0, 0, 1),
         coste=(1, 2, 3))
    return np.array(V, float), np.array(UV, float), np.array(T, int), inizio


def _righe_plancia(p):
    """Le righe della plancia sagomata, (v, da, a), dalla cima alla
    cerniera: il profilo, allungato fino al bordo del coperchio e fino alla
    cerniera."""
    righe = [(q[0], q[1], q[2]) for q in p.profilo if q[0] <= p.vH]
    if righe[-1][0] < p.vH:
        righe.append((p.vH,) + righe[-1][1:])
    if p.taglio and righe[0][0] > p.vF:
        righe.insert(0, (p.vF,) + righe[0][1:])
    return righe


def _a(righe, v):
    """La riga interpolata a v."""
    for r0, r1 in zip(righe[:-1], righe[1:]):
        if r0[0] <= v <= r1[0]:
            t = (v - r0[0]) / ((r1[0] - r0[0]) or 1.0)
            return (v, r0[1] + (r1[1] - r0[1]) * t, r0[2] + (r1[2] - r0[2]) * t)
    return min(righe, key=lambda r: abs(r[0] - v))


def _sagomata(p, quad, X, Zc, H, D, sp):
    """Il coperchio attorno alla finestra sagomata: a strisce lungo v, dal
    bordo del coperchio al bordo della finestra, da tutte e due le parti;
    dietro la cerniera, se non e' sul bordo, il coperchio intero."""
    righe = [(q[0], q[3], q[4]) for q in p.profilo if q[0] <= p.vH]
    righe = [(p.vF,) + righe[0][1:]] + righe
    if righe[-1][0] < p.vH:
        righe.append((p.vH,) + righe[-1][1:])
    for r0, r1 in zip(righe[:-1], righe[1:]):
        v0, v1 = r0[0], r1[0]
        quad([(X(p.uL), H, Zc(v1)), (X(p.uL), H, Zc(v0)), (X(r0[1]), H, Zc(v0)),
              (X(r1[1]), H, Zc(v1))],
             [(p.uL, v1), (p.uL, v0), (r0[1], v0), (r1[1], v1)], (0, 1, 0),
             coste=(2,))
        quad([(X(r1[2]), H, Zc(v1)), (X(r0[2]), H, Zc(v0)), (X(p.uR), H, Zc(v0)),
              (X(p.uR), H, Zc(v1))],
             [(r1[2], v1), (r0[2], v0), (p.uR, v0), (p.uR, v1)], (0, 1, 0),
             coste=(0,))
    if p.vH < p.vB - 0.5:
        quad([(X(p.uL), H, Zc(p.vB)), (X(p.uL), H, Zc(p.vH)),
              (X(p.uR), H, Zc(p.vH)), (X(p.uR), H, Zc(p.vB))],
             [(p.uL, p.vB), (p.uL, p.vH), (p.uR, p.vH), (p.uR, p.vB)],
             (0, 1, 0))


def _fondo_sul_fianco(p, quad, X, Zc, H, sp):
    """Il fondo attaccato al fianco: dalla piega in fondo al fianco fino
    all'altro fianco, con la stampa sotto. Il fianco e' piu' lungo della
    scatola: il di piu' sta sotto, sul fondo, una striscia doppia. La
    striscia del fianco di fronte si piega dentro, sul fondo."""
    fu, far = p.fondo_u
    da_sx = fu < p.uL
    piega = p.uL if da_sx else p.uR
    altra = p.uR if da_sx else p.uL
    verso = 1 if da_sx else -1          # dalla piega verso l'interno, in u
    zF, zB = Zc(p.vF), Zc(p.vB)
    quad([(X(piega), 0, zB), (X(piega), 0, zF), (X(altra), 0, zF),
          (X(altra), 0, zB)],
         [(fu, p.vB), (fu, p.vF), (far, p.vF), (far, p.vB)], (0, -1, 0))
    # il di piu' del fianco, sotto il fondo
    giu = piega - verso * H
    resto = abs(giu - fu)
    if resto > 1.0:
        xs, xe = X(piega), X(piega + verso * resto)
        y = -1.5 * sp
        quad([(xs, y, zB), (xs, y, zF), (xe, y, zF), (xe, y, zB)],
             [(giu, p.vB), (giu, p.vF), (fu, p.vF), (fu, p.vB)], (0, -1, 0),
             coste=(2,))
    if p.striscia:
        # dalla parete di fronte verso l'interno: il bordo vicino alla
        # parete sul foglio e' quello vicino alla sua piega
        vic, lon = sorted(p.striscia, key=lambda u: abs(u - altra))
        xs, xe = X(altra), X(altra - verso * abs(lon - vic))
        y = 2.5 * sp
        quad([(xs, y, zB), (xs, y, zF), (xe, y, zF), (xe, y, zB)],
             [(vic, p.vB), (vic, p.vF), (lon, p.vF), (lon, p.vB)], (0, -1, 0),
             coste=(2,))


def _plancia_su(p, quad, X, zh, H, sp):
    """La plancia sagomata alzata: dalla cerniera alla riga di mezzo in
    piedi, con la stampa verso il retro; dalla riga di mezzo alla cima
    ripiegata davanti, con la stampa verso chi guarda; la cima che entra
    nel fronte segue i suoi tagli (`_taglio`). Come la plancia diritta, a
    strisce lungo v."""
    righe = _righe_plancia(p)
    alto = p.vH - p.vM
    zd = zh + 2 * sp
    su = [r for r in righe if r[0] >= p.vM]
    giu = [r for r in righe if r[0] <= p.vM]
    m = _a(righe, p.vM)
    if not su or su[0][0] > p.vM:
        su.insert(0, m)
    if not giu or giu[-1][0] < p.vM:
        giu.append(m)

    def in_piedi(u, v):
        return (X(u), H + (p.vH - v), zh)

    def davanti(u, v):
        return (X(u), H + alto - (p.vM - v), zd)

    for parte, f, fuori in ((su, in_piedi, (0, 0, -1)), (giu, davanti, (0, 0, 1))):
        for r0, r1 in zip(parte[:-1], parte[1:]):
            if r1[0] - r0[0] < 1e-6:
                continue
            quad([f(r0[1], r0[0]), f(r0[2], r0[0]), f(r1[2], r1[0]),
                  f(r1[1], r1[0])],
                 [(r0[1], r0[0]), (r0[2], r0[0]), (r1[2], r1[0]),
                  (r1[1], r1[0])], fuori, coste=(1, 3))
    # la cima nel fronte: fra il bordo del coperchio e il taglio
    a, b = righe[0][1], righe[0][2]
    t = [(u, v) for u, v in p.taglio if v < p.vF - 0.05 and a <= u <= b]
    for (ua, va), (ub, vb) in zip(t[:-1], t[1:]):
        quad([davanti(ua, p.vF), davanti(ub, p.vF), davanti(ub, vb),
              davanti(ua, va)],
             [(ua, p.vF), (ub, p.vF), (ub, vb), (ua, va)], (0, 0, 1),
             coste=(2,))
