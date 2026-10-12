"""La texture del modello e' lo steso del PDF.

Lo steso pulito - la grafica senza disegno tecnico, quote, legende, aree
riservate - nel verso in cui sta nel PDF, inquadrato sul DT, e le UV del
modello che puntano li'. Chi vuole una variante prende la texture, ci
sovrappone il nuovo artwork - stesso DT, stesso verso, stessa scala - e la
rimette sul modello: ogni cosa torna al suo posto. Vedi REGOLE.md, *La
texture e' lo steso*.

Le famiglie costruiscono la loro texture nel telaio in cui lavorano: il foglio
girato sul verso della grafica (`artwork.pagina_girata`), il film coricato,
con sotto le strisce delle tinte dell'interno e del taglio. Qui si riporta
tutto allo steso, alla fine, senza toccare la costruzione:

- `nel_verso_del_pdf`: la texture girata indietro dei gradi del foglio, e le
  UV con lei;
- `ritaglia`: la texture ridotta al riquadro del DT;
- `senza_strisce`: le strisce delle tinte tolte dalla texture, e i triangoli
  che le usavano col loro colore pieno, un materiale senza texture (`Tinte`).

Le UV sono glTF: u verso destra, v verso il basso, origine in alto a
sinistra.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

# Le trasposizioni di PIL come trasformazioni delle UV: `(u, v) -> M @ (u,
# v, 1)` porta il punto di un'immagine nella stessa immagine trasposta.
# ROTATE_90 gira in senso antiorario.
_MATRICI = {
    None: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    Image.ROTATE_90: ((0.0, 1.0, 0.0), (-1.0, 0.0, 1.0)),
    Image.ROTATE_180: ((-1.0, 0.0, 1.0), (0.0, -1.0, 1.0)),
    Image.ROTATE_270: ((0.0, -1.0, 1.0), (1.0, 0.0, 0.0)),
}
INVERSA = {None: None, Image.ROTATE_90: Image.ROTATE_270,
           Image.ROTATE_180: Image.ROTATE_180, Image.ROTATE_270: Image.ROTATE_90}

# Il foglio di lavoro e' la pagina del PDF girata di `gradi` in senso orario
# (`artwork.pagina_girata`): per tornare al verso del PDF si gira la texture
# degli stessi gradi in senso antiorario.
INDIETRO = {0: None, 90: Image.ROTATE_90, 180: Image.ROTATE_180,
            270: Image.ROTATE_270}


def matrice(op):
    """La trasformazione affine (2 x 3) delle UV per la trasposizione `op`."""
    return np.array(_MATRICI[op], float)


def componi(*M):
    """Le affini (2 x 3) una dopo l'altra: prima la prima."""
    tot = np.eye(3)
    for m in M:
        tot = np.vstack([m, (0.0, 0.0, 1.0)]) @ tot
    return tot[:2]


def applica(M, UV):
    """Le UV `(n, 2)` trasformate dall'affine `M`."""
    UV = np.asarray(UV, float)
    return (UV @ M[:, :2].T + M[:, 2]).astype(np.float32)


def gira(im, op):
    """L'immagine (PIL) trasposta, o None se e' None."""
    if im is None or op is None:
        return im
    return im.transpose(op)


def nel_verso_del_pdf(gradi, tela, UV, *mappe):
    """`(tela, UV, *mappe)` riportate dal foglio di lavoro, girato di `gradi`
    in senso orario, al verso del PDF. Le `mappe` (metallo e ruvidita') sono
    immagini nello stesso telaio della tela. Una mappa delle normali NON si
    gira cosi': i suoi vettori stanno nel telaio dell'immagine, e si rifa'
    dall'altezza girata (`rilievo`)."""
    op = INDIETRO[int(gradi) % 360]
    if op is None:
        return (tela, np.asarray(UV, np.float32)) + tuple(mappe)
    return ((gira(tela, op), applica(matrice(op), UV))
            + tuple(gira(m, op) for m in mappe))


def ritaglia(box, tela, UV, *mappe):
    """La tela ridotta al riquadro `box` (pixel, x0 y0 x1 y1), le UV con lei.
    Le mappe, se ci sono, hanno la misura della tela."""
    x0, y0, x1, y1 = (int(round(c)) for c in box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(tela.width, x1), min(tela.height, y1)
    W, H = tela.size
    w, h = x1 - x0, y1 - y0
    UV = np.asarray(UV, float)
    nuove = np.stack([(UV[:, 0] * W - x0) / w, (UV[:, 1] * H - y0) / h], 1)
    out = (tela.crop((x0, y0, x1, y1)), nuove.astype(np.float32))
    return out + tuple(None if m is None else
                       (m if m.size == tela.size else m.resize(tela.size))
                       .crop((x0, y0, x1, y1)) for m in mappe)


def lineare(rgb):
    """Un colore sRGB (0-255) nei valori lineari di glTF (`baseColorFactor`)."""
    c = np.asarray(rgb, float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return [round(float(x), 5) for x in lin]


@dataclass
class Tinte:
    """I triangoli col colore pieno: `quale[t]` e' l'indice in `colori` del
    triangolo t, -1 se prende la texture. `colori` sono `(nome, (r, g, b))`,
    in sRGB."""
    quale: np.ndarray
    colori: list = field(default_factory=list)

    def indice(self, nome, rgb):
        for i, (n, c) in enumerate(self.colori):
            if tuple(c) == tuple(rgb):
                return i
        self.colori.append((nome, tuple(int(x) for x in rgb)))
        return len(self.colori) - 1


def senza_strisce(alto, tela, UV, T, nomi, *mappe):
    """Le strisce delle tinte, sotto le prime `alto` righe della tela, tolte.
    I triangoli che pescavano li' (il baricentro delle UV sotto `alto`)
    prendono il colore della striscia come tinta piena; `nomi` e'
    `{(r, g, b): nome}` per chiamare i materiali. Torna `(tela, UV, Tinte,
    *mappe)`: la tela alta `alto`, le UV sulla tela nuova."""
    W, H = tela.size
    UV = np.asarray(UV, float)
    T = np.asarray(T).reshape(-1, 3)
    a = np.asarray(tela.convert("RGB"))
    v_alto = alto / float(H)
    cv = UV[T, 1].mean(1)
    tinte = Tinte(np.full(len(T), -1, np.int32))
    sotto = np.nonzero(cv >= v_alto)[0]
    for t in sotto:
        cu = UV[T[t], 0].mean()
        x = min(W - 1, max(0, int(cu * W)))
        y = min(H - 1, max(alto, int(cv[t] * H)))
        rgb = tuple(int(c) for c in a[y, x])
        tinte.quale[t] = tinte.indice(nomi.get(rgb, "tinta"), rgb)
    nuove = UV.copy()
    nuove[:, 1] = np.clip(UV[:, 1] / v_alto, 0.0, 1.0)
    return ((tela.crop((0, 0, W, alto)), nuove.astype(np.float32), tinte)
            + tuple(None if m is None else
                    (m if m.size == tela.size else m.resize(tela.size))
                    .crop((0, 0, W, alto)) for m in mappe))


def uniforme(im):
    """Il colore (r, g, b) di un'immagine tutta di un colore, o None."""
    e = im.convert("RGB").getextrema()
    if all(lo == hi for lo, hi in e):
        return tuple(lo for lo, _hi in e)
    return None


# --------------------------------------------------------------------------- #
# l'astuccio: le facce sullo steso
# --------------------------------------------------------------------------- #
def facce_sullo_steso(faces, panels, girate, scala, box, gradi):
    """A ogni faccia stampata dell'astuccio, `f["telaio"]`: l'affine dalle UV
    della sua immagine alle UV dello steso girato nel verso del PDF.

    L'immagine di una faccia e' il riquadro del suo pannello ritagliato dal
    foglio (`folding.rasterize_panels`, coi pixel arrotondati), girato di
    `girate[nome]` (`artwork.gira_sulla_grafica`); lo steso e' il riquadro
    `box` (pixel) dello stesso foglio, e il foglio di lavoro e' il PDF girato
    di `gradi` in senso orario. Le facce di colore pieno non ne hanno
    bisogno. Torna la trasposizione che riporta lo steso nel verso del PDF."""
    from .artwork import GIRO_TEXTURE
    sx0, sy0, sx1, sy1 = box
    W, H = float(sx1 - sx0), float(sy1 - sy0)
    op = INDIETRO[int(gradi) % 360]
    indietro = matrice(op)
    for f in faces:
        p = panels.get(f["name"])
        if p is None or uniforme(f["tex"]) is not None:
            continue
        bx0, by0, bx1, by1 = (round(c * scala) for c in (p.x0, p.y0, p.x1, p.y1))
        g = (girate or {}).get(f["name"])
        sul_ritaglio = matrice(INVERSA[GIRO_TEXTURE[g]] if g else None)
        sullo_steso = np.array([[(bx1 - bx0) / W, 0.0, (bx0 - sx0) / W],
                                [0.0, (by1 - by0) / H, (by0 - sy0) / H]])
        f["telaio"] = componi(sul_ritaglio, sullo_steso, indietro)
    return op


def riscontro(faces, tela, punti=400, tolleranza=0.9):
    """Le facce la cui immagine NON torna con lo steso nel loro telaio: per
    ognuna si confrontano `punti` pixel presi a caso lontano dai bordi, e
    devono essere uguali (a meno di 6 livelli) almeno in `tolleranza`.
    Lista vuota se tornano tutte."""
    A = np.asarray(tela.convert("RGB"), np.int16)
    H, W = A.shape[:2]
    rng = np.random.default_rng(0)
    no = []
    for f in faces:
        if f.get("telaio") is None:
            continue
        a = np.asarray(f["tex"].convert("RGB"), np.int16)
        h, w = a.shape[:2]
        if h < 8 or w < 8:
            continue
        uv = rng.uniform(0.1, 0.9, (punti, 2))
        x, y = (uv[:, 0] * w).astype(int), (uv[:, 1] * h).astype(int)
        uv = np.stack([(x + 0.5) / w, (y + 0.5) / h], 1)
        s = applica(f["telaio"], uv)
        X = np.clip((s[:, 0] * W).astype(int), 0, W - 1)
        Y = np.clip((s[:, 1] * H).astype(int), 0, H - 1)
        uguali = (np.abs(a[y, x] - A[Y, X]).max(1) <= 6).mean()
        if uguali < tolleranza:
            no.append((f["name"], float(uguali)))
    return no
