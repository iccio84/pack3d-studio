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
# glTF binario (GLB) monofile
# --------------------------------------------------------------------------- #
def write_glb(faces, path, unit_scale=0.001, tex_quality=88, tex_max=2048,
              pellicola=None):
    """unit_scale: le quote sono in mm, glTF lavora in metri. `pellicola`,
    se c'e', e' `(V, T)` in mm: la pellicola trasparente delle finestre, un
    nodo a parte col suo materiale (`PELLICOLA`). Una faccia con la chiave
    `normale` porta la mappa delle normali del suo rilievo."""
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

    def materiale(nome, im, normale=None):
        if max(im.size) > tex_max:
            r = tex_max / max(im.size)
            im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))))
        bio = io.BytesIO()
        im.convert("RGB").save(bio, "JPEG", quality=tex_quality, subsampling=0)
        iv = add_view(bio.getvalue())
        images.append({"bufferView": iv, "mimeType": "image/jpeg"})
        textures.append({"source": len(images) - 1})
        materials.append({
            "name": nome,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": len(textures) - 1},
                "metallicFactor": 0.0, "roughnessFactor": 0.85,
            },
        })
        if normale is not None:
            # il rilievo della faccia (`rilievo.sulle_facce`), in PNG
            bio = io.BytesIO()
            normale.convert("RGB").save(bio, "PNG", optimize=True)
            images.append({"bufferView": add_view(bio.getvalue()),
                           "mimeType": "image/png"})
            textures.append({"source": len(images) - 1})
            materials[-1]["normalTexture"] = {"index": len(textures) - 1}
        return len(materials) - 1

    solco = None
    for f in faces:
        if f.get("maglia"):
            # la faccia incisa (`incisioni.incidi`): la superficie con la sua
            # texture, il solco con la tinta del cartoncino tagliato
            m = materiale(f["name"], f["tex"], f.get("normale"))
            sup, inc = f["maglia"]
            if sup is not None:
                V, N, UV, T = sup
                primitiva(np.asarray(V) * unit_scale, N, UV, T, m)
            if inc is not None:
                if solco is None:
                    from PIL import Image
                    from .folding import TAGLIO
                    solco = materiale("solco", Image.new("RGB", (4, 4), TAGLIO))
                V, N, UV, T = inc
                primitiva(np.asarray(V) * unit_scale, N, UV, T, solco)
            continue
        quad = np.array(f["quad"], np.float32) * unit_scale
        nrm = np.tile(_normal(f["quad"]).astype(np.float32), (4, 1))
        uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32)
        idx = np.array([0, 2, 1, 0, 3, 2], np.uint16)
        # prima i vertici e poi l'immagine, come e' sempre stato: un astuccio
        # senza incisioni esce identico al byte
        primitiva(quad, nrm, uv, idx, len(materials))
        materiale(f["name"], f["tex"], f.get("normale"))

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
