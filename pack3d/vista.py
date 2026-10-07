"""
Il modello finito visto da fuori: dal GLB a un'immagine, senza GPU.

Serve al controllo dell'AI (`controllo.py`): prima di consegnare un modello,
Claude lo guarda accanto all'artwork. Quindi il modello va guardato com'e'
uscito, cioe' dal GLB scritto su disco, e non dalle strutture interne di chi
l'ha costruito: un difetto dell'export si deve vedere come lo vede l'utente.

Due cose da sapere:

- Si scartano le facce posteriori, come fa il viewer della pagina. Un modello
  con le normali girate deve sembrare sbagliato anche qui, se no il controllo
  promuove quello che l'utente vede rotto.
- Lo z-buffer e' vettoriale. `raster.render_mesh` gira un triangolo alla
  volta in Python, e su un flowpack da 125 mila triangoli quattro viste erano
  minuti: troppo per stare dentro ogni costruzione. Qui i triangoli si
  rasterizzano a blocchi, raggruppati per quanto sono grandi sullo schermo, e
  solo i pochi grandi (le facce di un astuccio sono due triangoli l'una) si
  fanno uno per uno.
"""
from __future__ import annotations

import io
import json
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

SFONDO = (238, 238, 241)
# Luce dall'alto a sinistra, davanti: la stessa di raster.render_mesh, cosi'
# le viste del controllo somigliano alle anteprime di sempre.
LUCE = (-0.35, 0.62, 0.70)
AMBIENTE, DIFFUSA, SPECULARE, LUCIDO = 0.60, 0.42, 0.16, 26.0

# Le quattro viste del controllo: (nome, yaw, pitch) in gradi. Il fronte del
# modello guarda +Z (vedi folding.corners), quindi yaw 0 e' il fronte dritto.
VISTE = (
    ("fronte", 0.0, 0.0),
    ("tre quarti", 35.0, 20.0),
    ("retro", 215.0, 20.0),
    ("dall'alto", 25.0, 65.0),
)

_TIPI = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
         5125: np.uint32, 5126: np.float32}
_COMPONENTI = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# --------------------------------------------------------------------------- #
# lettura del GLB
# --------------------------------------------------------------------------- #
def _trs(nodo):
    """La matrice 4x4 locale di un nodo glTF (matrix, o T * R * S)."""
    if "matrix" in nodo:
        return np.array(nodo["matrix"], float).reshape(4, 4).T
    M = np.eye(4)
    x, y, z, w = nodo.get("rotation", (0.0, 0.0, 0.0, 1.0))
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M[:3, :3] = R * np.array(nodo.get("scale", (1.0, 1.0, 1.0)), float)
    M[:3, 3] = nodo.get("translation", (0.0, 0.0, 0.0))
    return M


def leggi_glb(sorgente):
    """Le parti di un GLB, pronte da rendere.

    `sorgente` e' un percorso o i byte del file. Torna una lista di dict con
    verts (Nx3, metri, gia' nel riferimento della scena), normals (Nx3 o
    None), uvs (Nx2), tris (Mx3) e tex (HxWx3 uint8): una per primitiva,
    tranne le trasparenti - la pellicola delle finestre - che si saltano.
    """
    if isinstance(sorgente, (bytes, bytearray)):
        d = bytes(sorgente)
    else:
        with open(sorgente, "rb") as fh:
            d = fh.read()
    if d[:4] != b"glTF":
        raise ValueError("non e' un GLB")
    lunghezza = struct.unpack_from("<I", d, 8)[0]
    off, J, binario = 12, None, 0
    while off < lunghezza:
        n, tipo = struct.unpack_from("<II", d, off)
        if tipo == 0x4E4F534A:          # JSON
            J = json.loads(d[off + 8:off + 8 + n].decode("utf-8"))
        elif tipo == 0x004E4942:        # BIN
            binario = off + 8
        off += 8 + n
    if J is None:
        raise ValueError("GLB senza JSON")

    def vista_byte(i):
        bv = J["bufferViews"][i]
        a = binario + bv.get("byteOffset", 0)
        return a, bv["byteLength"], bv.get("byteStride")

    def accessor(i):
        acc = J["accessors"][i]
        tipo = np.dtype(_TIPI[acc["componentType"]]).newbyteorder("<")
        k = _COMPONENTI[acc["type"]]
        a, _n, passo = vista_byte(acc["bufferView"])
        a += acc.get("byteOffset", 0)
        conta = acc["count"]
        if passo and passo != tipo.itemsize * k:
            righe = np.frombuffer(d, np.uint8, count=passo * (conta - 1) + tipo.itemsize * k,
                                  offset=a)
            idx = (np.arange(conta)[:, None] * passo + np.arange(tipo.itemsize * k)[None, :])
            r = righe[idx].copy().view(tipo).reshape(conta, k)
        else:
            r = np.frombuffer(d, tipo, count=conta * k, offset=a).reshape(conta, k)
        return r

    immagini = {}

    def immagine(indice_texture):
        src = J["textures"][indice_texture]["source"]
        if src not in immagini:
            a, n, _p = vista_byte(J["images"][src]["bufferView"])
            im = Image.open(io.BytesIO(d[a:a + n])).convert("RGB")
            immagini[src] = np.asarray(im)
        return immagini[src]

    def texture(materiale):
        """La texture del colore base, o un pixel del colore pieno."""
        pbr = (J.get("materials") or [{}])[materiale].get("pbrMetallicRoughness", {}) \
            if materiale is not None else {}
        bct = pbr.get("baseColorTexture")
        if bct is not None:
            return immagine(bct["index"])
        f = pbr.get("baseColorFactor", (1.0, 1.0, 1.0, 1.0))
        return np.array([[[int(255 * c) for c in f[:3]]]], np.uint8)

    def metallo(materiale):
        """La mappa metallo/ruvidita', se il materiale ne ha una."""
        pbr = (J.get("materials") or [{}])[materiale].get("pbrMetallicRoughness", {}) \
            if materiale is not None else {}
        mrt = pbr.get("metallicRoughnessTexture")
        return immagine(mrt["index"]) if mrt is not None else None

    parti = []

    def visita(i, padre):
        nodo = J["nodes"][i]
        M = padre @ _trs(nodo)
        if "mesh" in nodo:
            lin = M[:3, :3]
            for prim in J["meshes"][nodo["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4:
                    continue
                m = prim.get("material")
                if m is not None and (J.get("materials") or [{}])[m].get(
                        "alphaMode") == "BLEND":
                    # la pellicola trasparente delle finestre: qui si
                    # dipingerebbe opaca, e il controllo guarda la grafica e
                    # la forma, che sono quelle di sempre
                    continue
                att = prim["attributes"]
                V = accessor(att["POSITION"]).astype(float)
                V = V @ lin.T + M[:3, 3]
                N = None
                if "NORMAL" in att:
                    N = accessor(att["NORMAL"]).astype(float) @ np.linalg.inv(lin)
                    lun = np.linalg.norm(N, axis=1, keepdims=True)
                    N = N / np.where(lun == 0, 1, lun)
                if "TEXCOORD_0" in att:
                    UV = accessor(att["TEXCOORD_0"]).astype(float)
                else:
                    UV = np.zeros((len(V), 2))
                if "indices" in prim:
                    T = accessor(prim["indices"]).astype(np.int64).reshape(-1, 3)
                else:
                    T = np.arange(len(V) - len(V) % 3).reshape(-1, 3)
                parti.append(dict(nome=nodo.get("name", ""), verts=V, normals=N,
                                  uvs=UV, tris=T, tex=texture(prim.get("material")),
                                  mr=metallo(prim.get("material"))))
        for figlio in nodo.get("children", ()):
            visita(figlio, M)

    scena = J.get("scenes", [{}])[J.get("scene", 0)] if J.get("scenes") else {}
    for i in scena.get("nodes", range(len(J.get("nodes", [])))):
        visita(i, np.eye(4))
    return parti


def ingombro_mm(parti):
    """Le tre misure del modello in mm: larghezza (X), altezza (Y), profondita' (Z)."""
    V = np.concatenate([p["verts"] for p in parti])
    return tuple(float(x) for x in (V.max(0) - V.min(0)) * 1000.0)


# --------------------------------------------------------------------------- #
# z-buffer vettoriale
# --------------------------------------------------------------------------- #
def _rotazione(yaw, pitch):
    a, b = np.radians(yaw), np.radians(pitch)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    return Rx @ Ry


def _normali(V, T):
    N = np.zeros_like(V)
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    lun = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.where(lun == 0, 1, lun)


class _Tela:
    """Colore e profondita' di un'immagine, scritti a blocchi di frammenti."""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.z = np.full(W * H, np.inf)
        self.rgb = np.empty((W * H, 3), np.float32)
        self.rgb[:] = SFONDO

    def scrivi(self, pix, w0, w1, w2, ti, P):
        """Il frammento piu' vicino per pixel, se batte quello che c'e' gia'."""
        T, inv = P["T"], P["inv"]
        i0, i1, i2 = T[ti, 0], T[ti, 1], T[ti, 2]
        a0, a1, a2 = w0 * inv[i0], w1 * inv[i1], w2 * inv[i2]
        z = 1.0 / (a0 + a1 + a2)
        ordine = np.lexsort((z, pix))
        ps = pix[ordine]
        primo = np.ones(len(ordine), bool)
        primo[1:] = ps[1:] != ps[:-1]
        k = ordine[primo]
        k = k[z[k] < self.z[pix[k]]]
        if not len(k):
            return
        p = pix[k]
        self.z[p] = z[k]
        UV, lit, tex = P["UV"], P["lit"], P["tex"]
        a0, a1, a2, zk = a0[k], a1[k], a2[k], z[k]
        j0, j1, j2 = i0[k], i1[k], i2[k]
        u = (a0 * UV[j0, 0] + a1 * UV[j1, 0] + a2 * UV[j2, 0]) * zk
        v = (a0 * UV[j0, 1] + a1 * UV[j1, 1] + a2 * UV[j2, 1]) * zk
        th, tw = tex.shape[:2]
        tx = np.clip((u * tw).astype(np.int64), 0, tw - 1)
        ty = np.clip((v * th).astype(np.int64), 0, th - 1)
        luce = w0[k] * lit[j0] + w1[k] * lit[j1] + w2[k] * lit[j2]
        mr = P.get("mr")
        if mr is not None:
            # Il metallo non ha luce sua: rimanda l'ambiente, nitido se e'
            # lucido, mediato se e' satinato. Senza, un film metallizzato
            # usciva bianco latte, e il controllo lo confrontava col grigio
            # dell'alluminio del DT.
            mh, mw = mr.shape[:2]
            mx = np.clip((u * mw).astype(np.int64), 0, mw - 1)
            my = np.clip((v * mh).astype(np.int64), 0, mh - 1)
            m = mr[my, mx, 2].astype(np.float32) / 255.0
            r = mr[my, mx, 1].astype(np.float32) / 255.0
            E = P["ambiente"]
            amb = w0[k] * E[j0] + w1[k] * E[j1] + w2[k] * E[j2]
            sfoca = np.clip((r - 0.12) / 0.45, 0.0, 1.0)
            luce = luce * (1.0 - m) + (amb * (1.0 - sfoca) + RIFLESSO_MEDIO * sfoca) * m
        self.rgb[p] = np.clip(tex[ty, tx].astype(np.float32) * luce[:, None], 0, 255)


# frammenti per blocco: abbastanza per vettorializzare, pochi per la memoria
# di un piano piccolo (ogni frammento porta una decina di numeri)
_BLOCCO = 1_500_000


def _rasterizza(tela, P):
    """Riempie la tela con i triangoli davanti, riga per riga.

    Per ogni riga di pixel si calcola dove i lati del triangolo la tagliano e
    si prendono solo i pixel in mezzo: il lavoro va con l'AREA del triangolo,
    non col suo riquadro. Col riquadro le fette lunghe e sottili del lid (un
    ventaglio dal centro al bordo) costavano come triangoli pieni, ed erano la
    meta' del tempo.
    """
    xs, ys = P["xs"], P["ys"]
    T = P["T"]
    x0, y0 = xs[T[:, 0]], ys[T[:, 0]]
    x1, y1 = xs[T[:, 1]], ys[T[:, 1]]
    x2, y2 = xs[T[:, 2]], ys[T[:, 2]]
    A = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    W, H = tela.W, tela.H
    # Davanti = antiorario visto dalla camera, come glTF; sullo schermo la y
    # scende, quindi l'area con segno di una faccia davanti e' negativa.
    tieni = P["vivi"] & (A < 0)
    # le righe il cui centro (j + 0,5) puo' cadere nel triangolo
    r0 = np.ceil(np.minimum(np.minimum(y0, y1), y2) - 0.5)
    r1 = np.floor(np.maximum(np.maximum(y0, y1), y2) - 0.5)
    tieni &= (r1 >= np.maximum(r0, 0)) & (r0 <= H - 1)
    tieni &= (np.maximum(np.maximum(x0, x1), x2) >= 0.5)
    tieni &= (np.minimum(np.minimum(x0, x1), x2) <= W - 0.5)
    t_tutti = np.nonzero(tieni)[0]
    if not len(t_tutti):
        return
    r0 = np.clip(r0, 0, H - 1).astype(np.int64)
    r1 = np.clip(r1, 0, H - 1).astype(np.int64)
    # stima dei frammenti per triangolo, per fare blocchi di peso simile
    peso = np.abs(A[t_tutti]) / 2.0 + (r1 - r0 + 1)[t_tutti] + 1.0
    tagli = np.searchsorted(np.cumsum(peso), np.arange(1, int(peso.sum() // _BLOCCO) + 2) * _BLOCCO)
    inizio = 0
    for fine in list(tagli) + [len(t_tutti)]:
        fine = max(fine, inizio + 1)
        t = t_tutti[inizio:fine]
        inizio = fine
        if not len(t):
            continue
        # una voce per riga
        nr = r1[t] - r0[t] + 1
        tr = np.repeat(t, nr)
        prima = np.repeat(np.cumsum(nr) - nr, nr)
        y = r0[tr] + (np.arange(len(tr)) - prima)
        py = y + 0.5
        xl = np.full(len(tr), np.inf)
        xr = np.full(len(tr), -np.inf)
        for xa, ya, xb, yb in ((x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x0, y0)):
            xa, ya, xb, yb = xa[tr], ya[tr], xb[tr], yb[tr]
            dy = yb - ya
            ok = (np.minimum(ya, yb) <= py) & (py <= np.maximum(ya, yb)) & (dy != 0)
            x = xa + (py - ya) * (xb - xa) / np.where(dy != 0, dy, 1.0)
            xl = np.where(ok, np.minimum(xl, x), xl)
            xr = np.where(ok, np.maximum(xr, x), xr)
        c0 = np.maximum(np.ceil(xl - 0.5), 0)
        c1 = np.minimum(np.floor(xr - 0.5), W - 1)
        quanti = np.where(np.isfinite(c0) & np.isfinite(c1), c1 - c0 + 1, 0)
        quanti = np.maximum(quanti, 0).astype(np.int64)
        if not quanti.sum():
            continue
        # una voce per pixel
        riga = np.repeat(np.arange(len(tr)), quanti)
        prima = np.repeat(np.cumsum(quanti) - quanti, quanti)
        x = c0[riga].astype(np.int64) + (np.arange(len(riga)) - prima)
        ti = tr[riga]
        PX, PY = x + 0.5, py[riga]
        a = A[ti]
        w0 = ((x1[ti] - PX) * (y2[ti] - PY) - (x2[ti] - PX) * (y1[ti] - PY)) / a
        w1 = ((x2[ti] - PX) * (y0[ti] - PY) - (x0[ti] - PX) * (y2[ti] - PY)) / a
        # il pixel e' dentro per costruzione: si tagliano solo gli
        # arrotondamenti, che sui bordi darebbero pesi appena negativi
        w0 = np.clip(w0, 0.0, 1.0)
        w1 = np.clip(w1, 0.0, 1.0 - w0)
        w2 = 1.0 - w0 - w1
        tela.scrivi(y[riga] * W + x, w0, w1, w2, ti, P)


# L'ambiente che il metallo rimanda: uno studio, chiaro in alto e scuro in
# basso, con la luce della scena come finestra. Un film metallizzato lucido ci
# fa bande chiare e scure lungo le grinze; satinato, un grigio piu' chiaro e
# uniforme. Tarato perche' il metallo visto di fronte cada sul grigio con cui
# il DT disegna l'alluminio, e la vernice opaca sopra resti piu' chiara, come
# la disegna la grafica del Nutella Biscuits.
AMBIENTE_BUIO, AMBIENTE_CHIARO, FINESTRA = 0.35, 1.2, 0.6
RIFLESSO_MEDIO = 0.88


def _ambiente(R, L):
    """Quanta luce arriva dalla direzione `R` (riflessa, nel telaio camera)."""
    cielo = np.clip((R[:, 1] + 0.9) / 1.8, 0.0, 1.0)
    cielo = cielo * cielo * (3.0 - 2.0 * cielo)
    return (AMBIENTE_BUIO + (AMBIENTE_CHIARO - AMBIENTE_BUIO) * cielo
            + FINESTRA * np.clip(R @ L, 0.0, 1.0) ** 12)


def rendi(parti, yaw, pitch, lato=512, ss=2):
    """Una vista del modello: PIL RGB lato x lato, il modello al centro."""
    W = H = lato * ss
    R = _rotazione(yaw, pitch)
    V_tutti = np.concatenate([p["verts"] for p in parti])
    centro = (V_tutti.max(0) + V_tutti.min(0)) / 2.0
    raggio = float(np.linalg.norm(V_tutti - centro, axis=1).max()) or 1.0
    dist = 3.5 * raggio
    # inquadratura: con f = 1 si misura l'ingombro proiettato, poi si scala
    q = (V_tutti - centro) @ R.T
    prof = dist - q[:, 2]
    px, py = q[:, 0] / prof, -q[:, 1] / prof
    f = 0.86 * W / max(px.max() - px.min(), py.max() - py.min(), 1e-12)
    cx = W / 2.0 - f * (px.max() + px.min()) / 2.0
    cy = H / 2.0 - f * (py.max() + py.min()) / 2.0

    L = np.array(LUCE, float)
    L /= np.linalg.norm(L)
    Hm = L + np.array([0.0, 0.0, 1.0])
    Hm /= np.linalg.norm(Hm)
    tela = _Tela(W, H)
    for p in parti:
        V, T = p["verts"], p["tris"]
        if not len(T):
            continue
        q = (V - centro) @ R.T
        prof = dist - q[:, 2]
        N = p["normals"] if p["normals"] is not None else _normali(V, T)
        Nv = N @ R.T
        lit = (AMBIENTE + DIFFUSA * np.clip(Nv @ L, 0, 1)
               + SPECULARE * np.clip(Nv @ Hm, 0, 1) ** LUCIDO)
        vivi_v = prof > 1e-9 * raggio
        P = dict(T=T, xs=cx + f * q[:, 0] / prof, ys=cy - f * q[:, 1] / prof,
                 inv=1.0 / np.where(vivi_v, prof, 1.0), UV=p["uvs"], lit=lit,
                 tex=p["tex"], vivi=vivi_v[T].all(1))
        if p.get("mr") is not None:
            occhio = np.array([0.0, 0.0, dist]) - q
            occhio /= np.maximum(np.linalg.norm(occhio, axis=1, keepdims=True), 1e-12)
            Rv = 2.0 * np.sum(Nv * occhio, axis=1, keepdims=True) * Nv - occhio
            P.update(mr=p["mr"], ambiente=_ambiente(Rv, L))
        _rasterizza(tela, P)
    im = Image.fromarray(tela.rgb.reshape(H, W, 3).astype(np.uint8))
    return im.resize((lato, lato), Image.LANCZOS) if ss > 1 else im


def _carattere(px):
    try:
        return ImageFont.load_default(size=px)
    except TypeError:                   # Pillow senza FreeType
        return ImageFont.load_default()


def viste(sorgente, lato=512):
    """Le quattro viste del controllo in un'immagine sola, 2 x 2, con i nomi.

    Torna (immagine PIL, ingombro in mm).
    """
    parti = leggi_glb(sorgente)
    if not parti:
        raise ValueError("il GLB non ha triangoli")
    tav = Image.new("RGB", (2 * lato, 2 * lato), (255, 255, 255))
    disegno = ImageDraw.Draw(tav)
    font = _carattere(max(12, lato // 26))
    for k, (nome, yaw, pitch) in enumerate(VISTE):
        x, y = (k % 2) * lato, (k // 2) * lato
        tav.paste(rendi(parti, yaw, pitch, lato), (x, y))
        disegno.rectangle([x, y, x + lato - 1, y + lato - 1], outline=(200, 200, 205))
        disegno.text((x + 10, y + 8), "%d  %s" % (k + 1, nome), fill=(60, 60, 70), font=font)
    return tav, ingombro_mm(parti)


def pagina(pdf_path, lato=1400, misure=False):
    """La prima pagina del PDF come la vede chi la apre, lato lungo `lato` px.

    Con `misure=True` torna anche (larghezza, altezza) del foglio in mm.
    Usa pdfium: va chiamata dentro il posto di costruzione, come ogni altra
    rasterizzazione (pdfium non e' thread-safe, vedi server.MAX_JOBS).
    """
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[0]
        page.set_cropbox(*page.get_mediabox())
        w, h = page.get_size()
        scala = lato / max(w, h, 1.0)
        im = page.render(scale=scala).to_pil().convert("RGB")
    finally:
        doc.close()
    return (im, (w * 25.4 / 72.0, h * 25.4 / 72.0)) if misure else im


def png(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()
