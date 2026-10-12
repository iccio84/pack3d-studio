"""La texture del modello, a parte dal GLB.

E' l'immagine che il GLB usa come colore del pack, con le stesse UV, ed e'
lo steso del PDF: la grafica pulita, nel verso del foglio, inquadrata sul DT
(`pack3d.steso`). Ci si sovrappone il nuovo artwork di una variante e la si
rimette sul modello - come fa Glam Lab con le texture della sua sezione - e
ogni cosa torna al suo posto. Un modello ne ha una per foglio: una quasi
sempre; due la coppa col tappo e il cono col lid, che vengono da due PDF, e
il riempimento, il vassoio e il pack. A parte si danno tutte, ma Glam, che
mette una texture sola su tutto il modello, la riceve solo se e' una
(`per_glam`).

Glam accetta immagini fino a 5000 px di lato (`LATO_GLAM`). Una texture piu'
grande - un display in HD arriva a 8192 px - si riduce in proporzione: le UV
sono frazioni dell'immagine, e restano giuste. Le mappe del metallo, della
ruvidita' e del rilievo restano nel modello: Glam cambia solo il colore.

La pagina dello Space fa lo stesso, nel browser, sul GLB che ha appena
ricevuto (`textureDelGlb` in pack3d_studio.html): la regola e' la stessa.
"""
from __future__ import annotations

import io
import json
import struct

LATO_GLAM = 5000
# la qualita' del JPEG di una texture ridotta; una che non si riduce esce coi
# byte del GLB, senza ricomprimerla
QUALITA = 90
ESTENSIONI = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _parti(glb):
    """`(json, binario)` di un GLB."""
    if glb[:4] != b"glTF":
        raise ValueError("non e' un GLB")
    n = struct.unpack_from("<I", glb, 12)[0]
    J = json.loads(glb[20:20 + n])
    o = 20 + n
    binario = b""
    if len(glb) >= o + 8 and glb[o + 4:o + 8] == b"BIN\0":
        m = struct.unpack_from("<I", glb, o)[0]
        binario = glb[o + 8:o + 8 + m]
    return J, binario


def texture(glb, lato_max=LATO_GLAM):
    """Le texture del colore del modello, una per immagine, nell'ordine del
    GLB: `[{"nome", "dati", "mime", "estensione", "lato", "ridotta",
    "sorgente"}]`. `nome` e' quello della prima mesh che la usa (vassoio,
    flowpack, packaging...), `lato` la misura `(l, a)` del file che esce,
    `sorgente` l'indice dell'immagine nel GLB."""
    from PIL import Image
    J, binario = _parti(glb)
    materiali = J.get("materials") or []

    def colore(m):
        """L'immagine del colore del materiale m, o None."""
        t = (materiali[m].get("pbrMetallicRoughness") or {}).get("baseColorTexture")
        return None if t is None else J["textures"][t["index"]]["source"]

    usate = []
    for m in range(len(materiali)):
        s = colore(m)
        if s is not None and s not in usate:
            usate.append(s)
    # la mesh che usa ogni immagine, per il nome del file
    nomi = {}
    for mesh in J.get("meshes") or []:
        for p in mesh.get("primitives") or []:
            s = colore(p["material"]) if "material" in p else None
            if s is not None:
                nomi.setdefault(s, mesh.get("name") or "")
    fuori = []
    for s in usate:
        im = J["images"][s]
        bv = J["bufferViews"][im["bufferView"]]
        a = bv.get("byteOffset", 0)
        dati = binario[a:a + bv["byteLength"]]
        mime = im.get("mimeType", "image/jpeg")
        img = Image.open(io.BytesIO(dati))
        lato, ridotta = img.size, False
        if max(img.size) > lato_max:
            r = lato_max / max(img.size)
            lato = (max(1, round(img.width * r)), max(1, round(img.height * r)))
            bio = io.BytesIO()
            img.convert("RGB").resize(lato, Image.LANCZOS).save(
                bio, "JPEG", quality=QUALITA, subsampling=0)
            dati, mime, ridotta = bio.getvalue(), "image/jpeg", True
        fuori.append({"nome": nomi.get(s, ""), "dati": dati, "mime": mime,
                      "estensione": ESTENSIONI.get(mime, "jpg"), "lato": lato,
                      "ridotta": ridotta, "sorgente": s})
    return fuori


def per_glam(glb, lato_max=LATO_GLAM):
    """La texture da mettere nella sezione texture di Glam, o None: Glam la
    mette su tutti i materiali del modello che hanno un colore da immagine,
    e va bene solo se l'immagine e' una."""
    t = texture(glb, lato_max)
    return t[0] if len(t) == 1 else None


def nomi_file(base, tex):
    """I nomi dei file delle texture di un modello che si chiama `base`:
    `base_texture.jpg` se e' una, `base_texture_vassoio.jpg`... se sono
    piu' d'una."""
    if len(tex) == 1:
        return ["%s_texture.%s" % (base, tex[0]["estensione"])]
    nomi = []
    for i, t in enumerate(tex, 1):
        n = "".join(c if c.isalnum() else "_" for c in t["nome"]).strip("_") or str(i)
        nome = "%s_texture_%s.%s" % (base, n, t["estensione"])
        if nome in nomi:
            nome = "%s_texture_%s_%d.%s" % (base, n, i, t["estensione"])
        nomi.append(nome)
    return nomi
