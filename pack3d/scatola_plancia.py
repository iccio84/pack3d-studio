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
    return tuple(out)


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
    return None


def dichiara(p):
    basso = p.vH - p.vM
    return ["display a scatola: scatola chiusa con la plancia ricavata dal "
            "coperchio",
            "scatola %.1f x %.1f x %.1f mm (larga x profonda x alta)"
            % (p.W, p.D, p.H),
            "plancia %.1f mm, alta %.1f mm sul coperchio, la parte verso il "
            "fronte (%.1f mm) ripiegata davanti; finestra nel coperchio "
            "%.1f x %.1f mm"
            % (p.pl_u[1] - p.pl_u[0], basso, p.vM - p.vT,
               p.buco_u[1] - p.buco_u[0], p.vH - max(p.vT, p.vF))]


def maglia(p, origine_mm, px_mm, misura_tex, spessore=None):
    """(V, UV, T, inizio_plancia) del display aperto, in mm, con la texture
    del DT intero e sotto le strisce del rovescio (`ballotin.con_interno`).
    Il fronte guarda +Z, la cima +Y, il fondo sta a Y = 0. I triangoli della
    plancia vengono per ultimi, da `inizio_plancia`: nel GLB sono un nodo a
    parte, e il riempimento misura il vano senza di lei."""
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
    pezzi_cop = [((p.uL, p.vF), (b0, p.vB), (2,)),       # a sinistra
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

    # i fianchi, giu' dai lati del coperchio
    for fuori_u, piega_u in ((p.uL - H, p.uL), (p.uR + H, p.uR)):
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
    quad([(X(p.uL), 0, -D / 2), (X(p.uR), 0, -D / 2), (X(p.uR), 0, D / 2),
          (X(p.uL), 0, D / 2)],
         [(p.uL, f0), (p.uR, f0), (p.uR, f1), (p.uL, f1)], (0, -1, 0))

    inizio = len(T)
    # la plancia. Alzata sulla cerniera, che sta verso il retro, la parte
    # verso la cerniera sta in piedi e mostra la stampa a chi sta DIETRO, col
    # fronte del foglio in alto: la sua scritta, dritta sul foglio, si legge
    # da dietro. La parte verso il fronte si ripiega in avanti sulla riga di
    # mezzo e scende davanti, con la stampa verso chi guarda: la sua
    # scritta, capovolta sul foglio, si legge dritta. Il piede scende nella
    # finestra. Vedi REGOLE.md, *Il display a scatola*.
    a0, a1 = p.pl_u
    zh = Zc(vh)
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
