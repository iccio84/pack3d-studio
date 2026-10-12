"""
I riempimenti: un vassoio espositore pieno dei suoi flowpack.

Due modelli costruiti ognuno dalla sua famiglia - il vassoio da
`pack3d.vassoio`, il flowpack da `build_flowpack` - e un GLB solo: il vassoio
com'e', e il flowpack una volta sola come maglia, richiamata da N nodi, uno per
pezzo, ognuno con la sua posa. La texture del flowpack c'e' una volta, e il
file resta leggero anche con quaranta pezzi.

La disposizione la decide il vano del vassoio:

- il vano e' l'ingombro del vassoio meno lo spessore del cartoncino; si
  impila fino alla parete piu' alta (su un display i fianchi bassi lasciano
  vedere il prodotto, le testate alte reggono la pila);
- il flowpack si misura sulla sua maglia: l'asse lungo, la sezione a meta' (il
  corpo pieno, rigonfiamento compreso) e la lunghezza del corpo, fin dove lo
  spessore resta oltre meta'. Le pinne sono film: piu' larghe del corpo e piu'
  lunghe del vano, si piegano e si accartocciano, e la disposizione non le
  conta;
- si provano le pose sdraiate - la faccia stampata in su, l'asse lungo per il
  largo o per il lungo del vano - e di taglio; vince la sdraiata, se i pezzi
  ci stanno, e fra due sdraiate quella con meno strati. Il KMS Raspberry T1x40: 8 barrette di
  traverso per 5 strati, 40 pezzi.

Poi il flowpack si adatta al vano, una volta per tutti i pezzi: le pinne si
stringono quanto il passo fra due pezzi, perche' due pinne sovrapposte sullo
stesso piano nel viewer sfarfallano, e le punte che uscirebbero dal vano si
piegano in su contro la parete, come fa il film vero.
"""
from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, field

import numpy as np

SPESSORE_VASSOIO = 1.0      # mm, come `vassoio.SPESSORE`
GIOCO = 0.6                 # mm fra le punte piegate e la parete
COMPRIME = 0.02             # quanto si schiaccia un pezzo gonfio fra i vicini
PIEGA_PINNA = math.radians(80.0)
SOGLIA_CORPO = 0.5          # il corpo finisce dove lo spessore scende sotto meta'


# --------------------------------------------------------------------------- #
# GLB: leggere e scrivere

def leggi(dati):
    """(json, bin) di un GLB."""
    if dati[:4] != b"glTF":
        raise ValueError("non e' un GLB")
    lunghezza = struct.unpack_from("<I", dati, 8)[0]
    off, J, B = 12, None, b""
    while off < lunghezza:
        n, tipo = struct.unpack_from("<II", dati, off)
        if tipo == 0x4E4F534A:
            J = json.loads(dati[off + 8:off + 8 + n].decode("utf-8"))
        elif tipo == 0x004E4942:
            B = dati[off + 8:off + 8 + n]
        off += 8 + n
    if J is None:
        raise ValueError("GLB senza JSON")
    return J, B


def scrivi(J, B):
    """I byte di un GLB da json e bin."""
    j = json.dumps(J, separators=(",", ":")).encode("utf-8")
    j += b" " * (-len(j) % 4)
    B = bytes(B) + b"\0" * (-len(B) % 4)
    totale = 12 + 8 + len(j) + 8 + len(B)
    return (struct.pack("<III", 0x46546C67, 2, totale)
            + struct.pack("<II", len(j), 0x4E4F534A) + j
            + struct.pack("<II", len(B), 0x004E4942) + B)


_TIPI = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
         5125: np.uint32, 5126: np.float32}
_N = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _dati(J, B, i):
    """L'accessor i come array (count x componenti)."""
    acc = J["accessors"][i]
    bv = J["bufferViews"][acc["bufferView"]]
    tipo = np.dtype(_TIPI[acc["componentType"]]).newbyteorder("<")
    k = _N[acc["type"]]
    a = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    passo = bv.get("byteStride") or tipo.itemsize * k
    righe = np.frombuffer(B, np.uint8, count=passo * (acc["count"] - 1) + tipo.itemsize * k,
                          offset=a)
    out = np.lib.stride_tricks.as_strided(
        righe, shape=(acc["count"], tipo.itemsize * k), strides=(passo, 1)).copy()
    return out.view(tipo).reshape(acc["count"], k)


def _matrice(nodo):
    """La matrice 4x4 di un nodo glTF."""
    if "matrix" in nodo:
        return np.array(nodo["matrix"], float).reshape(4, 4).T
    M = np.eye(4)
    if "scale" in nodo:
        M = np.diag(list(nodo["scale"]) + [1.0]) @ M
    if "rotation" in nodo:
        M = _da_quaternione(nodo["rotation"]) @ M
    if "translation" in nodo:
        T = np.eye(4)
        T[:3, 3] = nodo["translation"]
        M = T @ M
    return M


def _da_quaternione(q):
    x, y, z, w = q
    R = np.eye(4)
    R[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                 [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                 [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return R


def _quaternione(R):
    """[x, y, z, w] di una rotazione 3x3."""
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        return [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s,
                (R[1, 0] - R[0, 1]) / s, 0.25 * s]
    i = int(np.argmax(np.diag(R)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(1.0 + R[i, i] - R[j, j] - R[k, k]) * 2
    q = [0.0, 0.0, 0.0, 0.0]
    q[i] = 0.25 * s
    q[j] = (R[j, i] + R[i, j]) / s
    q[k] = (R[k, i] + R[i, k]) / s
    q[3] = (R[k, j] - R[j, k]) / s
    return q


def vertici(J, B):
    """Tutti i vertici della scena, in mm, nel riferimento della scena."""
    out = []

    def visita(i, M):
        nodo = J["nodes"][i]
        M = M @ _matrice(nodo)
        if "mesh" in nodo:
            for prim in J["meshes"][nodo["mesh"]]["primitives"]:
                P = _dati(J, B, prim["attributes"]["POSITION"]).astype(float)
                P = (np.c_[P, np.ones(len(P))] @ M.T)[:, :3]
                out.append(P)
        for c in nodo.get("children", []):
            visita(c, M)

    for r in J["scenes"][J.get("scene", 0)]["nodes"]:
        visita(r, np.eye(4))
    return np.vstack(out) * 1000.0


# --------------------------------------------------------------------------- #
# Le misure

@dataclass
class Vano:
    """Il vano del vassoio, in mm, nel riferimento della scena (Y in su)."""
    x0: float
    x1: float
    z0: float
    z1: float
    fondo: float            # la quota del piano su cui poggia il prodotto
    tetto: float            # fin dove si impila: la parete piu' alta

    @property
    def lati(self):
        return self.x1 - self.x0, self.z1 - self.z0, self.tetto - self.fondo


def misura_vassoio(J, B, spessore=SPESSORE_VASSOIO):
    V = vertici(J, B)
    lo, hi = V.min(0), V.max(0)
    return Vano(lo[0] + spessore, hi[0] - spessore, lo[2] + spessore, hi[2] - spessore,
                lo[1] + spessore, hi[1])


@dataclass
class Prodotto:
    """Il flowpack misurato sulla sua maglia, in mm. `assi` sono gli indici
    degli assi del suo riferimento: lungo, largo, spesso."""
    assi: tuple
    centro: np.ndarray
    lungo: float            # tutto, pinne comprese
    corpo: float            # fin dove lo spessore resta oltre meta'
    largo: float            # la sezione a meta'
    spesso: float
    largo_pinne: float
    fronte: int             # +1 se la faccia stampata guarda il verso + dello spessore


def misura_prodotto(J, B):
    V = vertici(J, B)
    lo, hi = V.min(0), V.max(0)
    ampi = hi - lo
    lungo = int(np.argmax(ampi))
    altri = [a for a in range(3) if a != lungo]
    centro = (lo + hi) / 2.0
    x = V[:, lungo] - centro[lungo]
    meta = np.abs(x) < max(2.0, 0.03 * ampi[lungo])
    sezione = V[meta][:, altri]
    sez = sezione.max(0) - sezione.min(0)
    spesso_i = altri[int(np.argmin(sez))]
    largo_i = altri[int(np.argmax(sez))]
    spesso, largo = float(sez.min()), float(sez.max())
    # il corpo: fin dove lo spessore resta oltre meta' di quello a meta'
    passo = max(0.5, ampi[lungo] / 400.0)
    fine = 0.0
    for s in np.arange(0.0, ampi[lungo] / 2.0, passo):
        fetta = np.abs(np.abs(x) - s) < passo
        if not fetta.any():
            continue
        if np.ptp(V[fetta, spesso_i]) >= SOGLIA_CORPO * spesso:
            fine = s
    pinne = np.abs(x) > fine
    largo_pinne = float(np.ptp(V[pinne, largo_i])) if pinne.any() else largo
    # la faccia stampata: nel riferimento dei modelli di pack3d il fronte guarda
    # +Z; per un prodotto girato diversamente vale il verso + dello spessore
    return Prodotto((lungo, largo_i, spesso_i), centro, float(ampi[lungo]),
                    float(2.0 * fine), largo, spesso, largo_pinne, +1)


# --------------------------------------------------------------------------- #
# La disposizione

@dataclass
class Disposizione:
    posa: str               # a parole
    lungo_su: int           # l'asse della scena lungo cui va l'asse lungo (0 = X, 2 = Z)
    verticale: str          # "spesso" (sdraiato) o "largo" (di taglio)
    per_fila: int           # pezzi lungo l'asse lungo del prodotto
    file: int               # file affiancate
    strati: int
    passo_lungo: float
    passo_fila: float
    passo_strato: float
    capienza: int
    pose: list = field(default_factory=list)    # (R 3x3, t mm) per pezzo

    @property
    def per_strato(self):
        return self.per_fila * self.file


def disposizioni(vano, p):
    """Le pose possibili, la migliore prima."""
    L, Wv, H = vano.lati
    out = []
    for verticale in ("spesso", "largo"):
        alto = p.spesso if verticale == "spesso" else p.largo
        fianco = p.largo if verticale == "spesso" else p.spesso
        for lungo_su in (0, 2):
            lungo_vano = L if lungo_su == 0 else Wv
            fianco_vano = Wv if lungo_su == 0 else L
            # in fila, le pinne di due pezzi vicini non si compenetrano: solo
            # quelle contro le due pareti si piegano
            pinne = p.lungo - p.corpo
            per_fila = int((lungo_vano + pinne) // p.lungo) if lungo_vano >= p.corpo else 0
            file = int(fianco_vano // (fianco * (1.0 - COMPRIME)))
            strati = int(H // (alto * (1.0 - COMPRIME)))
            if per_fila < 1 or file < 1 or strati < 1:
                continue
            out.append(Disposizione(
                ("sdraiati" if verticale == "spesso" else "di taglio")
                + (", per il largo del vassoio" if lungo_su == 0 else ", per il lungo del vassoio"),
                lungo_su, verticale, per_fila, file, strati,
                lungo_vano / per_fila, fianco_vano / file, min(alto, H / strati),
                per_fila * file * strati))
    return out


def scegli(vano, p, quanti):
    """La disposizione per `quanti` pezzi, o None se non ci stanno in nessuna
    posa (allora la capienza massima e' quella della prima di `disposizioni`)."""
    cand = disposizioni(vano, p)
    buone = [d for d in cand if d.capienza >= quanti]
    if not buone:
        return None, max((d.capienza for d in cand), default=0)
    # sdraiati quando ci stanno, come si espone; poi meno strati
    buone.sort(key=lambda d: (d.verticale != "spesso", -(-quanti // d.per_strato),
                              -d.per_strato))
    return buone[0], buone[0].capienza


def capienza(vano, p):
    cand = disposizioni(vano, p)
    return max((d.capienza for d in cand), default=0)


def _rotazione(p, d):
    """La rotazione che porta il riferimento del prodotto nella posa: l'asse
    lungo lungo X o Z della scena; sdraiato, lo spessore in su con la faccia
    stampata sopra; di taglio, la larghezza in su. Le colonne di R sono gli
    assi del prodotto visti nella scena."""
    lungo, largo, spesso = p.assi
    su = spesso if d.verticale == "spesso" else largo
    terzo = largo if d.verticale == "spesso" else spesso
    e = np.eye(3)
    R = np.zeros((3, 3))
    R[:, lungo] = e[d.lungo_su]
    R[:, su] = e[1] * (p.fronte if d.verticale == "spesso" else 1.0)
    R[:, terzo] = e[2 if d.lungo_su == 0 else 0]
    if np.linalg.det(R) < 0:
        R[:, terzo] = -R[:, terzo]
    return R


def pose(vano, p, d, quanti, V_prodotto):
    """Le pose dei `quanti` pezzi: (R, t) in mm. Si riempie dal basso, strato
    per strato; l'ultimo strato, se non e' pieno, ha i pezzi al centro."""
    R = _rotazione(p, d)
    W = (V_prodotto - p.centro) @ R.T
    base = -W[:, 1].min()               # il pezzo poggia sul piano
    lungo_vano = (vano.x0, vano.x1) if d.lungo_su == 0 else (vano.z0, vano.z1)
    fianco_vano = (vano.z0, vano.z1) if d.lungo_su == 0 else (vano.x0, vano.x1)
    posti = []
    for s in range(d.strati):
        strato = []
        for f in range(d.file):
            for k in range(d.per_fila):
                strato.append((s, f, k))
        posti.append(strato)
    scelti = []
    resto = quanti
    for strato in posti:
        if resto <= 0:
            break
        if resto >= len(strato):
            scelti.extend(strato)
            resto -= len(strato)
        else:
            # i posti piu' vicini al centro, in ordine
            c_f, c_k = (d.file - 1) / 2.0, (d.per_fila - 1) / 2.0
            ordine = sorted(strato, key=lambda q: (abs(q[1] - c_f) + abs(q[2] - c_k), q[1], q[2]))
            scelti.extend(sorted(ordine[:resto]))
            resto = 0
    out = []
    for s, f, k in scelti:
        a = lungo_vano[0] + (k + 0.5) * d.passo_lungo
        b = fianco_vano[0] + (f + 0.5) * d.passo_fila
        y = vano.fondo + base + s * d.passo_strato
        t = np.array([a, y, b]) if d.lungo_su == 0 else np.array([b, y, a])
        out.append((R, t - R @ np.zeros(3)))
    return out, R


# --------------------------------------------------------------------------- #
# Il prodotto adattato al vano

def adatta(P, N, p, d, vano):
    """Posizioni e normali del prodotto (mm, nel suo riferimento) con le
    pinne strette quanto il passo fra due file e le punte piegate in su dove
    uscirebbero dal vano. Torna (P, N, quante pinne piegate)."""
    lungo, largo, spesso = p.assi
    fianco_i = largo if d.verticale == "spesso" else spesso
    su_i = spesso if d.verticale == "spesso" else largo
    P = P.copy()
    N = N.copy() if N is not None else None
    x = P[:, lungo] - p.centro[lungo]
    fine = p.corpo / 2.0
    # 1. le pinne non piu' larghe del passo fra due file
    fianco = p.largo if d.verticale == "spesso" else p.spesso
    largo_pinne = p.largo_pinne if d.verticale == "spesso" else fianco
    k = min(1.0, (d.passo_fila - GIOCO) / max(largo_pinne, 1e-6))
    if k < 1.0:
        sfuma = np.clip((np.abs(x) - fine) / max(0.25 * (p.lungo / 2.0 - fine), 1e-6), 0.0, 1.0)
        f = 1.0 - (1.0 - k) * sfuma
        c = p.centro[fianco_i]
        P[:, fianco_i] = c + (P[:, fianco_i] - c) * f
    # 2. le punte che uscirebbero dal vano, piegate in su contro la parete
    meta_vano = d.passo_lungo / 2.0 - GIOCO
    piegate = 0
    if p.lungo / 2.0 > meta_vano and meta_vano > fine:
        c_su = p.centro[su_i]
        alto = p.fronte if d.verticale == "spesso" else 1.0    # dov'e' su
        for segno in (1.0, -1.0):
            m = segno * x > meta_vano
            if not m.any():
                continue
            piegate += 1
            dx = segno * x[m] - meta_vano
            dz = (P[m, su_i] - c_su) * alto
            cs, sn = math.cos(PIEGA_PINNA), math.sin(PIEGA_PINNA)
            P[m, lungo] = p.centro[lungo] + segno * (meta_vano + dx * cs - dz * sn)
            P[m, su_i] = c_su + alto * (dx * sn + dz * cs)
            if N is not None:
                nl, ns = N[m, lungo] * segno, N[m, su_i] * alto
                N[m, lungo] = segno * (nl * cs - ns * sn)
                N[m, su_i] = alto * (nl * sn + ns * cs)
    return P, N, piegate


# --------------------------------------------------------------------------- #
# Il GLB composto

def componi(glb_vassoio, glb_prodotto, quanti=None):
    """Il GLB del vassoio con `quanti` pezzi dentro (None: pieno, quanti ne
    stanno). Torna (byte, righe da mostrare). Se ne chiedi piu' di quanti ne
    stanno, mette quelli che ci stanno e lo dice; ValueError se non ce ne sta
    neanche uno."""
    Jv, Bv = leggi(glb_vassoio)
    Jp, Bp = leggi(glb_prodotto)
    # il flowpack si misura nella scena e si adatta nella sua maglia: valgono
    # insieme solo se i suoi nodi non spostano niente, come li fa build_flowpack
    if any(k in n for n in Jp.get("nodes", [])
           for k in ("matrix", "rotation", "translation", "scale")):
        raise ValueError("riempimento: il GLB del flowpack ha nodi trasformati")
    vano = misura_vassoio(Jv, Bv)
    p = misura_prodotto(Jp, Bp)
    chiesti = quanti
    massimo = capienza(vano, p)
    if massimo < 1:
        raise ValueError("riempimento: nel vano del vassoio (%.0f x %.0f x %.0f mm) il "
                         "flowpack (%.0f x %.0f x %.0f mm) non ci sta in nessuna posa"
                         % (vano.lati + (p.lungo, p.largo, p.spesso)))
    if quanti is None or quanti > massimo:
        # pieno: la posa sdraiata, se c'e', anche se di taglio ne starebbero di piu'
        sdraiati = max((c.capienza for c in disposizioni(vano, p) if c.verticale == "spesso"),
                       default=0)
        quanti = massimo if quanti is not None else (sdraiati or massimo)
    d, cap = scegli(vano, p, quanti)
    Vp = vertici(Jp, Bp)
    poste, R = pose(vano, p, d, quanti, Vp)

    J = json.loads(json.dumps(Jv))
    B = bytearray(Bv)

    def allinea():
        B.extend(b"\0" * (-len(B) % 4))

    # il prodotto: le sue parti accodate a quelle del vassoio, con gli indici
    # spostati
    sposta = {k: len(J.get(k, [])) for k in ("bufferViews", "accessors", "images",
                                            "samplers", "textures", "materials", "meshes",
                                            "nodes")}
    allinea()
    base = len(B)
    B.extend(Bp)
    for bv in Jp.get("bufferViews", []):
        bv = dict(bv, buffer=0, byteOffset=bv.get("byteOffset", 0) + base)
        J.setdefault("bufferViews", []).append(bv)
    for acc in Jp.get("accessors", []):
        J.setdefault("accessors", []).append(
            dict(acc, bufferView=acc["bufferView"] + sposta["bufferViews"]))
    for im in Jp.get("images", []):
        J.setdefault("images", []).append(
            dict(im, bufferView=im["bufferView"] + sposta["bufferViews"]) if "bufferView" in im else im)
    for s in Jp.get("samplers", []):
        J.setdefault("samplers", []).append(s)
    for t in Jp.get("textures", []):
        t = dict(t)
        if "source" in t:
            t["source"] += sposta["images"]
        if "sampler" in t:
            t["sampler"] += sposta["samplers"]
        J.setdefault("textures", []).append(t)

    def rinumera(o):
        if isinstance(o, dict):
            return {k: (v + sposta["textures"] if k == "index" and isinstance(v, int)
                        else rinumera(v)) for k, v in o.items()}
        if isinstance(o, list):
            return [rinumera(v) for v in o]
        return o

    for m in Jp.get("materials", []):
        J.setdefault("materials", []).append(rinumera(m))
    piegate = 0
    for me in Jp.get("meshes", []):
        me = json.loads(json.dumps(me))
        for prim in me["primitives"]:
            a = prim["attributes"]
            P = _dati(Jp, Bp, a["POSITION"]).astype(float) * 1000.0
            Nn = _dati(Jp, Bp, a["NORMAL"]).astype(float) if "NORMAL" in a else None
            P2, N2, piegate = adatta(P, Nn, p, d, vano)
            for nome, arr in (("POSITION", P2 / 1000.0), ("NORMAL", N2)):
                if arr is None:
                    continue
                if nome == "NORMAL":
                    arr = arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-9)
                arr = np.ascontiguousarray(arr, dtype="<f4")
                allinea()
                J["bufferViews"].append({"buffer": 0, "byteOffset": len(B),
                                         "byteLength": arr.nbytes, "target": 34962})
                B.extend(arr.tobytes())
                acc = {"bufferView": len(J["bufferViews"]) - 1, "componentType": 5126,
                       "count": len(arr), "type": "VEC3"}
                if nome == "POSITION":
                    acc["min"] = arr.min(0).tolist()
                    acc["max"] = arr.max(0).tolist()
                J["accessors"].append(acc)
                a[nome] = len(J["accessors"]) - 1
            for k, v in list(a.items()):
                if k not in ("POSITION", "NORMAL"):
                    a[k] = v + sposta["accessors"]
            if "indices" in prim:
                prim["indices"] += sposta["accessors"]
            if "material" in prim:
                prim["material"] += sposta["materials"]
        J["meshes"].append(me)

    # un nodo per pezzo, con sotto una copia dei nodi del prodotto
    radici = Jp["scenes"][Jp.get("scene", 0)]["nodes"]

    def copia(i):
        n = json.loads(json.dumps(Jp["nodes"][i]))
        if "mesh" in n:
            n["mesh"] += sposta["meshes"]
        figli = [copia(c) for c in n.get("children", [])]
        if figli:
            n["children"] = figli
        J["nodes"].append(n)
        return len(J["nodes"]) - 1

    scena = J["scenes"][J.get("scene", 0)]["nodes"]
    q = _quaternione(R)
    for k, (_R, t) in enumerate(poste):
        figli = [copia(r) for r in radici]
        # t e' dove va il centro del prodotto: il nodo sposta prima il centro
        # nell'origine
        tt = t - R @ p.centro
        J["nodes"].append({"name": "pezzo %d" % (k + 1), "children": figli,
                           "rotation": [float(v) for v in q],
                           "translation": [float(v) / 1000.0 for v in tt]})
        scena.append(len(J["nodes"]) - 1)
    J["buffers"] = [{"byteLength": len(B) + (-len(B) % 4)}]
    for chiave in ("extensionsUsed", "extensionsRequired"):
        u = sorted(set(Jv.get(chiave, [])) | set(Jp.get(chiave, [])))
        if u:
            J[chiave] = u
    righe = []
    if chiesti is not None and chiesti > quanti:
        righe.append("ne hai chiesti %d, ma nel vassoio ce ne stanno al massimo %d: "
                     "ne ho messi %d" % (chiesti, massimo, quanti))
    strati = -(-quanti // d.per_strato)
    righe += ["riempimento: %d %s nel vassoio%s, %s"
              % (quanti, "pezzo" if quanti == 1 else "pezzi",
                 " (pieno)" if chiesti is None else "", d.posa),
             "%d per strato (%d x %d), %d %s: ce ne stanno fino a %d"
             % (d.per_strato, d.file, d.per_fila, strati,
                "strato" if strati == 1 else "strati", d.capienza),
             "vano %.1f x %.1f mm, alto fino a %.1f; pezzo %.1f x %.1f x %.1f (corpo %.1f)"
             % (vano.lati[0], vano.lati[1], vano.lati[2], p.lungo, p.largo, p.spesso, p.corpo)]
    if piegate:
        righe.append("pinne piu' lunghe del vano: le punte si piegano in su contro la parete")
    if d.verticale != "spesso":
        sdraiati = max((c.capienza for c in disposizioni(vano, p) if c.verticale == "spesso"),
                       default=0)
        righe.append("di taglio perche' sdraiati ce ne stanno al massimo %d" % sdraiati)
    if d.verticale == "spesso" and p.largo_pinne > d.passo_fila:
        righe.append("pinne piu' larghe del passo fra due pezzi (%.1f contro %.1f): si "
                     "stringono come il film accartocciato" % (p.largo_pinne, d.passo_fila))
    return scrivi(J, bytes(B)), righe
