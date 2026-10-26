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
- i pack stanno frontali: la faccia stampata verso il davanti del vassoio e il
  marchio dritto, come stanno nel loro modello, in file dal davanti al fondo e
  a strati uguali. Il KMS Raspberry T1x40: 2 file da 20, una sull'altra.
  Sdraiati, la faccia in su, solo se in piedi non ci stanno, o se i pezzi
  contati frontali vengono a strati diversi e sdraiati fanno una griglia
  piena (`_griglia`, il T15: 5 x 3). Sdraiati stanno in piano: inclinati
  all'indietro la faccia non tornava piu' col DT (il T15: «annullare
  l'inclinazione»).

Poi il flowpack si adatta al vano, una volta per tutti i pezzi: le pinne si
stringono quanto il passo fra due pezzi, perche' due pinne sovrapposte sullo
stesso piano nel viewer sfarfallano, e le punte che uscirebbero dal vano si
piegano sullo spessore contro la parete, come fa il film vero.
"""
from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, replace

import numpy as np

SPESSORE_VASSOIO = 1.0      # mm, come `vassoio.SPESSORE`
GIOCO = 0.6                 # mm fra le punte piegate e la parete
COMPRIME = 0.02             # quanto si schiaccia un pezzo gonfio fra i vicini
PIEGA_PINNA = math.radians(80.0)
SOGLIA_CORPO = 0.5          # il corpo finisce dove lo spessore scende sotto meta'
PASSO_MAX = 1.2             # in fila, al massimo un quinto di spessore d'aria fra due pezzi
SCHIACCIA_MAX = 0.25        # nel display fatto per N pezzi, un flowpack gonfio si schiaccia al massimo cosi'


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


def vertici(J, B, senza=()):
    """I vertici della scena, in mm, nel riferimento della scena: quelli che
    i triangoli usano davvero, senza i nodi che si chiamano come `senza`. Il
    display e la sua plancia stanno sugli stessi vertici, e si distinguono
    solo dai triangoli."""
    out = []

    def visita(i, M):
        nodo = J["nodes"][i]
        if nodo.get("name") in senza:
            return
        M = M @ _matrice(nodo)
        if "mesh" in nodo:
            for prim in J["meshes"][nodo["mesh"]]["primitives"]:
                P = _dati(J, B, prim["attributes"]["POSITION"]).astype(float)
                if "indices" in prim:
                    P = P[np.unique(_dati(J, B, prim["indices"]).ravel())]
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

    @property
    def per_asse(self):
        """Le misure lungo X, Y (l'altezza) e Z della scena."""
        return self.x1 - self.x0, self.tetto - self.fondo, self.z1 - self.z0


def misura_vassoio(J, B, spessore=SPESSORE_VASSOIO):
    # del display conta la scatola: la plancia sta dietro, in alto, e non
    # contiene niente
    V = vertici(J, B, senza=("plancia",))
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
    rigido: bool = False    # un astuccio: niente pinne, e non si schiaccia
    accorcia: float = 1.0   # quanto e' stato accorciato lungo l'asse lungo: vedi `accorcia`
    schiaccia: float = 1.0  # quanto e' stato schiacciato nello spessore: vedi `schiaccia`


def misura_prodotto(J, B, rigido=False):
    V = vertici(J, B)
    lo, hi = V.min(0), V.max(0)
    ampi = hi - lo
    if rigido:
        # un astuccio e' il suo ingombro: le facce sono quadrilateri grandi,
        # e a meta' non ha vertici da cui leggere una sezione
        lungo, largo_i, spesso_i = (int(i) for i in np.argsort(-ampi))
        return Prodotto((lungo, largo_i, spesso_i), (lo + hi) / 2.0, float(ampi[lungo]),
                        float(ampi[lungo]), float(ampi[largo_i]), float(ampi[spesso_i]),
                        float(ampi[largo_i]), +1, True)
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
    """Come stanno i pezzi nel vano. `R` porta il riferimento del prodotto
    nella scena: le sue colonne sono gli assi del prodotto visti nella scena.
    `n` e' quanti pezzi stanno al massimo lungo X, Y e Z della scena, `passo`
    a che distanza; `piega` il verso, lungo lo spessore del prodotto, in cui
    si piegano le punte delle pinne."""
    posa: str               # "frontali" o "sdraiati"
    dove: str               # a parole
    R: np.ndarray
    n: tuple
    passo: tuple
    piega: float

    @property
    def capienza(self):
        return self.n[0] * self.n[1] * self.n[2]

    @property
    def per_strato(self):
        return self.n[0] * self.n[2]

    def asse(self, j):
        """L'asse della scena lungo cui va l'asse j del prodotto."""
        return int(np.argmax(np.abs(self.R[:, j])))


def _misura(p, j):
    """La misura del prodotto lungo il suo asse j: tutto per il lungo, il
    corpo per gli altri due."""
    lungo, largo, _ = p.assi
    return p.lungo if j == lungo else p.largo if j == largo else p.spesso


def _quanti_lungo(lato, p, j):
    """Quanti pezzi stanno in fila su un lato del vano, con l'asse j del
    prodotto lungo quel lato. Per il lungo conta la lunghezza intera, ma le
    pinne di due pezzi vicini non si compenetrano: solo quelle contro le due
    pareti si piegano. Gli altri due lati si schiacciano un poco."""
    if j == p.assi[0]:
        return int((lato + p.lungo - p.corpo) // p.lungo) if lato >= p.corpo else 0
    return int(lato // (_misura(p, j) * (1.0 - (0.0 if p.rigido else COMPRIME))))


def _disposizione(vano, p, posa, dove, R, piega):
    lati = vano.per_asse
    n, passo = [], []
    for a in range(3):
        j = int(np.argmax(np.abs(R[a, :])))
        n.append(_quanti_lungo(lati[a], p, j))
        if a == 1 and n[-1] == 0:
            # piu' alto delle pareti: sta in piedi lo stesso, e sporge, come
            # il T10 nel suo vassoio da 40 mm. Le pareti tengono il piede
            n[-1] = 1
        # in altezza gli strati si appoggiano uno sull'altro; di lato e in
        # profondita' si allargano su tutto il vano
        passo.append(lati[a] / max(n[-1], 1) if a != 1
                     else _misura(p, j) if _misura(p, j) > lati[1]
                     else min(_misura(p, j), lati[1] / max(n[-1], 1)))
    if min(n) < 1:
        return None
    return Disposizione(posa, dove, R, tuple(n), tuple(passo), piega)


def disposizioni(vano, p):
    """Le pose possibili, la migliore prima.

    Frontali: il pezzo sta nel vassoio come sta nel suo modello, con la faccia
    stampata verso il davanti del vassoio e il marchio dritto; le file vanno
    dal davanti al fondo. E' cosi' che si espone, e si prova per prima.
    Sdraiati, la faccia stampata in su, solo se in piedi non ci stanno."""
    lungo, largo, spesso = p.assi
    out = []
    d = _disposizione(vano, p, "frontali", "la faccia stampata verso il davanti, il marchio dritto",
                      np.eye(3), -float(p.fronte))
    if d:
        out.append(d)
    e = np.eye(3)
    for lungo_su in (0, 2):
        R = np.zeros((3, 3))
        R[:, lungo] = e[lungo_su]
        R[:, spesso] = e[1] * p.fronte
        R[:, largo] = e[2 if lungo_su == 0 else 0]
        if np.linalg.det(R) < 0:
            R[:, largo] = -R[:, largo]
        d = _disposizione(vano, p, "sdraiati",
                          "la faccia stampata in su, " + ("per il largo del vassoio"
                                                          if lungo_su == 0 else
                                                          "per il lungo del vassoio"),
                          R, float(p.fronte))
        if d:
            out.append(d)
    return out


def scegli(vano, p, quanti):
    """La disposizione per `quanti` pezzi (None: pieno), o None se il prodotto
    non ci sta in nessuna posa. Frontali sempre, se in piedi ci stanno: se ne
    chiedi di piu', si mettono quelli che ci stanno. Sdraiati, quella che li
    tiene tutti con meno strati, o la piu' capiente."""
    cand = disposizioni(vano, p)
    if not cand:
        return None
    if cand[0].posa == "frontali":
        g = None if quanti is None else _griglia(cand, quanti)
        return g or cand[0]
    if quanti is None:
        return max(cand, key=lambda d: d.capienza)
    buone = [d for d in cand if d.capienza >= quanti]
    if not buone:
        return max(cand, key=lambda d: d.capienza)
    buone.sort(key=lambda d: (-(-quanti // d.per_strato), -d.per_strato))
    return buone[0]


def _griglia(cand, quanti):
    """Il display e' fatto per il suo numero: `quanti` pezzi stanno in una
    griglia piena, a per strato e s strati. Se frontali vengono a strati
    diversi (15: 8 e 7) e una posa sdraiata li mette in strati tutti uguali
    e pieni (15: 5 x 3), si prende quella, con meno strati. La disposizione
    torna con i pezzi di uno strato allargati su tutto il vano. None se
    frontali vanno gia' bene, o se nessuna posa fa la griglia."""
    fr = cand[0]
    if len(set(_strati(fr, quanti))) <= 1 and quanti <= fr.capienza:
        return None
    migliore = None
    for d in cand[1:]:
        nx, ny, nz = d.n
        for s in range(1, ny + 1):
            if quanti % s:
                continue
            a = quanti // s
            for gx in range(min(nx, a), 0, -1):
                if a % gx or a // gx > nz:
                    continue
                gz = a // gx
                if migliore is None or (s, -a) < (migliore[0], -migliore[1]):
                    migliore = (s, a, d, gx, gz)
                break
    if migliore is None:
        return None
    s, a, d, gx, gz = migliore
    lx, lz = d.passo[0] * d.n[0], d.passo[2] * d.n[2]
    return Disposizione(d.posa, d.dove + ", %d x %d" % (a, s), d.R, (gx, d.n[1], gz),
                        (lx / gx, d.passo[1], lz / gz), d.piega)


def accorcia(vano, p):
    """Il flowpack ACCORCIATO quanto basta per stare nel vano, con la sua
    disposizione: `(prodotto, disposizione)`, o None.

    Serve quando il corpo e' piu' lungo di ogni lato del vano e non c'e' posa
    in cui stia: il caso e1b3cc77a7, un flowpack con 119 mm di corpo in una
    scatola da 79 x 109 mm. Chi l'ha caricato ha chiesto di schiacciarlo
    finche' non entra: il film si accartoccia, e nel modello il pezzo si
    accorcia lungo il suo asse lungo, pinne e corpo insieme, fino al lato del
    vano su cui va. Le pose si provano nell'ordine di sempre - frontali, poi
    sdraiati - e vince la prima in cui, accorciato, il pezzo ci sta: cosi'
    si espone come gli altri riempimenti, anche se costa accorciarlo di piu'.
    Un astuccio non si schiaccia."""
    if p.rigido:
        return None
    lungo = p.assi[0]
    lati = vano.per_asse
    # il lato del vano su cui va l'asse lungo: frontali come sta nel suo
    # modello, sdraiati per il largo o per il lungo del vassoio
    for posa, a in (("frontali", lungo), ("sdraiati", 0), ("sdraiati", 2)):
        if lati[a] >= p.corpo or lati[a] <= 0:
            continue
        # il corpo un poco piu' corto del lato: le punte delle pinne si
        # piegano contro la parete a `GIOCO` da lei (`adatta`), e con il corpo
        # lungo quanto il lato non c'era dove piegarle, e uscivano dal vano
        k = (lati[a] - 4.0 * GIOCO) / p.corpo
        q = Prodotto(p.assi, p.centro, p.lungo * k, p.corpo * k, p.largo,
                     p.spesso, p.largo_pinne, p.fronte, p.rigido,
                     p.accorcia * k)
        for d in disposizioni(vano, q):
            if d.posa == posa and d.asse(lungo) == a:
                return q, d
    return None


def schiaccia(vano, p, quanti, posa):
    """Il flowpack SCHIACCIATO nello spessore quanto basta perche' ci stiano
    i `quanti` pezzi chiesti, con la sua disposizione: `(prodotto,
    disposizione)`, o None.

    Un display e' fatto per il suo numero, e i flowpack, pieni d'aria, ci
    stanno stretti: si schiacciano fra i vicini. Col rigonfiamento nello
    spessore il flowpack e' piu' spesso di prima, e il vassoio da 40 ne
    teneva 38 (20,5 mm invece di 17), il display da 26 ne teneva 20 (20
    invece di 16,5). Lo spessore cala a passi di mezzo per cento finche' ci
    stanno tutti, al massimo di `SCHIACCIA_MAX`; oltre, il pezzo e' davvero
    troppo grande e se ne mettono meno, come prima. La posa resta `posa`,
    quella del pezzo non schiacciato: il vassoio da 40, frontale, al primo
    mezzo per cento trovava sdraiati una griglia 8 x 5. Un astuccio non si
    schiaccia."""
    if p.rigido or quanti is None:
        return None
    k = 1.0
    while k > 1.0 - SCHIACCIA_MAX + 1e-9:
        k -= 0.005
        q = replace(p, spesso=p.spesso * k, schiaccia=p.schiaccia * k)
        d = scegli(vano, q, quanti)
        if d is not None and d.posa == posa and d.capienza >= quanti:
            return q, d
    return None


def capienza(vano, p):
    d = scegli(vano, p, None)
    return d.capienza if d else 0


def _strati(d, quanti):
    """Quanti pezzi per strato, dal basso. Frontali: strati uguali, 40 in due
    strati fanno 20 e 20 (se avanzano, uno in piu' sotto). Sdraiati: strati
    pieni, e l'ultimo con quelli che restano."""
    s = -(-quanti // d.per_strato)
    if d.posa == "frontali":
        return [quanti // s + (1 if k < quanti % s else 0) for k in range(s)]
    return [min(d.per_strato, quanti - k * d.per_strato) for k in range(s)]


def pose(vano, p, d, quanti, V_prodotto):
    """Le pose dei `quanti` pezzi: (R, t) in mm, con t dove va il centro del
    prodotto. `V_prodotto` sono i vertici del prodotto gia' adattato al vano:
    il pezzo poggia sul piano col corpo, non con le pinne."""
    R = d.R
    W = (V_prodotto - p.centro) @ R.T
    base = -W[:, 1].min()
    nx, _, nz = d.n
    out = []
    for s, c in enumerate(_strati(d, quanti)):
        y = vano.fondo + base + s * d.passo[1]
        if d.posa == "frontali":
            # le file dal davanti al fondo, allargate su tutta la profondita':
            # al massimo un quinto di spessore d'aria fra due pezzi, se no si
            # appoggiano al davanti
            righe = -(-c // nx)
            pz = min(vano.per_asse[2] / righe, _misura(p, int(np.argmax(np.abs(R[2, :]))))
                     * PASSO_MAX)
            posti = [(r, f) for r in range(righe) for f in range(nx)]
            dove = lambda r, f: (vano.x0 + (f + 0.5) * d.passo[0], vano.z1 - (r + 0.5) * pz)
        else:
            posti = [(r, f) for r in range(nz) for f in range(nx)]
            dove = lambda r, f: (vano.x0 + (f + 0.5) * d.passo[0],
                                 vano.z0 + (r + 0.5) * d.passo[2])
        if c < len(posti):
            # i posti piu' vicini al centro della fila o dello strato
            cr = (max(r for r, _ in posti)) / 2.0
            cf = (nx - 1) / 2.0
            if d.posa == "frontali":
                pieni = [q for q in posti if q[0] < c // nx]
                resto = sorted((q for q in posti if q[0] == c // nx),
                               key=lambda q: (abs(q[1] - cf), q[1]))[:c - len(pieni)]
                posti = pieni + sorted(resto)
            else:
                posti = sorted(sorted(posti, key=lambda q: (abs(q[0] - cr) + abs(q[1] - cf),
                                                            q))[:c])
        for r, f in posti:
            x, z = dove(r, f)
            out.append((R, np.array([x, y, z])))
    return out


# --------------------------------------------------------------------------- #
# Il prodotto adattato al vano

def adatta(P, N, p, d):
    """Posizioni e normali del prodotto (mm, nel suo riferimento) con le
    pinne strette quanto il passo fra due pezzi lungo la loro larghezza, e le
    punte che uscirebbero dal posto del pezzo piegate contro la parete:
    sdraiati in su, frontali verso il dietro. Torna (P, N, quante pinne
    piegate)."""
    lungo, largo, spesso = p.assi
    P = P.copy()
    N = N.copy() if N is not None else None
    # 0. accorciato, se nel vano non stava in nessuna posa: vedi `accorcia`
    if p.accorcia != 1.0:
        P[:, lungo] = p.centro[lungo] + (P[:, lungo] - p.centro[lungo]) * p.accorcia
        if N is not None:
            N[:, lungo] = N[:, lungo] / p.accorcia
    # 0. schiacciato nello spessore, se no i pezzi chiesti non ci stavano:
    # vedi `schiaccia`
    if p.schiaccia != 1.0:
        P[:, spesso] = p.centro[spesso] + (P[:, spesso] - p.centro[spesso]) * p.schiaccia
        if N is not None:
            N[:, spesso] = N[:, spesso] / p.schiaccia
    x = P[:, lungo] - p.centro[lungo]
    fine = p.corpo / 2.0
    # 1. le pinne non piu' larghe del passo fra due pezzi: due pinne vicine
    # sullo stesso piano nel viewer sfarfallano
    k = min(1.0, (d.passo[d.asse(largo)] - GIOCO) / max(p.largo_pinne, 1e-6))
    if k < 1.0:
        sfuma = np.clip((np.abs(x) - fine) / max(0.25 * (p.lungo / 2.0 - fine), 1e-6), 0.0, 1.0)
        f = 1.0 - (1.0 - k) * sfuma
        c = p.centro[largo]
        P[:, largo] = c + (P[:, largo] - c) * f
    # 2. le punte che uscirebbero, piegate sullo spessore come il film vero
    meta = d.passo[d.asse(lungo)] / 2.0 - GIOCO
    piegate = 0
    if p.lungo / 2.0 > meta > fine and d.posa == "sdraiati":
        # sdraiati la punta piegata in su stava davanti alla faccia come un
        # gradino, e la pinna sembrava chiusa: il film invece si accartoccia
        # in lunghezza, e la pinna resta aperta, distesa e piu' corta
        k = (meta - fine) / (p.lungo / 2.0 - fine)
        m = np.abs(x) > fine
        P[m, lungo] = p.centro[lungo] + np.sign(x[m]) * (fine + (np.abs(x[m]) - fine) * k)
        if N is not None:
            N[m, lungo] = N[m, lungo] / k
        piegate = 2
    elif p.lungo / 2.0 > meta > fine:
        c_sp = p.centro[spesso]
        verso = d.piega
        cs, sn = math.cos(PIEGA_PINNA), math.sin(PIEGA_PINNA)
        for segno in (1.0, -1.0):
            m = segno * x > meta
            if not m.any():
                continue
            piegate += 1
            dx = segno * x[m] - meta
            dz = (P[m, spesso] - c_sp) * verso
            P[m, lungo] = p.centro[lungo] + segno * (meta + dx * cs - dz * sn)
            P[m, spesso] = c_sp + verso * (dx * sn + dz * cs)
            if N is not None:
                nl, ns = N[m, lungo] * segno, N[m, spesso] * verso
                N[m, lungo] = segno * (nl * cs - ns * sn)
                N[m, spesso] = verso * (nl * sn + ns * cs)
    return P, N, piegate


# --------------------------------------------------------------------------- #
# Il GLB composto

def componi(glb_vassoio, glb_prodotto, quanti=None, rigido=False):
    """Il GLB del vassoio con `quanti` pezzi dentro (None: pieno, quanti ne
    stanno). Torna (byte, righe da mostrare). Se ne chiedi piu' di quanti ne
    stanno, mette quelli che ci stanno e lo dice; ValueError se non ce ne sta
    neanche uno. `rigido`: il pack e' un astuccio, che non ha pinne da
    adattare e non si schiaccia."""
    Jv, Bv = leggi(glb_vassoio)
    Jp, Bp = leggi(glb_prodotto)
    cosa = "l'astuccio" if rigido else "il flowpack"
    # il pack si misura nella scena e si adatta nella sua maglia: valgono
    # insieme solo se i suoi nodi non spostano niente, come li fanno
    # build_flowpack e build_carton
    if any(k in n for n in Jp.get("nodes", [])
           for k in ("matrix", "rotation", "translation", "scale")):
        raise ValueError("riempimento: il GLB del pack ha nodi trasformati")
    vano = misura_vassoio(Jv, Bv)
    p = misura_prodotto(Jp, Bp, rigido)
    chiesti = quanti
    d = scegli(vano, p, quanti)
    accorciato = []
    if d is None:
        q = accorcia(vano, p)
        if q is not None:
            corpo = p.corpo
            p, d = q
            accorciato = ["%s ha il corpo lungo %.0f mm e nel vano (%.0f x %.0f x %.0f mm) "
                          "non ci sta in nessuna posa: l'ho accorciato, pinne e corpo "
                          "schiacciati, a %.0f mm di corpo (%.0f%%)"
                          % ((cosa, corpo) + vano.lati + (p.corpo, 100.0 * p.accorcia))]
    if d is None:
        raise ValueError("riempimento: nel vano del vassoio (%.0f x %.0f x %.0f mm) %s "
                         "(%.0f x %.0f x %.0f mm) non ci sta in nessuna posa"
                         % (vano.lati + (cosa, p.lungo, p.largo, p.spesso)))
    if quanti is not None and d.capienza < quanti:
        q = schiaccia(vano, p, quanti, d.posa)
        if q is not None:
            spesso = p.spesso
            p, d = q
            accorciato.append("%s, gonfio, e' spesso %.1f mm e i %d pezzi chiesti non ci "
                              "stavano: schiacciato fra i vicini a %.1f mm (%.0f%%)"
                              % (cosa, spesso, quanti, p.spesso, 100.0 * p.schiaccia))
    massimo = d.capienza
    if quanti is None or quanti > massimo:
        quanti = massimo
    # il pezzo poggia col corpo: le pinne, piu' larghe, si stringono prima
    Vp = vertici(Jp, Bp)
    if not rigido:
        Vp, _, _ = adatta(Vp, None, p, d)
    poste = pose(vano, p, d, quanti, Vp)
    R = d.R

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
            if rigido:
                # niente da adattare: la maglia dell'astuccio com'e'
                for k, v in list(a.items()):
                    a[k] = v + sposta["accessors"]
                if "indices" in prim:
                    prim["indices"] += sposta["accessors"]
                if "material" in prim:
                    prim["material"] += sposta["materials"]
                continue
            P = _dati(Jp, Bp, a["POSITION"]).astype(float) * 1000.0
            Nn = _dati(Jp, Bp, a["NORMAL"]).astype(float) if "NORMAL" in a else None
            P2, N2, piegate = adatta(P, Nn, p, d)
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
    for k, (Rk, t) in enumerate(poste):
        figli = [copia(r) for r in radici]
        q = _quaternione(Rk)
        # t e' dove va il centro del prodotto: il nodo sposta prima il centro
        # nell'origine
        tt = t - Rk @ p.centro
        J["nodes"].append({"name": "pezzo %d" % (k + 1), "children": figli,
                           "rotation": [float(v) for v in q],
                           "translation": [float(v) / 1000.0 for v in tt]})
        scena.append(len(J["nodes"]) - 1)
    J["buffers"] = [{"byteLength": len(B) + (-len(B) % 4)}]
    for chiave in ("extensionsUsed", "extensionsRequired"):
        u = sorted(set(Jv.get(chiave, [])) | set(Jp.get(chiave, [])))
        if u:
            J[chiave] = u
    righe = list(accorciato)
    if chiesti is not None and chiesti > quanti:
        righe.append("ne hai chiesti %d, ma %s nel vassoio ce ne stanno al massimo %d: "
                     "ne ho messi %d" % (chiesti, d.posa, massimo, quanti))
    conti = _strati(d, quanti)
    pezzi = "pezzo" if quanti == 1 else "pezzi"
    strati = "%d %s" % (len(conti), "strato" if len(conti) == 1 else "strati")
    if d.posa == "frontali":
        nx = d.n[0]
        file = [c // nx + (1 if f < c % nx else 0) for c in conti for f in range(nx)]
        file = [f for f in file if f]
        da = ("%d" % file[0] if len(set(file)) == 1
              else ", ".join("%d" % f for f in file))
        righe += ["riempimento: %d %s nel vassoio%s, frontali (%s): %d %s da %s, dal "
                  "davanti al fondo" % (quanti, pezzi, " (pieno)" if chiesti is None else "",
                                        d.dove, len(file), "fila" if len(file) == 1 else "file",
                                        da),
                  "%s, %d %s per strato: frontali ce ne stanno fino a %d (%d per fila)"
                  % (strati, nx, "fila" if nx == 1 else "file", d.capienza, d.n[2])]
    else:
        righe += ["riempimento: %d %s nel vassoio%s, sdraiati (%s)"
                  % (quanti, pezzi, " (pieno)" if chiesti is None else "", d.dove),
                  "%d per strato (%d x %d), %s: ce ne stanno fino a %d"
                  % (d.per_strato, d.n[2], d.n[0], strati, d.capienza),
                  "sdraiati perche' in piedi, con la faccia verso il davanti, nel vano non "
                  "ci stanno" if not d.dove.endswith(" x %d" % len(conti)) else
                  "sdraiati perche' frontali %d non fanno strati uguali, e cosi' fanno una "
                  "griglia piena" % quanti]
    righe.append("vano %.1f x %.1f mm, alto fino a %.1f; pezzo %.1f x %.1f x %.1f (corpo %.1f)"
                 % (vano.lati[0], vano.lati[1], vano.lati[2], p.lungo, p.largo, p.spesso,
                    p.corpo))
    alto = _misura(p, int(np.argmax(np.abs(d.R[1, :]))))
    if alto > vano.per_asse[1]:
        righe.append("il pack e' alto %.1f mm e le pareti %.1f: sta in piedi e sporge dal "
                     "vassoio" % (alto, vano.per_asse[1]))
    if rigido:
        return scrivi(J, bytes(B)), righe
    if piegate:
        righe.append("pinne piu' lunghe del posto del pezzo: %s"
                     % ("le punte si piegano verso il dietro" if d.posa == "frontali" else
                        "si accorciano, accartocciate in lunghezza, e restano aperte"))
    passo = d.passo[d.asse(p.assi[1])]
    if p.largo_pinne > passo:
        righe.append("pinne piu' larghe del passo fra due pezzi (%.1f contro %.1f): si "
                     "stringono come il film accartocciato" % (p.largo_pinne, passo))
    return scrivi(J, bytes(B)), righe
