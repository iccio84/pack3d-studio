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
def write_glb(faces, path, unit_scale=0.001, tex_quality=88, tex_max=2048):
    """unit_scale: le quote sono in mm, glTF lavora in metri."""
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

    for f in faces:
        quad = np.array(f["quad"], np.float32) * unit_scale
        nrm = np.tile(_normal(f["quad"]).astype(np.float32), (4, 1))
        uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32)
        idx = np.array([0, 2, 1, 0, 3, 2], np.uint16)

        vp = add_view(quad.tobytes(), 34962)
        accessors.append({"bufferView": vp, "componentType": 5126, "count": 4,
                          "type": "VEC3",
                          "min": quad.min(0).tolist(), "max": quad.max(0).tolist()})
        a_pos = len(accessors) - 1
        vn = add_view(nrm.tobytes(), 34962)
        accessors.append({"bufferView": vn, "componentType": 5126, "count": 4,
                          "type": "VEC3"})
        a_nrm = len(accessors) - 1
        vt = add_view(uv.tobytes(), 34962)
        accessors.append({"bufferView": vt, "componentType": 5126, "count": 4,
                          "type": "VEC2"})
        a_uv = len(accessors) - 1
        vi = add_view(idx.tobytes(), 34963)
        accessors.append({"bufferView": vi, "componentType": 5123, "count": 6,
                          "type": "SCALAR"})
        a_idx = len(accessors) - 1

        im = f["tex"]
        if max(im.size) > tex_max:
            r = tex_max / max(im.size)
            im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))))
        bio = io.BytesIO()
        im.convert("RGB").save(bio, "JPEG", quality=tex_quality, subsampling=0)
        iv = add_view(bio.getvalue())
        images.append({"bufferView": iv, "mimeType": "image/jpeg"})
        textures.append({"source": len(images) - 1})
        materials.append({
            "name": f["name"],
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": len(textures) - 1},
                "metallicFactor": 0.0, "roughnessFactor": 0.85,
            },
        })
        prims.append({"attributes": {"POSITION": a_pos, "NORMAL": a_nrm,
                                     "TEXCOORD_0": a_uv},
                      "indices": a_idx, "material": len(materials) - 1})

    gltf = {
        "asset": {"version": "2.0", "generator": "pack3d"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "packaging"}],
        "meshes": [{"name": "packaging", "primitives": prims}],
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
                   tex_quality=88, tex_max=2048):
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
    idx = np.asarray(tris, np.uint32).ravel()

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
    a_idx = len(accessors)
    accessors.append({"bufferView": add_view(idx.tobytes(), 34963),
                      "componentType": 5125, "count": len(idx), "type": "SCALAR"})

    im = tex
    if max(im.size) > tex_max:
        r = tex_max / max(im.size)
        im = im.resize((int(im.width * r), int(im.height * r)))
    bio = io.BytesIO()
    im.convert("RGB").save(bio, "JPEG", quality=tex_quality, subsampling=0)
    iv = add_view(bio.getvalue())

    gltf = {
        "asset": {"version": "2.0", "generator": "pack3d"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "flowpack"}],
        "meshes": [{"name": "flowpack", "primitives": [{
            "attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "TEXCOORD_0": a_uv},
            "indices": a_idx, "material": 0}]}],
        "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": len(buf)}],
        "images": [{"bufferView": iv, "mimeType": "image/jpeg"}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987,
                      "wrapS": 33071, "wrapT": 33071}],
        "textures": [{"source": 0, "sampler": 0}],
        "materials": [{"name": "film", "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0},
            "metallicFactor": 0.0, "roughnessFactor": 0.42}}],
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
