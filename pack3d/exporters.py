"""Export del modello mappato: OBJ + MTL + texture, oppure GLB monofile."""
from __future__ import annotations

import io
import json
import os
import struct

import numpy as np


def _normal(quad):
    a = np.array(quad[1], float) - np.array(quad[0], float)
    b = np.array(quad[3], float) - np.array(quad[0], float)
    n = -np.cross(a, b)
    return n / (np.linalg.norm(n) or 1.0)


# La pellicola delle finestre: una lastra di plastica trasparente, PET o OPP
# da qualche centesimo di mm, incollata dall'interno. Nel GLB e' un nodo suo,
# con un materiale suo: trasparente (BLEND), a due facce, liscio. Il bianco
# appena azzurro e il 22% di copertura la fanno leggere come un velo lucido
# sulla finestra senza annebbiare quello che c'e' dietro: provati in
# model-viewer sul ballotin Raffaello, al 16% non si vedeva, al 40% la
# finestra era lattiginosa. Niente KHR_materials_transmission, che sarebbe
# il vetro vero: un viewer che non la conosce mostrerebbe un foglio bianco
# opaco. Il controllo dell'AI non la guarda: vedi `vista.leggi_glb`.
PELLICOLA = {
    "name": "pellicola",
    "pbrMetallicRoughness": {"baseColorFactor": [0.94, 0.97, 1.0, 0.22],
                             "metallicFactor": 0.0, "roughnessFactor": 0.05},
    "alphaMode": "BLEND",
    "doubleSided": True,
}


def _pellicola(pellicola, unit_scale, add_view, accessors, materials):
    """Accessori e materiale della pellicola: la mesh da mettere nel GLB."""
    V = np.asarray(pellicola[0], float)
    T = np.asarray(pellicola[1], np.uint32).reshape(-1, 3)
    pos = (V * unit_scale).astype(np.float32)
    a_pos = len(accessors)
    accessors.append({"bufferView": add_view(pos.tobytes(), 34962),
                      "componentType": 5126, "count": len(pos), "type": "VEC3",
                      "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
    a_nrm = len(accessors)
    accessors.append({"bufferView": add_view(_normals(V, T).tobytes(), 34962),
                      "componentType": 5126, "count": len(pos), "type": "VEC3"})
    a_idx = len(accessors)
    accessors.append({"bufferView": add_view(T.ravel().tobytes(), 34963),
                      "componentType": 5125, "count": int(T.size),
                      "type": "SCALAR"})
    materials.append(dict(PELLICOLA))
    return {"name": "pellicola", "primitives": [{
        "attributes": {"POSITION": a_pos, "NORMAL": a_nrm},
        "indices": a_idx, "material": len(materials) - 1}]}


# --------------------------------------------------------------------------- #
# OBJ + MTL
# --------------------------------------------------------------------------- #
def write_obj(faces, outdir, basename="model", tex_quality=92):
    os.makedirs(outdir, exist_ok=True)
    obj, mtl = [], []
    obj.append(f"# generato da pack3d\nmtllib {basename}.mtl\n")
    vi = 1
    for f in faces:
        tex_name = f"{basename}_{f['name']}.jpg"
        f["tex"].save(os.path.join(outdir, tex_name), quality=tex_quality,
                      subsampling=0)
        n = _normal(f["quad"])
        mtl.append(f"newmtl {f['name']}\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\n"
                   f"d 1\nillum 1\nmap_Kd {tex_name}\n")
        obj.append(f"o {f['name']}")
        for v in f["quad"]:
            obj.append("v %.4f %.4f %.4f" % v)
        # in OBJ l'origine UV e' in basso a sinistra
        for u, v in [(0, 0), (1, 0), (1, 1), (0, 1)]:
            obj.append("vt %.6f %.6f" % (u, 1.0 - v))
        obj.append("vn %.6f %.6f %.6f" % tuple(n))
        obj.append(f"usemtl {f['name']}")
        # senso antiorario visto da fuori: con l'ordine diretto la faccia
        # risulta rivolta all'interno e i viewer con culling la scartano
        idx = [vi, vi + 3, vi + 2, vi + 1]
        obj.append("f " + " ".join(f"{i}/{i}/{(vi - 1)//4 + 1}" for i in idx))
        vi += 4
    with open(os.path.join(outdir, f"{basename}.obj"), "w") as fh:
        fh.write("\n".join(obj) + "\n")
    with open(os.path.join(outdir, f"{basename}.mtl"), "w") as fh:
        fh.write("\n".join(mtl) + "\n")
    return os.path.join(outdir, f"{basename}.obj")


# --------------------------------------------------------------------------- #
# L'atlante: le immagini delle facce in una texture sola
# --------------------------------------------------------------------------- #
# Un astuccio ha un'immagine per faccia, ma il modello ne porta una sola: le
# facce stanno in un atlante, ognuna nel suo riquadro, e le UV puntano li'.
# Cosi' la texture si puo' dare a parte e un viewer che la cambia - Glam Lab
# mette la texture scelta su tutti i materiali che ne hanno una - ritrova
# ogni faccia al suo posto. Fra un riquadro e l'altro c'e' il bordo della
# faccia ripetuto (`MARGINE_ATLANTE` px): i livelli ridotti della texture
# (mipmap) non prendono il colore della faccia accanto. Le UV cadono sui
# centri dei pixel di bordo, mezzo pixel dentro il riquadro, come faceva il
# bordo bloccato (CLAMP_TO_EDGE) della texture di una faccia sola.
MARGINE_ATLANTE = 8
NORMALE_PIATTA = (128, 128, 255)


def _scaffali(misure, margine):
    """`(L, A, posizioni)`: i riquadri `misure` (l, a) in file orizzontali,
    dal piu' alto, con `margine` px attorno a ognuno; `posizioni[i]` e'
    l'angolo in alto a sinistra dell'immagine i, margine escluso. Fra le
    larghezze possibili vince quella col lato piu' lungo piu' corto: il
    lato e' quello che deve stare sotto il massimo della texture."""
    ordine = sorted(range(len(misure)), key=lambda i: (-misure[i][1], -misure[i][0]))
    piene = [(l + 2 * margine, a + 2 * margine) for l, a in misure]
    minimo, totale = max(l for l, _ in piene), sum(l for l, _ in piene)
    meglio = None
    for passo in range(65):
        L = int(minimo + (totale - minimo) * passo / 64)
        pos, x, y, riga = [None] * len(misure), 0, 0, 0
        for i in ordine:
            l, a = piene[i]
            if x and x + l > L:
                x, y, riga = 0, y + riga, 0
            pos[i] = (x + margine, y + margine)
            x, riga = x + l, max(riga, a)
        larga = max(pos[i][0] + misure[i][0] + margine for i in ordine)
        prova = (max(larga, y + riga), larga * (y + riga), larga, y + riga, pos)
        if meglio is None or prova[:2] < meglio[:2]:
            meglio = prova
    return meglio[2], meglio[3], meglio[4]


def _incolla(tela, im, x, y, margine):
    """`im` sulla `tela` in (x, y), col suo bordo ripetuto per `margine` px."""
    a = np.asarray(im.convert("RGB"))
    a = np.pad(a, ((margine, margine), (margine, margine), (0, 0)), mode="edge")
    from PIL import Image
    tela.paste(Image.fromarray(a), (x - margine, y - margine))


def atlante(immagini, lato_max, normali=None, margine=MARGINE_ATLANTE):
    """Le `immagini` (PIL) in una texture sola, col lato piu' lungo entro
    `lato_max`: se non ci stanno, si riducono tutte della stessa misura.
    Torna `(texture, mappa_normali o None, riquadri)`: `riquadri[i]` e'
    `(x, y, l, a, L, A)`, dove sta l'immagine i e quanto e' grande la
    texture. `normali[i]`, se c'e', e' la mappa delle normali della stessa
    immagine: va nello stesso riquadro di una seconda texture, piatta dove
    non ce n'e'."""
    from PIL import Image
    s = 1.0
    while True:
        misure = [(max(1, round(im.width * s)), max(1, round(im.height * s)))
                  for im in immagini]
        L, A, pos = _scaffali(misure, margine)
        if max(L, A) <= lato_max or max(max(m) for m in misure) <= 1:
            break
        s *= lato_max / max(L, A) * 0.99
    tela = Image.new("RGB", (L, A), (255, 255, 255))
    for im, (x, y), m in zip(immagini, pos, misure):
        _incolla(tela, im if im.size == m else im.resize(m, Image.LANCZOS), x, y, margine)
    mappa = None
    if normali and any(n is not None for n in normali):
        mappa = Image.new("RGB", (L, A), NORMALE_PIATTA)
        for n, (x, y), m in zip(normali, pos, misure):
            if n is not None:
                _incolla(mappa, n if n.size == m else n.resize(m, Image.LANCZOS),
                         x, y, margine)
    return tela, mappa, [(x, y, m[0], m[1], L, A) for (x, y), m in zip(pos, misure)]


def uv_atlante(uv, riquadro):
    """Le UV di una faccia (0-1 sulla sua immagine) nel suo riquadro
    dell'atlante, sui centri dei pixel di bordo."""
    x, y, l, a, L, A = riquadro
    uv = np.asarray(uv, np.float64)
    return np.stack([(x + 0.5 + uv[:, 0] * (l - 1)) / L,
                     (y + 0.5 + uv[:, 1] * (a - 1)) / A], 1).astype(np.float32)


# --------------------------------------------------------------------------- #
# glTF binario (GLB) monofile
# --------------------------------------------------------------------------- #
def write_glb(faces, path, unit_scale=0.001, tex_quality=88, tex_max=2048,
              pellicola=None):
    """unit_scale: le quote sono in mm, glTF lavora in metri. `pellicola`,
    se c'e', e' `(V, T)` in mm: la pellicola trasparente delle finestre, un
    nodo a parte col suo materiale (`PELLICOLA`). Una faccia con la chiave
    `normale` porta la mappa delle normali del suo rilievo.

    Ogni faccia ha il suo materiale, col suo nome, ma la texture e' una
    sola: l'atlante delle immagini delle facce (`atlante`), entro `tex_max`
    px di lato. Lo stesso per le mappe delle normali, se ce ne sono."""
    buf = bytearray()
    views, accessors, images, textures, materials, prims = [], [], [], [], [], []

    def add_view(data, target=None):
        while len(buf) % 4:
            buf.append(0)
        off = len(buf)
        buf.extend(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    def primitiva(pos, nrm, uv, idx, materiale):
        pos = np.asarray(pos, np.float32)
        vp = add_view(pos.tobytes(), 34962)
        accessors.append({"bufferView": vp, "componentType": 5126,
                          "count": len(pos), "type": "VEC3",
                          "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
        a_pos = len(accessors) - 1
        vn = add_view(np.asarray(nrm, np.float32).tobytes(), 34962)
        accessors.append({"bufferView": vn, "componentType": 5126,
                          "count": len(pos), "type": "VEC3"})
        a_nrm = len(accessors) - 1
        vt = add_view(np.asarray(uv, np.float32).tobytes(), 34962)
        accessors.append({"bufferView": vt, "componentType": 5126,
                          "count": len(pos), "type": "VEC2"})
        a_uv = len(accessors) - 1
        # una faccia incisa ha piu' di 65 535 vertici solo in teoria; il
        # quad ne ha quattro, e resta a 16 bit come e' sempre stato
        grandi = len(pos) > 65535
        ix = np.asarray(idx, np.uint32 if grandi else np.uint16).reshape(-1)
        vi = add_view(ix.tobytes(), 34963)
        accessors.append({"bufferView": vi,
                          "componentType": 5125 if grandi else 5123,
                          "count": len(ix), "type": "SCALAR"})
        prims.append({"attributes": {"POSITION": a_pos, "NORMAL": a_nrm,
                                     "TEXCOORD_0": a_uv},
                      "indices": len(accessors) - 1, "material": materiale})

    # le immagini delle facce, una volta sola anche se piu' facce hanno la
    # stessa (le tinte piene dell'interno e del taglio), e la tinta del solco
    # delle incisioni se qualche faccia ne ha uno
    solco = None
    if any(f.get("maglia") and f["maglia"][1] is not None for f in faces):
        from PIL import Image
        from .folding import TAGLIO
        solco = Image.new("RGB", (4, 4), TAGLIO)
    chiavi, immagini, normali = {}, [], []

    def posto(im, normale=None):
        k = (id(im), id(normale))
        if k not in chiavi:
            chiavi[k] = len(immagini)
            immagini.append(im)
            normali.append(normale)
        return chiavi[k]

    for f in faces:
        posto(f["tex"], f.get("normale"))
    if solco is not None:
        posto(solco)
    tela, mappa, riquadri = atlante(immagini, tex_max, normali)

    def materiale(nome, normale):
        m = {"name": nome,
             "pbrMetallicRoughness": {"baseColorTexture": {"index": 0},
                                      "metallicFactor": 0.0,
                                      "roughnessFactor": 0.85}}
        if normale is not None:
            # il rilievo della faccia (`rilievo.sulle_facce`)
            m["normalTexture"] = {"index": 1}
        materials.append(m)
        return len(materials) - 1

    m_solco = None
    for f in faces:
        q = riquadri[posto(f["tex"], f.get("normale"))]
        m = materiale(f["name"], f.get("normale"))
        if f.get("maglia"):
            # la faccia incisa (`incisioni.incidi`): la superficie con la sua
            # texture, il solco con la tinta del cartoncino tagliato
            sup, inc = f["maglia"]
            if sup is not None:
                V, N, UV, T = sup
                primitiva(np.asarray(V) * unit_scale, N, uv_atlante(UV, q), T, m)
            if inc is not None:
                if m_solco is None:
                    m_solco = materiale("solco", None)
                V, N, UV, T = inc
                primitiva(np.asarray(V) * unit_scale, N,
                          uv_atlante(UV, riquadri[posto(solco)]), T, m_solco)
            continue
        quad = np.array(f["quad"], np.float32) * unit_scale
        nrm = np.tile(_normal(f["quad"]).astype(np.float32), (4, 1))
        uv = uv_atlante([[0, 0], [1, 0], [1, 1], [0, 1]], q)
        idx = np.array([0, 2, 1, 0, 3, 2], np.uint16)
        primitiva(quad, nrm, uv, idx, m)

    # l'atlante, e accanto, nello stesso ordine, le normali in PNG
    bio = io.BytesIO()
    tela.save(bio, "JPEG", quality=tex_quality, subsampling=0)
    images.append({"bufferView": add_view(bio.getvalue()), "mimeType": "image/jpeg"})
    textures.append({"source": 0})
    if mappa is not None:
        bio = io.BytesIO()
        mappa.save(bio, "PNG", optimize=True)
        images.append({"bufferView": add_view(bio.getvalue()), "mimeType": "image/png"})
        textures.append({"source": 1})

    nodi = [{"mesh": 0, "name": "packaging"}]
    mesh = [{"name": "packaging", "primitives": prims}]
    if pellicola is not None:
        nodi.append({"mesh": 1, "name": "pellicola"})
        mesh.append(_pellicola(pellicola, unit_scale, add_view, accessors,
                               materials))
    gltf = {
        "asset": {"version": "2.0", "generator": "pack3d"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodi)))}],
        "nodes": nodi,
        "meshes": mesh,
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(buf)}],
        "images": images,
        "samplers": [{"magFilter": 9729, "minFilter": 9987,
                      "wrapS": 33071, "wrapT": 33071}],
        "textures": [dict(t, sampler=0) for t in textures],
        "materials": materials,
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    bin_ = bytes(buf) + b"\0" * ((4 - len(buf) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(bin_)
    with open(path, "wb") as fh:
        fh.write(b"glTF" + struct.pack("<II", 2, total))
        fh.write(struct.pack("<I", len(js)) + b"JSON" + js)
        fh.write(struct.pack("<I", len(bin_)) + b"BIN\0" + bin_)
    return path


# --------------------------------------------------------------------------- #
# export di mesh triangolari (superfici curve: flowpack, doypack, ...)
# --------------------------------------------------------------------------- #
def _normals(V, tris):
    N = np.zeros_like(V)
    a, b, c = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    for k in range(3):
        np.add.at(N, tris[:, k], fn)
    n = np.linalg.norm(N, axis=1, keepdims=True)
    return (N / np.where(n == 0, 1, n)).astype(np.float32)


def write_obj_mesh(V, UV, tris, tex, outdir, basename="model", tex_quality=92):
    os.makedirs(outdir, exist_ok=True)
    tex_name = f"{basename}_film.jpg"
    tex.save(os.path.join(outdir, tex_name), quality=tex_quality, subsampling=0)
    N = _normals(V, tris)
    lines = [f"# generato da pack3d\nmtllib {basename}.mtl", "o packaging"]
    lines += ["v %.4f %.4f %.4f" % tuple(p) for p in V]
    # in OBJ l'origine UV e' in basso a sinistra
    lines += ["vt %.6f %.6f" % (u, 1.0 - v) for u, v in UV]
    lines += ["vn %.6f %.6f %.6f" % tuple(n) for n in N]
    lines.append("usemtl film")
    for t in tris:
        a, b, c = t + 1
        lines.append(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}")
    with open(os.path.join(outdir, f"{basename}.obj"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(outdir, f"{basename}.mtl"), "w") as fh:
        fh.write("newmtl film\nKa 1 1 1\nKd 1 1 1\nKs 0.08 0.08 0.08\nNs 40\n"
                 f"d 1\nillum 2\nmap_Kd {tex_name}\n")
    return os.path.join(outdir, f"{basename}.obj")


def write_glb_mesh(V, UV, tris, tex, path, unit_scale=0.001,
                   tex_quality=88, tex_max=2048, parti=None, mr=None,
                   normale=None, pellicola=None):
    """Una maglia sola con la sua texture, in GLB.

    `parti`, se c'e', e' `[(nome, primo, ultimo)]` sui triangoli: ognuna
    diventa un NODO con la sua mesh, sugli stessi vertici e la stessa
    texture. Serve dove il pack e' fatto di elementi separati - il display
    con la plancia, che sta in piedi sul retro e non e' incollata al blocco -
    e chi apre il modello li deve poter prendere uno per uno. Senza `parti` il
    file e' quello di sempre: un nodo, una mesh.

    `mr`, se c'e', e' la mappa metallo/ruvidita' di glTF, nello stesso telaio
    della texture: ruvidita' nel verde, metallo nel blu. Viene dai DT del
    materiale (`materiali.py`) e va in PNG, perche' il JPEG sui bordi di una
    maschera inventa metallo dove non c'e'. Senza, il materiale e' quello di
    sempre: plastica, ruvidita' 0,42.

    `normale`, se c'e', e' la mappa delle normali del rilievo (`rilievo.py`)
    sulla stessa texture, anche a una risoluzione sua: va in PNG, perche' e'
    un dato e non un colore. `pellicola` e' quella di `write_glb`.
    """
    buf = bytearray()
    views, accessors = [], []

    def add_view(data, target=None):
        while len(buf) % 4:
            buf.append(0)
        off = len(buf)
        buf.extend(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    pos = (np.asarray(V, np.float32) * unit_scale)
    nrm = _normals(np.asarray(V, float), tris)
    uv = np.asarray(UV, np.float32)

    a_pos = len(accessors)
    accessors.append({"bufferView": add_view(pos.tobytes(), 34962),
                      "componentType": 5126, "count": len(pos), "type": "VEC3",
                      "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
    a_nrm = len(accessors)
    accessors.append({"bufferView": add_view(nrm.tobytes(), 34962),
                      "componentType": 5126, "count": len(nrm), "type": "VEC3"})
    a_uv = len(accessors)
    accessors.append({"bufferView": add_view(uv.tobytes(), 34962),
                      "componentType": 5126, "count": len(uv), "type": "VEC2"})
    tri = np.asarray(tris, np.uint32).reshape(-1, 3)
    pezzi = parti or [("flowpack", 0, len(tri))]
    a_idx = []
    for _nome, t0, t1 in pezzi:
        ix = tri[t0:t1].ravel()
        a_idx.append(len(accessors))
        accessors.append({"bufferView": add_view(ix.tobytes(), 34963),
                          "componentType": 5125, "count": len(ix),
                          "type": "SCALAR"})

    im = tex
    if max(im.size) > tex_max:
        r = tex_max / max(im.size)
        im = im.resize((int(im.width * r), int(im.height * r)))
    bio = io.BytesIO()
    im.convert("RGB").save(bio, "JPEG", quality=tex_quality, subsampling=0)
    iv = add_view(bio.getvalue())
    immagini = [{"bufferView": iv, "mimeType": "image/jpeg"}]
    trame = [{"source": 0, "sampler": 0}]
    materiale = {"name": "film", "pbrMetallicRoughness": {
        "baseColorTexture": {"index": 0},
        "metallicFactor": 0.0, "roughnessFactor": 0.42}}
    if mr is not None:
        from PIL import Image
        m = mr if mr.size == im.size else mr.resize(im.size, Image.BILINEAR)
        bio = io.BytesIO()
        m.convert("RGB").save(bio, "PNG", optimize=True)
        immagini.append({"bufferView": add_view(bio.getvalue()),
                         "mimeType": "image/png"})
        trame.append({"source": 1, "sampler": 0})
        materiale = {"name": "film", "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0},
            "metallicRoughnessTexture": {"index": 1},
            "metallicFactor": 1.0, "roughnessFactor": 1.0}}
    if normale is not None:
        bio = io.BytesIO()
        normale.convert("RGB").save(bio, "PNG", optimize=True)
        immagini.append({"bufferView": add_view(bio.getvalue()),
                         "mimeType": "image/png"})
        trame.append({"source": len(immagini) - 1, "sampler": 0})
        materiale["normalTexture"] = {"index": len(trame) - 1}

    nodi = [{"mesh": k, "name": nome}
            for k, (nome, _t0, _t1) in enumerate(pezzi)]
    mesh = [{"name": nome, "primitives": [{
        "attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "TEXCOORD_0": a_uv},
        "indices": a_idx[k], "material": 0}]}
        for k, (nome, _t0, _t1) in enumerate(pezzi)]
    materiali = [materiale]
    if pellicola is not None:
        nodi.append({"mesh": len(mesh), "name": "pellicola"})
        mesh.append(_pellicola(pellicola, unit_scale, add_view, accessors,
                               materiali))
    gltf = {
        "asset": {"version": "2.0", "generator": "pack3d"},
        "scene": 0, "scenes": [{"nodes": list(range(len(nodi)))}],
        "nodes": nodi,
        "meshes": mesh,
        "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": len(buf)}],
        "images": immagini,
        "samplers": [{"magFilter": 9729, "minFilter": 9987,
                      "wrapS": 33071, "wrapT": 33071}],
        "textures": trame,
        "materials": materiali,
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    bin_ = bytes(buf) + b"\0" * ((4 - len(buf) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(bin_)
    with open(path, "wb") as fh:
        fh.write(b"glTF" + struct.pack("<II", 2, total))
        fh.write(struct.pack("<I", len(js)) + b"JSON" + js)
        fh.write(struct.pack("<I", len(bin_)) + b"BIN\0" + bin_)
    return path
