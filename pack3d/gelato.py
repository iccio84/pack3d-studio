"""
Il gelato del tubo a cono: il ghiacciolo che esce dalla bocca, aggiunto al
GLB del tubo (`server.build_tubo` con l'opzione «con il gelato»).

Il ghiaccio e' aderente al tubo: dentro la bocca ha il raggio di dentro
della parete (`STACCO` in meno) e si schiaccia come lei; sopra esce dritto,
largo quanto la bocca, per `SPORGE` volte il suo diametro; l'orlo a tubetto
resta tutto a vista. La cima e' appena bombata, col bordo tondo e qualche
irregolarita'.

Il ghiaccio non ha una texture del colore. Glam mette la texture del pack su
tutti i materiali che hanno un colore da immagine (GLAM.md, sezione 8), e la
texture a parte e il template PSD contano le immagini del colore
(`pack3d.texture`): con una sua texture il modello ne avrebbe due, e Glam ci
stamperebbe sopra l'artwork. Il colore e' pieno (`baseColorFactor`, il gusto)
con le variazioni e l'ombra del tubo nei colori dei vertici (COLOR_0, in
RGBA: in RGB il render di Glam lo fa nero); il dettaglio sta nelle altre
mappe:

- le normali: la grana satinata dei fianchi, le scaglie di cristallo sulla
  cima;
- ruvidita' (G) e bagnato (R, letto anche come clearcoat): tutto bagnato e
  lucido, le scaglie lucidissime;
- l'emissione: il sorbetto lascia passare un poco di luce (un bagliore del
  suo colore) e le scaglie brillano.

Le mappe si calcolano sul punto 3D di ogni texel: niente cuciture lungo il
giro, niente stiramenti al polo della cima. Il rumore e' una funzione del
punto, senza estrazioni a caso: lo stesso PDF da' lo stesso GLB.
"""
from __future__ import annotations

import io
import json
import math
import struct

import numpy as np

STACCO = 0.06       # mm fra il ghiaccio e la parete: aderente
SPORGE = 0.7        # quanto esce sopra la parete, in diametri della bocca
RACCORDO = 1.6      # mm, il bordo tondo della cima
CUPOLA = 0.4        # mm, quanto la cima e' bombata
SOTTO = 14.0        # mm di ghiaccio dentro il tubo, sotto la cima della parete
CALO = 0.8          # mm: il ghiaccio era gelato poco sotto la bocca
BAGLIORE = 0.12     # l'emissione del sorbetto, in parte del suo colore
# il lato delle mappe, px (meta' in altezza): 0,1 mm per pixel sul giro. A
# 2048 non si vede la differenza nemmeno da vicino, e costa venti volte tanto
LATO = 1024
PASSI_GIRO = 192
PASSI_PROFILO = 300

# I gusti: il colore (lineare) del ghiaccio, scuro e chiaro, e quello delle
# scaglie. Il lime e' misurato sulla foto del caso 84c854d6a5.
GUSTI = {
    "lime": ((0.27, 0.42, 0.006), (0.35, 0.50, 0.016), (0.52, 0.64, 0.12)),
    "limone": ((0.70, 0.60, 0.08), (0.82, 0.72, 0.14), (0.90, 0.85, 0.45)),
    "arancia": ((0.75, 0.20, 0.008), (0.86, 0.30, 0.020), (0.95, 0.60, 0.30)),
    "fragola": ((0.52, 0.012, 0.025), (0.66, 0.030, 0.050), (0.88, 0.40, 0.45)),
    "cola": ((0.075, 0.018, 0.004), (0.12, 0.034, 0.008), (0.40, 0.25, 0.15)),
}


def gusto(valore):
    """Il gusto scelto, o None (senza gelato). ValueError se non c'e'."""
    if valore in (None, "", 0, "0", False):
        return None
    g = str(valore).strip().lower()
    if g not in GUSTI:
        raise ValueError("Il gelato: un gusto fra %s" % ", ".join(GUSTI))
    return g


# --------------------------------------------------------------------------- #
# il rumore 3D
# --------------------------------------------------------------------------- #
def _hash(ix, iy, iz, seme):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263
         + iz.astype(np.int64) * 2147483647 + seme * 144665) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def _rumore(P, scala, seme=0):
    """Rumore di valore in 3D, in [-1, 1], interpolato col quintico."""
    Q = P / scala
    i = np.floor(Q).astype(np.int64)
    f = Q - i
    u = f * f * f * (f * (f * 6 - 15) + 10)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1])
                     * (u[:, 2] if dz else 1 - u[:, 2]))
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seme)
    return out * 2 - 1


def _fbm(P, scala, ottave, seme=0, guad=0.5):
    tot, amp, norm = 0, 1.0, 0
    for o in range(ottave):
        tot = tot + amp * _rumore(P, scala / 2 ** o, seme + 17 * o)
        norm += amp
        amp *= guad
    return tot / norm


def _liscio(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------- #
# la forma
# --------------------------------------------------------------------------- #
class _Forma:
    """Il profilo del ghiaccio (raggio, altezza) dal fondo alla punta della
    cupola, a lunghezza d'arco, sul tubo `p` (`pack3d.tubo.Tubo`)."""

    def __init__(self, p, spessore):
        self.cosf = math.sqrt(max(0.0, 1.0 - p.k ** 2))
        self.p, self.sp = p, spessore
        self.Yc = (p.R_cima - p.R_base) * self.cosf          # la cima della parete
        self.d_bocca = 2 * (self.r_parete(self.Yc) + spessore)
        self.Ytop = self.Yc - CALO + SPORGE * self.d_bocca
        self.yb = self.Yc - SOTTO
        prof = [(self.r_ghiaccio(y), y)
                for y in np.linspace(self.yb, self.Ytop - RACCORDO, 400)]
        self.n_fianco = len(prof)
        R_t = self.r_ghiaccio(self.Ytop - RACCORDO)
        for f in np.linspace(0, math.pi / 2, 60)[1:]:
            prof.append((R_t - RACCORDO + RACCORDO * math.cos(f),
                         self.Ytop - RACCORDO + RACCORDO * math.sin(f)))
        R_c = R_t - RACCORDO
        for s in np.linspace(1, 0, 120)[1:]:
            prof.append((R_c * s, self.Ytop + CUPOLA * (1 - s * s)))
        self.prof = np.array(prof)
        self.seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(self.prof, axis=0), axis=1))]
        self.lungo = float(self.seg[-1])
        self.d_cima = 2 * R_t

    def r_parete(self, y):
        """Il raggio di dentro della parete all'altezza y (mm dal fondo)."""
        rho = self.p.R_base + y / self.cosf
        return self.p.giro(rho) / (2 * math.pi) - self.sp

    def r_ghiaccio(self, y):
        return self.r_parete(min(y, self.Yc)) - STACCO

    def __call__(self, t):
        """t in [0,1] -> (raggio, altezza, normale nel piano (nr, ny))."""
        s = np.asarray(t) * self.lungo
        r = np.interp(s, self.seg, self.prof[:, 0])
        y = np.interp(s, self.seg, self.prof[:, 1])
        e = 0.05
        r2 = np.interp(s + e, self.seg, self.prof[:, 0])
        y2 = np.interp(s + e, self.seg, self.prof[:, 1])
        r1 = np.interp(s - e, self.seg, self.prof[:, 0])
        y1 = np.interp(s - e, self.seg, self.prof[:, 1])
        dr, dy = r2 - r1, y2 - y1
        n = np.hypot(dr, dy) + 1e-12
        return r, y, dy / n, -dr / n

    def pesi(self, Y):
        """(cima, alto, ombra) per altezze Y: 1 sulla cima, la parte fuori
        dalla bocca da 0 a 1, e la luce che arriva dentro la bocca."""
        cima = np.clip((Y - (self.Ytop - RACCORDO - 1.0)) / 2.0, 0, 1)
        alto = np.clip((Y - (self.Yc - 1)) / (self.Ytop - self.Yc), 0, 1)
        ombra = np.clip((Y - (self.Yc - 4.0)) / 6.0, 0, 1)
        return cima, alto, ombra


def _normali(P, T):
    N = np.zeros_like(P)
    f = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    for k in range(3):
        np.add.at(N, T[:, k], f)
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)


def maglia(p, spessore, quale):
    """(V, N, UV, T, COLORE, forma) del ghiaccio in mm, nello stesso sistema
    del tubo (`tubo.maglia`: il fondo a Y = 0, la bocca in su). COLORE e' il
    colore dei vertici, da moltiplicare per il chiaro del gusto."""
    scuro, chiaro, _ = (np.array(c) for c in GUSTI[quale])
    fo = _Forma(p, spessore)
    NT, NV = PASSI_GIRO, PASSI_PROFILO
    th = np.linspace(0, 2 * math.pi, NT + 1)
    tt = np.linspace(0, 1, NV)
    r, y, nr, ny = fo(tt)
    TH = np.meshgrid(th, tt)[0]
    R = np.repeat(r[:, None], NT + 1, 1)
    Y = np.repeat(y[:, None], NT + 1, 1)
    NR = np.repeat(nr[:, None], NT + 1, 1)
    NY = np.repeat(ny[:, None], NT + 1, 1)
    P0 = np.stack([R * np.sin(TH), Y, R * np.cos(TH)], -1).reshape(-1, 3)
    N0 = np.stack([NR * np.sin(TH), NY, NR * np.cos(TH)], -1).reshape(-1, 3)
    # grumi bassi, colature verticali, e la cima un poco irregolare
    cima, alto, ombra = fo.pesi(P0[:, 1])
    in_cima = np.clip((P0[:, 1] - (fo.Ytop - RACCORDO)) / RACCORDO, 0, 1)
    stirato = P0 * np.array([1.0, 0.25, 1.0])
    spost = ((0.025 * _fbm(P0, 6.0, 2, 1) + 0.02 * _fbm(stirato, 3.0, 2, 5))
             * (0.4 + 0.6 * alto) + 0.22 * _fbm(P0, 6.0, 2, 3) * in_cima)
    V = P0 + N0 * spost[:, None]
    # dentro la bocca la parete e' un poco schiacciata (`tubo.tondezza`): il
    # ghiaccio la segue, se no di davanti e di dietro uscirebbe dalla carta
    from .tubo import tondezza
    q = tondezza(p, spessore)
    dentro = V[:, 1] < fo.Yc
    V[dentro, 2] *= np.array([q(y / fo.cosf) for y in V[dentro, 1]])
    V = V.reshape(NV, NT + 1, 3)
    V[:, -1] = V[:, 0]
    V = V.reshape(-1, 3)
    UV = np.stack(np.meshgrid(th / (2 * math.pi), tt), -1).reshape(-1, 2)
    i, j = np.meshgrid(np.arange(NV - 1), np.arange(NT), indexing="ij")
    v00 = (i * (NT + 1) + j).reshape(-1)
    v01, v10, v11 = v00 + 1, v00 + NT + 1, v00 + NT + 2
    T = np.concatenate([np.stack([v00, v01, v11], 1), np.stack([v00, v11, v10], 1)])
    # il fondo dentro il tubo: un tappo piatto
    c0 = len(V)
    V = np.vstack([V, [[0, fo.yb, 0]]])
    UV = np.vstack([UV, [[0.5, 0.0]]])
    T = np.vstack([T, np.stack([np.full(NT, c0), np.arange(NT) + 1, np.arange(NT)], 1)])
    N = _normali(V, T)
    giro = NV * (NT + 1)
    Nm = N[:giro].reshape(NV, NT + 1, 3)
    m = Nm[:, 0] + Nm[:, -1]
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-12
    Nm[:, 0] = m
    Nm[:, -1] = m
    N[:giro] = Nm.reshape(-1, 3)
    if (np.einsum("ij,ij->i", N[:giro], N0) < 0).mean() > 0.5:
        T = T[:, ::-1].copy()
        N = -N
    # il colore dei vertici: le macchie del gusto e l'ombra dentro la bocca,
    # in parte del chiaro (il baseColorFactor)
    var = np.clip(0.5 + 0.7 * _fbm(np.vstack([P0, [[0, fo.yb, 0]]]), 3.0, 3, 71), 0, 1)
    col = scuro[None] * (1 - var[:, None]) + chiaro[None] * var[:, None]
    ombra = np.r_[ombra, 0.0]
    col = col * (0.35 + 0.65 * ombra[:, None])
    colore = np.clip(col / chiaro[None], 0.0, 1.0)
    return V, N, UV, T.astype(np.uint32), colore, fo


def mappe(fo, quale, lato=LATO):
    """Le mappe del ghiaccio: (emissione RGB, normali RGB, ruvidita'/bagnato
    RGB), immagini PIL di lato x lato/2, sulle UV di `maglia`."""
    from PIL import Image
    _, chiaro, crist = (np.array(c) for c in GUSTI[quale])
    W, Hh = lato, lato // 2
    us = (np.arange(W) + 0.5) / W
    vs = (np.arange(Hh) + 0.5) / Hh
    rt, yt, _, _ = fo(vs)
    U = np.meshgrid(us, vs)[0]
    THt = U * 2 * math.pi
    Rt = rt[:, None] * np.ones_like(U)
    Yt = yt[:, None] * np.ones_like(U)
    Pt = np.stack([Rt * np.sin(THt), Yt, Rt * np.cos(THt)], -1).reshape(-1, 3)
    cima, alto, ombra = fo.pesi(Yt.reshape(-1))
    liscio = 1 - cima
    satin = _fbm(Pt * np.array([1, 0.35, 1]), 0.12, 2, 23)
    onde = _fbm(Pt, 2.5, 2, 11)
    scaglie = (np.clip((_fbm(Pt, 1.1, 2, 31) - 0.42) / 0.10, 0, 1)
               * np.clip(cima + 0.12 * alto, 0, 1))
    h = 0.004 * onde + 0.006 * satin + 0.07 * scaglie
    # la normale dalla pendenza dell'altezza, in mm per texel
    dmm_u = 2 * math.pi * np.maximum(Rt, 0.3) / W
    dmm_v = fo.lungo / Hh
    hh = h.reshape(Hh, W)
    gu = (np.roll(hh, -1, 1) - np.roll(hh, 1, 1)) / (2 * dmm_u)
    gv = np.zeros_like(hh)
    gv[1:-1] = (hh[2:] - hh[:-2]) / (2 * dmm_v)
    fac = scaglie.reshape(Hh, W)
    nx = -gu + 1.1 * fac * _fbm(Pt, 0.35, 1, 51).reshape(Hh, W)
    ny = -gv + 1.1 * fac * _fbm(Pt, 0.35, 1, 61).reshape(Hh, W)
    nz = np.ones_like(hh)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    # glTF: +X verso +u, +Y verso -v dell'immagine (le righe crescono con v)
    nm = np.stack([nx / L, -ny / L, nz / L], -1)
    normali = Image.fromarray(((nm * 0.5 + 0.5) * 255).round().clip(0, 255).astype(np.uint8))
    # l'emissione: il bagliore del sorbetto (in ombra dentro la bocca) e le
    # scaglie che brillano
    em = (BAGLIORE * chiaro[None] * (0.35 + 0.65 * ombra[:, None])
          + 0.30 * crist[None] * scaglie[:, None])
    em = np.clip(em, 0, 1)
    em = np.where(em <= 0.0031308, 12.92 * em, 1.055 * np.power(em, 1 / 2.4) - 0.055)
    emissione = Image.fromarray((em.reshape(Hh, W, 3) * 255).round().clip(0, 255).astype(np.uint8))
    # ruvidita' (G) e bagnato (R): tutto bagnato e lucido, le scaglie di piu'
    rough = np.clip(0.20 + 0.06 * _fbm(Pt, 1.5, 2, 91) + 0.06 * liscio - 0.15 * scaglie,
                    0.04, 0.8)
    bagnato = np.clip(0.85 + 0.15 * scaglie, 0, 1)
    mr = np.zeros((Hh * W, 3))
    mr[:, 0] = bagnato
    mr[:, 1] = rough
    ruvidita = Image.fromarray((mr.reshape(Hh, W, 3) * 255).round().astype(np.uint8))
    return emissione, normali, ruvidita


# --------------------------------------------------------------------------- #
# nel GLB
# --------------------------------------------------------------------------- #
def aggiungi(glb_path, p, spessore, quale, lato=LATO, unit_scale=0.001):
    """Aggiunge il ghiacciolo al GLB del tubo in `glb_path` (lo riscrive):
    una mesh e un nodo in piu', un materiale senza texture del colore.
    Torna la riga per chi l'ha chiesto."""
    from PIL import Image  # noqa: F401  (le mappe sono PIL)
    V, N, UV, T, colore, fo = maglia(p, spessore, quale)
    emissione, normali, ruvidita = mappe(fo, quale, lato)
    with open(glb_path, "rb") as fh:
        b = fh.read()
    n = struct.unpack("<I", b[12:16])[0]
    J = json.loads(b[20:20 + n])
    o = 20 + n
    m = struct.unpack("<I", b[o:o + 4])[0]
    binb = bytearray(b[o + 8:o + 8 + m])

    def vista(dati, target=None):
        while len(binb) % 4:
            binb.append(0)
        bv = {"buffer": 0, "byteOffset": len(binb), "byteLength": len(dati)}
        if target:
            bv["target"] = target
        binb.extend(dati)
        J["bufferViews"].append(bv)
        return len(J["bufferViews"]) - 1

    def accessorio(arr, tipo, comp, target, minmax=False):
        acc = {"bufferView": vista(arr.tobytes(), target), "componentType": comp,
               "count": int(arr.shape[0]), "type": tipo}
        if minmax:
            acc["min"] = arr.min(0).tolist()
            acc["max"] = arr.max(0).tolist()
        J["accessors"].append(acc)
        return len(J["accessors"]) - 1

    attributi = {
        "POSITION": accessorio((V * unit_scale).astype(np.float32), "VEC3", 5126, 34962, True),
        "NORMAL": accessorio(N.astype(np.float32), "VEC3", 5126, 34962),
        "TEXCOORD_0": accessorio(UV.astype(np.float32), "VEC2", 5126, 34962),
        # RGBA, l'alfa a 1: il render di Glam (three-gpu-pathtracer) unisce le
        # mesh e da' al tubo, che non ha colori, un RGBA di serie; con un
        # COLOR_0 RGB le misure non tornano, la copia va al contrario e il
        # ghiaccio resta a zero: nero, col solo bagliore
        "COLOR_0": accessorio(np.c_[colore, np.ones(len(colore))].astype(np.float32),
                              "VEC4", 5126, 34962)}
    indici = accessorio(T.reshape(-1), "SCALAR", 5125, 34963)
    J.setdefault("samplers", []).append({"magFilter": 9729, "minFilter": 9987,
                                         "wrapS": 10497, "wrapT": 33071})
    campionatore = len(J["samplers"]) - 1

    def immagine(im, png=False):
        buf = io.BytesIO()
        if png:
            im.save(buf, "PNG")
        else:
            im.save(buf, "JPEG", quality=92)
        J.setdefault("images", []).append(
            {"bufferView": vista(buf.getvalue()),
             "mimeType": "image/png" if png else "image/jpeg"})
        J.setdefault("textures", []).append({"source": len(J["images"]) - 1,
                                             "sampler": campionatore})
        return len(J["textures"]) - 1

    t_em = immagine(emissione)
    t_n = immagine(normali)
    t_r = immagine(ruvidita)
    chiaro = GUSTI[quale][1]
    J["materials"].append({
        "name": "gelato",
        "pbrMetallicRoughness": {"baseColorFactor": list(chiaro) + [1.0],
                                 "metallicFactor": 0.0, "roughnessFactor": 1.0,
                                 "metallicRoughnessTexture": {"index": t_r}},
        "normalTexture": {"index": t_n, "scale": 1.0},
        "emissiveTexture": {"index": t_em},
        "emissiveFactor": [1.0, 1.0, 1.0],
        "extensions": {"KHR_materials_clearcoat": {"clearcoatFactor": 0.6,
                                                   "clearcoatTexture": {"index": t_r},
                                                   "clearcoatRoughnessFactor": 0.06},
                       "KHR_materials_ior": {"ior": 1.31}}})
    J["meshes"].append({"name": "gelato", "primitives": [
        {"attributes": attributi, "indices": indici,
         "material": len(J["materials"]) - 1}]})
    J["nodes"].append({"mesh": len(J["meshes"]) - 1, "name": "gelato"})
    J["scenes"][J.get("scene", 0)]["nodes"].append(len(J["nodes"]) - 1)
    J["extensionsUsed"] = sorted(set(J.get("extensionsUsed", []))
                                 | {"KHR_materials_clearcoat", "KHR_materials_ior"})
    while len(binb) % 4:
        binb.append(0)
    J["buffers"][0]["byteLength"] = len(binb)
    js = json.dumps(J, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    with open(glb_path, "wb") as fh:
        fh.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)))
        fh.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        fh.write(struct.pack("<II", len(binb), 0x004E4942) + bytes(binb))
    return ("con il gelato (%s): il ghiacciolo esce di %.1f mm dalla bocca, "
            "aderente al tubo, largo %.1f mm" % (quale, fo.Ytop - fo.Yc, fo.d_cima))
