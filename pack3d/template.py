"""Il template del modello: un PSD a livelli per chi disegna una variante.

In Glam Lab ogni modello ha «Scarica Template»: un PSD su cui il grafico
appoggia il nuovo artwork, e da cui esporta la texture da caricare sul
modello. Per i modelli costruiti dal PDF il template lo fa lo Space, dal GLB
che ha appena costruito, con la struttura del template ufficiale che Glam ha
gia' (quello del Nutella 750 g): due gruppi, dal basso.

**La tua grafica** - un livello solo, «La tua grafica», con la texture del
modello: lo steso del PDF (REGOLE.md, *La texture e' lo steso*), alla misura
di quella che va a Glam (`texture.per_glam`, al massimo 5000 px di lato). Ci
si sovrappone il nuovo artwork; esportato a questa misura e caricato come
texture del modello, ogni cosa torna al suo posto.

**Guide UV** - come nel template ufficiale, le prime tre bloccate del tutto:
si accendono e si spengono, ma non si dipingono per sbaglio:

- *Sovrapposizione modello* (nascosto): tutti gli spigoli della mappatura,
  grigi e sottili. Su un flowpack o una coppa sono migliaia;
- *Griglia texture* (nascosto): la scacchiera A0-J9 per provare il verso
  sul modello: esportata come texture, si legge dove va ogni cella;
- *Area non modificabile*: nero al 60% dove il modello non prende la
  texture, fuori dal DT e nelle finestre;
- *Contorni*: le linee della mappatura che contano per chi disegna. Il
  bordo di quello che il modello prende - il DT, una finestra, un solco -
  e le pieghe: gli spigoli fra due triangoli che nel modello stanno su
  piani diversi di piu' di `PIEGA` gradi - la cordonatura fra due pannelli,
  la pinna di un flowpack - se sono in una linea lunga (`LUNGA`): la
  zigrinatura della saldatura di un flowpack, fatta di pieghe corte che
  cambiano verso a ogni dente, non ci va. Gli spigoli fra triangoli dello
  stesso piano, la diagonale di un pannello, non ci sono. In magenta, come
  le fustelle, perche' si vedano sulla grafica;
- *Nomi delle facce*: FRONTE, RETRO, FIANCO SX... al centro di ogni faccia
  di un astuccio (`NOMI`), dove il GLB le chiama per nome; in verticale
  sulle facce alte e strette;
- *Nomi dei pezzi*: in un modello di piu' fogli - la coppa col tappo, il
  cono col lid, il riempimento - la texture e' un atlante coi loro stesi
  (`pack3d.atlante`), e ogni zona ha in alto a sinistra il nome del suo
  pezzo (`PEZZI`): COPPA, TAPPO, VASSOIO, FLOWPACK...

La composizione salvata nel file, quella che vede chi non legge i livelli,
e' quella dei livelli accesi.

Il template si fa solo se il modello ha una texture sola, come la texture
che va a Glam - e coi modelli di piu' fogli in atlante, ce l'hanno tutti:
Glam mette una texture su tutto il modello, e il template e' la tela di
quella texture. Le guide sono solo dei materiali che la usano:
l'interno, il taglio, il rovescio e la pellicola sono colori pieni, e la
texture di una variante non li tocca. Se il PSD supera `LIMITE`, si rifa'
piu' piccolo: le UV sono frazioni dell'immagine, e un template piu' piccolo
torna sul modello come quello grande.
"""
from __future__ import annotations

import io

import numpy as np

from . import texture as _texture

# gradi fra i piani di due triangoli oltre i quali lo spigolo comune e' una
# piega. Le cordonature di un astuccio sono a 90; la curva di un flowpack o di
# una coppa, divisa in tanti triangoli, ne fa pochi per spigolo.
PIEGA = 20.0
# una piega va nei contorni se sta in una linea lunga almeno questa parte del
# lato maggiore del template, e una linea e' una catena di pieghe che girano
# di meno di GIRO gradi da una all'altra
LUNGA = 0.03
GIRO = 20.0
# mm: due pannelli separati da meno di questo, nello steso, sono attaccati
# dalla loro piega. E' lo spessore del cartone, che nel display separa i
# pannelli di qualche decimo.
FESSURA = 1.5
CONTORNI = (236, 0, 140)
MAGLIA = (168, 168, 168)
SCRITTE = (63, 63, 63)
# l'opacita' dell'area non modificabile, come nel template ufficiale
VELO = 153
# byte: oltre, il template si rifa' piu' piccolo. Lo storage di Glam, di
# serie, non prende file oltre i 50 MB.
LIMITE = 45_000_000
MIME = "image/vnd.adobe.photoshop"
# le facce dell'astuccio, come le chiama `folding`: il fianco sinistro e'
# quello a sinistra guardando il fronte
# i pezzi di un atlante, come li chiama il GLB (`pack3d.atlante`)
PEZZI = {"coppa": "COPPA", "tappo": "TAPPO", "cono": "CONO", "lid": "LID",
         "vassoio": "VASSOIO", "display": "DISPLAY", "flowpack": "FLOWPACK",
         "packaging": "ASTUCCIO"}
NOMI = {"front": "FRONTE", "back": "RETRO", "left": "FIANCO SX",
        "right": "FIANCO DX", "top": "CIELO", "bottom": "FONDO",
        "back_top": "RETRO", "back_bottom": "RETRO"}

_TIPI = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
         5125: np.uint32, 5126: np.float32}
_COMPONENTI = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _accessorio(J, binario, i):
    """L'accessorio `i` del GLB come array (count, componenti)."""
    a = J["accessors"][i]
    bv = J["bufferViews"][a["bufferView"]]
    tipo = np.dtype(_TIPI[a["componentType"]])
    n = _COMPONENTI[a["type"]]
    passo = bv.get("byteStride") or tipo.itemsize * n
    inizio = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    grezzo = np.frombuffer(binario, np.uint8, count=passo * (a["count"] - 1)
                           + tipo.itemsize * n, offset=inizio)
    righe = np.lib.stride_tricks.as_strided(
        grezzo, (a["count"], tipo.itemsize * n), (passo, 1))
    x = np.ascontiguousarray(righe).view(tipo).reshape(a["count"], n)
    if a.get("normalized") and tipo.kind in "iu":
        x = x / float(np.iinfo(tipo).max)
    return x.astype(np.float64)


def triangoli(glb, sorgente):
    """`(P, UV, nomi)`: i triangoli del GLB che usano l'immagine `sorgente`
    come colore, coi vertici nel modello (n, 3, 3) e sulle UV (n, 3, 2), e
    per ognuno il nome del suo materiale."""
    J, binario = _texture._parti(glb)
    materiali = J.get("materials") or []
    P, UV, nomi = [], [], []
    for mesh in J.get("meshes") or []:
        for p in mesh.get("primitives") or []:
            if "material" not in p or p.get("mode", 4) != 4:
                continue
            m = materiali[p["material"]]
            t = (m.get("pbrMetallicRoughness") or {}).get("baseColorTexture")
            if t is None or J["textures"][t["index"]]["source"] != sorgente:
                continue
            uv = p["attributes"].get("TEXCOORD_%d" % t.get("texCoord", 0))
            if uv is None:
                continue
            V = _accessorio(J, binario, p["attributes"]["POSITION"])
            U = _accessorio(J, binario, uv)
            ix = (_accessorio(J, binario, p["indices"]).astype(np.int64).ravel()
                  if "indices" in p else np.arange(len(V)))
            ix = ix[:len(ix) // 3 * 3].reshape(-1, 3)
            P.append(V[ix])
            UV.append(U[ix])
            nomi += [m.get("name") or ""] * len(ix)
    if not P:
        return np.zeros((0, 3, 3)), np.zeros((0, 3, 2)), []
    return np.concatenate(P), np.concatenate(UV), nomi


def _vertici(punti, tolleranza):
    """Un numero per ogni punto (m, 2): uguale per i punti piu' vicini di
    `tolleranza`. Due facce vicine, fatte a parte - i pezzi di una plancia -
    hanno i capi comuni uguali a meno degli arrotondamenti, e devono
    risultare attaccate."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    unici, quale = np.unique(np.round(punti / tolleranza).astype(np.int64),
                             axis=0, return_inverse=True)
    quale = quale.ravel()
    centri = np.zeros((len(unici), 2))
    np.add.at(centri, quale, punti)
    centri /= np.bincount(quale, minlength=len(unici))[:, None]
    coppie = cKDTree(centri).query_pairs(2 * tolleranza, output_type="ndarray")
    n = len(unici)
    grafo = coo_matrix((np.ones(len(coppie)), (coppie[:, 0], coppie[:, 1])),
                       shape=(n, n)) if len(coppie) else coo_matrix((n, n))
    _k, gruppo = connected_components(grafo, directed=False)
    return gruppo[quale]


def _pieghe_a_t(capi, lati, normali, piega, fessura):
    """Le pieghe fra spigoli senza compagno (n, 2, 2, in pixel), ognuno col
    lato dove sta il suo triangolo (+1 o -1, rispetto al verso dello
    spigolo) e la normale del triangolo. Due spigoli quasi sulla stessa
    retta, coi triangoli da parti opposte, sono la stessa piega anche se i
    capi non coincidono - un pannello alto quanto due vicini - o se fra i due
    resta una `fessura` di pixel: lo spessore del cartone, che nello steso
    separa i pannelli di un display di qualche decimo di millimetro. Torna i
    tratti in comune (m, 2, 2), a meta' della fessura, dove i piani girano
    di piu' di `piega` gradi."""
    from scipy.spatial import cKDTree
    vuoto = np.zeros((0, 2, 2))
    if len(capi) < 2:
        return vuoto
    d = capi[:, 1] - capi[:, 0]
    d = d / np.linalg.norm(d, axis=1)[:, None]
    teta = np.arctan2(d[:, 1], d[:, 0]) % np.pi
    verso = np.stack([np.cos(teta), np.sin(teta)], 1)
    # il lato del triangolo, rispetto a `verso` invece che allo spigolo
    lati = lati * np.sign(np.einsum("ij,ij->i", d, verso))
    rho = capi[:, 0, 0] * verso[:, 1] - capi[:, 0, 1] * verso[:, 0]
    # la retta di uno spigolo: verso e distanza dall'origine. Mezzo grado di
    # verso pesa come la fessura; le rette quasi orizzontali stanno anche
    # dall'altra parte di pi greco, col verso e la distanza rovesciati.
    tol = np.radians(0.5)
    K = max(fessura, 0.5) / tol
    chi = np.arange(len(capi))
    giro = teta > np.pi - 2 * tol
    punti = np.concatenate([np.stack([teta * K, rho], 1),
                            np.stack([(teta[giro] - np.pi) * K, -rho[giro]], 1)])
    rov = np.concatenate([np.ones(len(capi)), -np.ones(giro.sum())])
    chi = np.concatenate([chi, chi[giro]])
    coppie = cKDTree(punti).query_pairs(1.5 * max(fessura, 0.5), output_type="ndarray")
    if not len(coppie):
        return vuoto
    i, j = coppie[:, 0], coppie[:, 1]
    a, b = chi[i], chi[j]
    # i due nel verso di `a`: se uno dei due e' la copia girata, b si rovescia
    s = rov[i] * rov[j]
    drho = np.abs(rho[a] - s * rho[b])
    dteta = np.abs(punti[i, 0] - punti[j, 0]) / K
    buoni = (a != b) & (dteta < tol) & (drho <= max(fessura, 0.5)) \
        & (lati[a] == -s * lati[b]) \
        & (np.einsum("ij,ij->i", normali[a], normali[b]) < np.cos(np.radians(piega)))
    a, b, s = a[buoni], b[buoni], s[buoni]
    if not len(a):
        return vuoto
    # il tratto in comune, lungo il verso di a, a meta' fra le due rette
    v = verso[a]
    ta = np.sort(np.einsum("nkj,nj->nk", capi[a], v), axis=1)
    tb = np.sort(np.einsum("nkj,nj->nk", capi[b], v), axis=1)
    t0 = np.maximum(ta[:, 0], tb[:, 0])
    t1 = np.minimum(ta[:, 1], tb[:, 1])
    buoni = t1 - t0 > 0.5
    v, t0, t1 = v[buoni], t0[buoni], t1[buoni]
    r = (rho[a] + s * rho[b])[buoni] / 2
    # il punto della retta piu' vicino all'origine: distanza r, sulla normale
    base = np.stack([r * v[:, 1], -r * v[:, 0]], 1)
    return np.stack([base + t0[:, None] * v, base + t1[:, None] * v], 1)


def _lunghe(capi, ids, lunghezza):
    """Delle pieghe `capi` (n, 2, 2, in pixel) coi capi `ids` (n, 2), quelle
    che stanno in una linea lunga almeno `lunghezza`: una linea e' una
    catena di pieghe che proseguono una nell'altra, girando di meno di
    `GIRO` gradi. Restano le cordonature e le pinne; la zigrinatura di una
    saldatura - pieghe di un paio di millimetri che cambiano verso a ogni
    dente - no."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    if not len(capi):
        return np.zeros(0, bool)
    d = capi[:, 1] - capi[:, 0]
    lun = np.linalg.norm(d, axis=1)
    d = d / np.maximum(lun, 1e-12)[:, None]
    # per ogni vertice le pieghe che ci arrivano, e il verso con cui escono
    vert = np.concatenate([ids[:, 0], ids[:, 1]])
    piega = np.concatenate([np.arange(len(capi))] * 2)
    verso = np.concatenate([d, -d])
    ordine = np.argsort(vert, kind="stable")
    vert, piega, verso = vert[ordine], piega[ordine], verso[ordine]
    a, b = [], []
    inizi = np.flatnonzero(np.r_[True, vert[1:] != vert[:-1]])
    fini = np.r_[inizi[1:], len(vert)]
    soglia = -np.cos(np.radians(GIRO))
    for i, j in zip(inizi, fini):
        if j - i < 2:
            continue
        V = verso[i:j]
        c = V @ V.T
        x, y = np.nonzero(np.triu(c < soglia, 1))
        a += piega[i:j][x].tolist()
        b += piega[i:j][y].tolist()
    n = len(capi)
    grafo = coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n))
    _k, linea = connected_components(grafo, directed=False)
    totale = np.bincount(linea, weights=lun)
    return totale[linea] >= lunghezza


def spigoli(P, UV, misura, piega=PIEGA):
    """`(pieghe, tutti)`: gli spigoli sulle UV, come array (n, 2, 2), su una
    tela di `misura` (l, a) pixel. `tutti` sono quelli di tutti i triangoli,
    una volta sola; `pieghe` quelli fra due triangoli su piani diversi di
    piu' di `piega` gradi, che stanno in una linea lunga (vedi il modulo).
    I bordi non si prendono da qui (`_bordo`)."""
    vuoto = np.zeros((0, 2, 2))
    if not len(P):
        return vuoto, vuoto
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    lun = np.linalg.norm(n, axis=1)
    scala = np.array(misura, float)
    area_px = np.abs(np.cross((UV[:, 1] - UV[:, 0]) * scala,
                              (UV[:, 2] - UV[:, 0]) * scala))
    buoni = (lun > 1e-12) & (area_px > 1e-6)
    P, UV, n = P[buoni], UV[buoni], n[buoni] / lun[buoni, None]
    if not len(P):
        return vuoto, vuoto
    # i tre spigoli di ogni triangolo, coi capi in ordine: due triangoli
    # vicini sulle UV hanno gli stessi capi, anche quando nel GLB sono
    # vertici diversi (le facce di un astuccio, i pezzi di una plancia)
    ids = _vertici((UV * scala).reshape(-1, 2), 0.05).reshape(-1, 3)
    capi = np.stack([UV[:, [0, 1]], UV[:, [1, 2]], UV[:, [2, 0]]], 1).reshape(-1, 2, 2)
    terzo = UV[:, [2, 0, 1]].reshape(-1, 2)
    e = np.stack([ids[:, [0, 1]], ids[:, [1, 2]], ids[:, [2, 0]]], 1).reshape(-1, 2)
    scambia = e[:, 0] > e[:, 1]
    e[scambia] = e[scambia][:, ::-1]
    capi[scambia] = capi[scambia][:, ::-1]
    # da che parte dello spigolo sta il suo triangolo
    dd = (capi[:, 1] - capi[:, 0]) * scala
    lati = np.sign(dd[:, 0] * ((terzo - capi[:, 0]) * scala)[:, 1]
                   - dd[:, 1] * ((terzo - capi[:, 0]) * scala)[:, 0])
    lungo = e[:, 0] != e[:, 1]
    _u, primo, quale, quanti = np.unique(e, axis=0, return_index=True,
                                         return_inverse=True, return_counts=True)
    quale = quale.ravel()
    normale = np.repeat(n, 3, axis=0)
    # per ogni spigolo, il coseno piu' piccolo fra la normale del primo
    # triangolo che lo usa e quelle degli altri
    coseno = np.ones(len(primo))
    np.minimum.at(coseno, quale, np.einsum("ij,ij->i", normale,
                                           normale[primo[quale]]))
    tieni = lungo[primo]
    piegato = (quanti > 1) & (coseno < np.cos(np.radians(piega))) & tieni
    soli = (quanti == 1) & tieni
    # le pieghe fra triangoli coi capi in comune, e quelle a T
    # i pixel per millimetro della texture: lo steso e' a scala uniforme, e
    # il rapporto fra le aree lo dice (le posizioni del GLB sono in metri)
    area3d = lun[buoni] / 2 * 1e6
    px_mm = float(np.sqrt(np.median(area_px[buoni] / 2 / np.maximum(area3d, 1e-12))))
    tratti = np.concatenate([capi[primo[piegato]] * scala,
                             _pieghe_a_t(capi[primo[soli]] * scala, lati[primo[soli]],
                                         normale[primo[soli]], piega,
                                         FESSURA * px_mm)])
    if not len(tratti):
        return np.zeros((0, 2, 2)), capi[primo[tieni]]
    ids = _vertici(tratti.reshape(-1, 2), 0.5).reshape(-1, 2)
    lunghe = _lunghe(tratti, ids, LUNGA * max(misura))
    return tratti[lunghe] / scala, capi[primo[tieni]]


def _tratti(misura, linee, spessore, alfa=None):
    """Le `linee` (n, 2, 2) in UV disegnate su una maschera `L` della
    `misura` (l, a), o su `alfa` se c'e'."""
    from PIL import Image, ImageDraw
    alfa = alfa or Image.new("L", misura, 0)
    d = ImageDraw.Draw(alfa)
    for a, b in linee * np.array(misura, float):
        d.line([tuple(a), tuple(b)], fill=255, width=spessore)
    return alfa


def _livello(alfa, colore):
    """Un livello di colore pieno, disegnato dalla trasparenza `alfa`: i tre
    canali del colore, tutti uguali, nel PSD non pesano."""
    from PIL import Image
    im = Image.new("RGBA", alfa.size, colore + (255,))
    im.putalpha(alfa)
    return im


def _dentro(misura, UV):
    """La maschera di dove il modello prende la texture: i triangoli pieni,
    col loro contorno, perche' nessuna scheggia della triangolazione resti
    fuori."""
    from PIL import Image, ImageDraw
    dentro = Image.new("L", misura, 0)
    d = ImageDraw.Draw(dentro)
    for t in UV * np.array(misura, float):
        d.polygon([tuple(v) for v in t], fill=255, outline=255)
    return dentro


def _bordo(dentro, spessore):
    """Il bordo di quello che il modello prende - il DT, le finestre, i
    solchi - spesso `spessore` pixel e tutto dentro. Si prende dalla
    maschera e non dagli spigoli: una triangolazione con le giunte a T
    (la plancia di un display, dal bordo ondulato) ha spigoli di un
    triangolo solo anche in mezzo a una faccia."""
    from PIL import ImageChops, ImageFilter
    lato = 2 * spessore + 1
    return ImageChops.subtract(dentro, dentro.filter(ImageFilter.MinFilter(lato)))


def _font(corpo):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=max(8, int(corpo)))
    except (TypeError, OSError):
        return ImageFont.load_default()


def _griglia(misura):
    """La scacchiera A0-J9: dieci colonne di colore dal rosa al viola, ogni
    riga un po' piu' scura, e il nome della cella in bianco. Colori pieni:
    nel PSD pesa poco."""
    import colorsys
    from PIL import Image, ImageDraw
    w, h = misura
    im = Image.new("RGBA", misura, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = _font(min(w, h) / 10 * 0.4)
    for i in range(10):
        for j in range(10):
            x0, x1 = round(i * w / 10), round((i + 1) * w / 10)
            y0, y1 = round(j * h / 10), round((j + 1) * h / 10)
            r, g, b = colorsys.hls_to_rgb(0.92 - 0.2 * i / 9, 0.62 - 0.22 * j / 9, 0.45)
            d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(round(r * 255), round(g * 255),
                                                       round(b * 255), 200))
            d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 255, 255, 200),
                        width=max(1, round(min(w, h) / 1000)))
            d.text(((x0 + x1) / 2, (y0 + y1) / 2), "ABCDEFGHIJ"[i] + str(j),
                   fill=(255, 255, 255, 230), font=f, anchor="mm")
    return im


def _nomi(misura, UV, nomi):
    """I nomi delle facce dell'astuccio, al baricentro delle loro UV; None
    se il modello non ha facce coi nomi di `NOMI`. Il corpo e' quello che
    sta in meta' della faccia, al massimo un quarantesimo del lato del
    template; su una faccia alta e stretta il nome va in verticale."""
    from PIL import Image, ImageDraw
    w, h = misura
    nomi = np.asarray(nomi, object)
    im = Image.new("RGBA", misura, (0, 0, 0, 0))
    scritte = 0
    for nome in sorted(set(nomi.tolist()) & set(NOMI)):
        T = UV[nomi == nome] * np.array(misura, float)
        area = np.abs(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])) / 2
        if area.sum() < 1:
            continue
        c = (T.mean(1) * area[:, None]).sum(0) / area.sum()
        larga, alta = np.ptp(T[..., 0]), np.ptp(T[..., 1])
        testo = NOMI[nome]
        # il corpo per cui il nome sta in meta' della faccia, in orizzontale
        # e in verticale: si sceglie il verso dove viene piu' grande
        prova = _font(100)
        x0, y0, x1, y1 = prova.getbbox(testo)
        rw, rh = (x1 - x0) / 100.0, (y1 - y0) / 100.0
        dritto = min(0.5 * larga / rw, 0.5 * alta / rh)
        girato = min(0.5 * alta / rw, 0.5 * larga / rh)
        corpo = min(max(dritto, girato), max(w, h) / 40)
        if corpo < 10:
            continue
        f = _font(corpo)
        bordo = max(1, round(corpo / 12))
        x0, y0, x1, y1 = f.getbbox(testo, stroke_width=bordo)
        pezzo = Image.new("RGBA", (x1 - x0 + 2, y1 - y0 + 2), (0, 0, 0, 0))
        ImageDraw.Draw(pezzo).text((1 - x0, 1 - y0), testo, fill=SCRITTE + (255,),
                                   font=f, stroke_width=bordo,
                                   stroke_fill=(255, 255, 255, 255))
        if girato > dritto:
            pezzo = pezzo.rotate(90, expand=True)
        im.alpha_composite(pezzo, (int(round(c[0] - pezzo.width / 2)),
                                   int(round(c[1] - pezzo.height / 2))))
        scritte += 1
    return im if scritte else None


def _pezzi(misura, zone):
    """I nomi dei pezzi di un atlante, in alto a sinistra di ogni zona; None
    se la texture non e' un atlante."""
    from PIL import Image, ImageDraw
    if not zone:
        return None
    w, h = misura
    im = Image.new("RGBA", misura, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for z in zone:
        zx, zy, zw, zh = z["x"] * w, z["y"] * h, z["w"] * w, z["h"] * h
        f = _font(min(min(zw, zh) / 8, max(w, h) / 30))
        bordo = max(1, round(f.size / 10))
        d.text((zx + f.size * 0.4, zy + f.size * 0.3),
               PEZZI.get(z.get("nome"), str(z.get("nome") or "").upper()),
               fill=SCRITTE + (255,), font=f, stroke_width=bordo,
               stroke_fill=(255, 255, 255, 255))
    return im


def _psd(tela, P, UV, nomi, zone=()):
    """`(byte del PSD, pieghe, spigoli)` sulla `tela` (la texture, RGB)."""
    from psd_tools import PSDImage
    from psd_tools.constants import ProtectedFlags, Tag
    from psd_tools.psd.tagged_blocks import ProtectedSetting
    from PIL import ImageChops
    misura = tela.size
    pieghe, tutti = spigoli(P, UV, misura)
    spessore = max(2, round(max(misura) / 1600))
    maglia = _livello(_tratti(misura, tutti, 1), MAGLIA)
    griglia = _griglia(misura)
    dentro = _dentro(misura, UV)
    fuori = _livello(ImageChops.invert(dentro), (0, 0, 0))
    # il bordo ha lo spessore delle pieghe: meta' di qua e meta' di la' di
    # una linea, e il bordo tutto dentro, si vedono uguali
    linee = _livello(_tratti(misura, pieghe, spessore,
                             _bordo(dentro, max(1, spessore // 2 + 1))), CONTORNI)
    scritte = _nomi(misura, UV, nomi)
    nomi_pezzi = _pezzi(misura, zone)
    # la composizione dei livelli accesi
    composizione = tela.convert("RGBA")
    velo = fuori.copy()
    velo.putalpha(fuori.getchannel("A").point(lambda a: a * VELO // 255))
    for sopra in (velo, linee, scritte, nomi_pezzi):
        if sopra is not None:
            composizione.alpha_composite(sopra)
    # Il documento nasce RGBA perche' psd-tools tenga la trasparenza dei
    # livelli come trasparenza: in un documento RGB la farebbe maschera di
    # livello, e il grafico si troverebbe le linee su un fondo nero
    # mascherato. Poi torna RGB a tre canali, com'e' un file di Photoshop
    # senza canali alfa: la composizione e' opaca.
    psd = PSDImage.frompil(composizione)
    grafica = psd.create_group(name="La tua grafica")
    grafica.create_pixel_layer(tela, name="La tua grafica")
    guide = psd.create_group(name="Guide UV")
    for im, nome, acceso, opaco, chiuso in (
            (maglia, "Sovrapposizione modello", False, 255, True),
            (griglia, "Griglia texture", False, 255, True),
            (fuori, "Area non modificabile", True, VELO, True),
            (linee, "Contorni", True, 255, False),
            (scritte, "Nomi delle facce", True, 255, False),
            (nomi_pezzi, "Nomi dei pezzi", True, 255, False)):
        if im is None:
            continue
        livello = guide.create_pixel_layer(im, name=nome, opacity=opaco)
        livello.visible = acceso
        if chiuso:
            # `livello.lock()` di psd-tools 1.24 cambia una copia, e nel
            # file il blocco resta a zero
            livello.tagged_blocks.set_data(
                Tag.PROTECTED_SETTING, ProtectedSetting(int(ProtectedFlags.COMPLETE)))
    testa = psd._record.header
    testa.channels = 3
    psd._record.image_data.set_data(
        [c.tobytes() for c in composizione.convert("RGB").split()], testa)
    # la composizione e' gia' quella giusta: psd-tools la rifarebbe dai
    # livelli, e su una texture da 5000 px ci mette venti secondi
    psd._updated = False
    bio = io.BytesIO()
    psd.save(bio)
    return bio.getvalue(), len(pieghe), len(tutti)


def template(glb, lato_max=_texture.LATO_GLAM):
    """Il template PSD del modello: `{"dati", "lato", "pieghe", "spigoli"}`,
    o None se il modello non ha una texture sola."""
    from PIL import Image
    t = _texture.per_glam(glb, lato_max)
    if t is None:
        return None
    tela = Image.open(io.BytesIO(t["dati"])).convert("RGB")
    P, UV, nomi = triangoli(glb, t["sorgente"])
    while True:
        dati, n_pieghe, n_tutti = _psd(tela, P, UV, nomi, t["zone"])
        if len(dati) <= LIMITE or max(tela.size) <= 1024:
            break
        r = 0.8 * (LIMITE / len(dati)) ** 0.5
        tela = tela.resize((max(1, round(tela.width * r)),
                            max(1, round(tela.height * r))), Image.LANCZOS)
    return {"dati": dati, "lato": tela.size, "pieghe": n_pieghe,
            "spigoli": n_tutti}


def nome_file(base):
    """Il nome del file del template di un modello che si chiama `base`."""
    return "%s_template.psd" % base
