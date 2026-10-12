"""L'atlante: un'immagine sola per un modello fatto di piu' pezzi.

Un modello fatto di piu' fogli - la coppa col tappo, il cono col lid, il
riempimento col vassoio e il pack - nasce con una texture per foglio, ognuna
lo steso del suo PDF (`pack3d.steso`). Ma Glam Lab mette una texture sola su
tutti i materiali di un modello, e il template (`pack3d.template`) e' la tela
di quella texture: con due texture, a Glam non andavano ne' l'una ne'
l'altro. Qui le texture diventano un'immagine sola, l'**atlante**, e il
modello torna ad averne una.

- **Ogni zona e' lo steso del suo foglio**, intero e nel suo verso, alla sua
  risoluzione: l'atlante li mette uno accanto all'altro, non li tocca. La
  coppa e il cono, che rendono i due fogli allo stesso dpi, hanno le zone
  alla stessa scala; nel riempimento il vassoio e il pack hanno ognuno la
  sua.
- **La disposizione** e' quella, fra le poche che si provano (`disponi`), col
  lato piu' corto: in fila, in colonna, il pezzo grande con gli altri accanto
  o sotto. Fra una zona e l'altra un margine di `MARGINE` pixel per parte,
  coi pixel del bordo ripetuti: il filtro della texture, da lontano, non
  mescola i pezzi.
- **Le UV** di ogni triangolo puntano alla sua zona; le altre mappe - il
  metallo e la ruvidita' del flowpack, il rilievo - vanno in un atlante loro
  con la stessa disposizione.
- **Le zone** restano scritte nel GLB, negli `extras` dell'immagine:
  `{"pack3d_zone": [{"nome", "x", "y", "w", "h"}]}`, in frazioni
  dell'atlante. Le leggono il template, per scrivere il nome di ogni pezzo,
  e il controllo degli stesi (`prove/parco.py stesi`), che cerca ogni zona
  nel suo PDF.
- **Al massimo `LATO` pixel di lato**, il tetto della texture HD: un atlante
  piu' grande si riduce tutto insieme, e le zone restano in proporzione.
"""
from __future__ import annotations

import io

import numpy as np

# px di margine attorno a ogni zona
MARGINE = 16
# il lato massimo dell'atlante: quello della texture HD (`artwork.TEXTURE`)
LATO = 8192
QUALITA = 90
# i ruoli delle mappe di un materiale glTF, oltre al colore, e il pixel che
# riempie l'atlante dove quel ruolo non c'e'
RUOLI = {"metallicRoughnessTexture": (0, 255, 0), "normalTexture": (128, 128, 255),
         "occlusionTexture": (255, 255, 255), "emissiveTexture": (0, 0, 0)}


def disponi(misure, margine=MARGINE):
    """`(W, H, angoli)`: la disposizione delle immagini di `misure` [(l, a)]
    col lato maggiore piu' corto, e a parita' l'area piu' piccola. `angoli`
    sono gli angoli in alto a sinistra di ogni immagine, margine escluso."""
    celle = [(w + 2 * margine, h + 2 * margine) for w, h in misure]
    n = len(celle)
    prove = []

    def fila(ordine, x0=0, y0=0):
        pos, x = {}, x0
        for i in ordine:
            pos[i] = (x, y0)
            x += celle[i][0]
        return pos

    def colonna(ordine, x0=0, y0=0):
        pos, y = {}, y0
        for i in ordine:
            pos[i] = (x0, y)
            y += celle[i][1]
        return pos
    per_area = sorted(range(n), key=lambda i: -celle[i][0] * celle[i][1])
    prove.append(fila(per_area))
    prove.append(colonna(per_area))
    if n > 2:
        grande, altri = per_area[0], per_area[1:]
        gw, gh = celle[grande]
        a = colonna(altri, gw, 0)
        a[grande] = (0, 0)
        b = fila(altri, 0, gh)
        b[grande] = (0, 0)
        prove += [a, b]
    migliore = None
    for pos in prove:
        W = max(pos[i][0] + celle[i][0] for i in range(n))
        H = max(pos[i][1] + celle[i][1] for i in range(n))
        chiave = (max(W, H), W * H)
        if migliore is None or chiave < migliore[0]:
            migliore = (chiave, W, H, pos)
    _c, W, H, pos = migliore
    return W, H, [(pos[i][0] + margine, pos[i][1] + margine) for i in range(n)]


def _incolla(tela, im, x, y, margine):
    """`im` sulla `tela` in (x, y), coi pixel del bordo ripetuti nel
    margine."""
    from PIL import Image
    a = np.asarray(im)
    pad = ((margine, margine), (margine, margine)) + ((0, 0),) * (a.ndim - 2)
    tela.paste(Image.fromarray(np.pad(a, pad, mode="edge")), (x - margine, y - margine))


def _da_glb(glb):
    from .riempimento import leggi
    return leggi(glb)


def _immagine(J, B, i):
    from PIL import Image
    bv = J["bufferViews"][J["images"][i]["bufferView"]]
    a = bv.get("byteOffset", 0)
    return Image.open(io.BytesIO(bytes(B[a:a + bv["byteLength"]])))


def _ricompatta(J, B, nuove):
    """Il binario rifatto con le sole viste che il GLB usa ancora, piu' le
    immagini `nuove` [(indice immagine, byte)]: le immagini vecchie che
    l'atlante sostituisce non restano nel file."""
    nuove = dict(nuove)
    usate = set()
    for a in J.get("accessors", []):
        if "bufferView" in a:
            usate.add(a["bufferView"])
    for i, im in enumerate(J.get("images", [])):
        if "bufferView" in im and i not in nuove:
            usate.add(im["bufferView"])
    viste, nuovo, mappa = [], bytearray(), {}
    for k in sorted(usate):
        v = dict(J["bufferViews"][k])
        a = v.get("byteOffset", 0)
        while len(nuovo) % 4:
            nuovo.append(0)
        v["byteOffset"] = len(nuovo)
        nuovo.extend(B[a:a + v["byteLength"]])
        mappa[k] = len(viste)
        viste.append(v)
    for a in J.get("accessors", []):
        if "bufferView" in a:
            a["bufferView"] = mappa[a["bufferView"]]
    for i, im in enumerate(J.get("images", [])):
        if i in nuove:
            continue
        if "bufferView" in im:
            im["bufferView"] = mappa[im["bufferView"]]
    for i, dati in nuove.items():
        while len(nuovo) % 4:
            nuovo.append(0)
        viste.append({"buffer": 0, "byteOffset": len(nuovo), "byteLength": len(dati)})
        nuovo.extend(dati)
        J["images"][i]["bufferView"] = len(viste) - 1
    J["bufferViews"] = viste
    J["buffers"] = [{"byteLength": len(nuovo)}]
    return bytes(nuovo)


def unisci(glb, lato=LATO):
    """`(glb, zone)`: il GLB con le texture del colore unite in un atlante, e
    le zone; `(glb, None)`, lo stesso GLB, se il colore e' gia' un'immagine
    sola. Solleva ValueError se un vertice e' di due pezzi."""
    from PIL import Image
    from .riempimento import _dati, scrivi
    J, B = _da_glb(glb)
    B = bytearray(B)
    materiali = J.get("materials") or []
    trame = J.get("textures") or []

    def fonte(t):
        return None if t is None else trame[t["index"]]["source"]
    colore = [fonte((m.get("pbrMetallicRoughness") or {}).get("baseColorTexture"))
              for m in materiali]
    fonti = []
    for s in colore:
        if s is not None and s not in fonti:
            fonti.append(s)
    if len(fonti) < 2:
        return glb, None
    for m in materiali:
        for t in [(m.get("pbrMetallicRoughness") or {}).get(r) for r in
                  ("baseColorTexture", "metallicRoughnessTexture")] + \
                [m.get(r) for r in RUOLI if r != "metallicRoughnessTexture"]:
            if t is not None and t.get("texCoord", 0) != 0:
                raise ValueError("atlante: un materiale usa un'altra UV")
    # il nome di ogni pezzo: la prima mesh che ne usa il colore
    nomi = {}
    for mesh in J.get("meshes") or []:
        for p in mesh.get("primitives") or []:
            s = colore[p["material"]] if "material" in p else None
            if s is not None:
                nomi.setdefault(s, mesh.get("name") or "pezzo")

    immagini = [_immagine(J, B, s).convert("RGB") for s in fonti]
    W, H, angoli = disponi([im.size for im in immagini])
    if max(W, H) > lato:
        r = (lato - 2 * MARGINE * len(fonti)) / float(max(W, H))
        immagini = [im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))),
                              Image.LANCZOS) for im in immagini]
        W, H, angoli = disponi([im.size for im in immagini])
    zona = {s: (x, y, im.width, im.height)
            for s, (x, y), im in zip(fonti, angoli, immagini)}

    # le UV: ogni vertice nella zona del suo pezzo
    di = {}
    for mesh in J.get("meshes") or []:
        for p in mesh.get("primitives") or []:
            s = colore[p["material"]] if "material" in p else None
            uv = p["attributes"].get("TEXCOORD_0")
            if s is None or uv is None:
                continue
            n = J["accessors"][uv]["count"]
            chi = di.setdefault(uv, np.full(n, -1, np.int64))
            ix = (_dati(J, B, p["indices"]).astype(np.int64).ravel()
                  if "indices" in p else np.arange(n))
            altri = chi[ix]
            if np.any((altri >= 0) & (altri != s)):
                raise ValueError("atlante: un vertice e' di due pezzi")
            chi[ix] = s
    for uv, chi in di.items():
        a = J["accessors"][uv]
        bv = J["bufferViews"][a["bufferView"]]
        if a["componentType"] != 5126 or a["type"] != "VEC2" or \
                bv.get("byteStride", 8) != 8:
            raise ValueError("atlante: UV non in float32 compatti")
        U = _dati(J, B, uv).astype(np.float64)
        for s, (x, y, w, h) in zona.items():
            q = chi == s
            U[q, 0] = (x + U[q, 0] * w) / W
            U[q, 1] = (y + U[q, 1] * h) / H
        inizio = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        dati = U.astype(np.float32).tobytes()
        B[inizio:inizio + len(dati)] = dati
        a["min"] = U.min(0).astype(np.float32).tolist()
        a["max"] = U.max(0).astype(np.float32).tolist()

    # l'atlante del colore, e uno per ogni altra mappa con la stessa
    # disposizione
    tela = Image.new("RGB", (W, H), (255, 255, 255))
    for s, im in zip(fonti, immagini):
        x, y, _w, _h = zona[s]
        _incolla(tela, im, x, y, MARGINE)
    bio = io.BytesIO()
    tela.save(bio, "JPEG", quality=QUALITA, subsampling=0)
    nuove = [(fonti[0], bio.getvalue())]
    J["images"][fonti[0]] = {"mimeType": "image/jpeg", "bufferView": 0, "extras": {
        "pack3d_zone": [{"nome": nomi.get(s, "pezzo"), "x": zona[s][0] / W,
                         "y": zona[s][1] / H, "w": zona[s][2] / W, "h": zona[s][3] / H}
                        for s in fonti]}}
    sostituite = {s: fonti[0] for s in fonti[1:]}
    for ruolo, fondo in RUOLI.items():
        dove = (lambda m: (m.get("pbrMetallicRoughness") or {})) \
            if ruolo == "metallicRoughnessTexture" else (lambda m: m)
        per_pezzo = {}
        for m, s in zip(materiali, colore):
            t = dove(m).get(ruolo)
            if s is not None and t is not None:
                per_pezzo.setdefault(s, fonte(t))
        if not per_pezzo:
            continue
        mappa = Image.new("RGB", (W, H), fondo)
        for s, i in per_pezzo.items():
            x, y, w, h = zona[s]
            _incolla(mappa, _immagine(J, B, i).convert("RGB").resize((w, h), Image.BILINEAR),
                     x, y, MARGINE)
        bio = io.BytesIO()
        mappa.save(bio, "PNG", optimize=True)
        prima = min(per_pezzo.values())
        nuove.append((prima, bio.getvalue()))
        J["images"][prima] = {"mimeType": "image/png", "bufferView": 0}
        for i in per_pezzo.values():
            if i != prima:
                sostituite[i] = prima
    # le immagini sostituite vanno via, gli indici si stringono, e le
    # texture che le usavano usano l'atlante
    restano = [i for i in range(len(J["images"])) if i not in sostituite]
    nuovo_indice = {i: k for k, i in enumerate(restano)}
    J["images"] = [J["images"][i] for i in restano]
    for t in trame:
        t["source"] = nuovo_indice[sostituite.get(t["source"], t["source"])]
    B = _ricompatta(J, B, [(nuovo_indice[i], dati) for i, dati in nuove])
    zone = J["images"][nuovo_indice[fonti[0]]]["extras"]["pack3d_zone"]
    return scrivi(J, B), zone


def unisci_file(path, lato=LATO):
    """`unisci` su un file GLB, riscritto al suo posto. Torna le zone, o
    None se c'era gia' un'immagine sola."""
    with open(path, "rb") as fh:
        glb = fh.read()
    nuovo, zone = unisci(glb, lato)
    if zone is not None:
        with open(path, "wb") as fh:
            fh.write(nuovo)
    return zone
