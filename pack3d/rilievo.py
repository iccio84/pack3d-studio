"""
Il rilievo: l'embossing - o il debossing - che il DT dichiara su una lastra sua.

Un rilievo non e' un inchiostro. E' il cartoncino spinto in fuori (embossing)
o in dentro (debossing) da una matrice a secco, quasi sempre a registro con
la grafica: sul ballotin Raffaello Passion Fruit sono i sei marchi
"Raffaello" e le due coppe delle praline. Il file lo dice con una tinta
piatta che si chiama come la lavorazione - `Embossing`, e un livello con lo
stesso nome - e quella lastra sulla texture non c'e': e' fra i Processing
Steps della norma (`techink.ISO_TYPES`), e la pulizia la toglie come ogni
lastra tecnica.

Sul modello il rilievo si fa con la luce: una mappa delle normali (la
`normalTexture` di glTF) nel telaio della texture, che lungo le spalle del
rilievo piega la normale come la piega la carta. La maglia resta quella: tre
decimi di rilievo su una scatola di dieci centimetri non cambiano la sagoma,
cambiano come la luce scivola sul marchio. E la mappa la leggono tutti i
viewer, senza estensioni.

La forma viene dalla lastra: dove l'inchiostro e' pieno il cartoncino sta
`ALTEZZA` mm sopra il piano (sotto, per un debossing), e la spalla e'
morbida, una gaussiana larga `SPALLA` mm - una matrice a secco non fa
spigoli vivi. Dall'altezza, la normale: (-dh/dx, +dh/dy, 1) col +Y in alto
nell'immagine, come vuole glTF.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile

import numpy as np
from PIL import Image

from . import techink

# Come si chiama la lastra di un rilievo, e da che parte va. "Embossing" e
# "Debossing" sono i nomi dei Processing Steps; gli altri quelli che si
# trovano nei file: rilievo, goffratura, Pragung, gaufrage, relieve. Il
# debossing si guarda prima: "Tiefpragung" e' un incavo anche se dice pragung.
_INCAVO = re.compile(r"deboss|incav|tiefpr")
_RILIEVO = re.compile(r"emboss|rilievo|goffr|pr(ae|a|\u00e4)g|gaufr|relieve|relief")

# mm: quanto sale il rilievo, e quanto e' larga la sua spalla (la sigma della
# gaussiana). Un embossing su cartoncino da astucci sta fra tre e sei decimi.
# Provati sul ballotin Raffaello in model-viewer, accanto allo stesso modello
# senza mappa: con 0,35 e 0,25 il marchio in rilievo quasi non si distingueva
# da quello piatto; con 0,5 e 0,2 le lettere hanno il bordo alto in luce e
# quello basso in ombra, e si leggono in rilievo senza sembrare scolpite.
ALTEZZA = 0.5
SPALLA = 0.2
# La lastra si legge a questa risoluzione, e la mappa delle normali ce l'ha
# uguale: sei pixel per mm bastano a una spalla di mezzo millimetro, e
# Ghostscript sul foglio del ballotin ci mette tre secondi invece di undici.
# Con la texture piu' rada (qualita' web) si scende alla sua.
DPI = 150.0
# quota d'inchiostro sotto la quale la lastra non c'e', come in `techink`
PIENO = 0.25


def segno(nome):
    """+1 se la lastra e' un rilievo, -1 se e' un incavo, 0 se non e' nessuno
    dei due."""
    n = techink._norm(nome)
    if _INCAVO.search(n):
        return -1
    if _RILIEVO.search(n):
        return 1
    return 0


def lastre(pdf, page_no=0):
    """`{lastra: segno}` delle lastre di rilievo della pagina: vuoto se non ce
    n'e'. Costa la lettura delle risorse della pagina, non una resa."""
    import pypdf
    try:
        pagina = pypdf.PdfReader(pdf).pages[page_no]
        nomi = set(techink.technical_separations(
            pagina, prova=lambda n: segno(n) != 0).values())
    except Exception:                                   # noqa: BLE001
        return {}
    return {n: segno(n) for n in sorted(nomi)}


def _ritaglio(pdf, page_no, riquadro, uscita):
    from .materiali import _ritaglio as ritaglia
    return ritaglia(pdf, page_no, riquadro, uscita)


def altezze(pdf, quali, riquadro, misura, page_no=0, dpi=DPI):
    """L'altezza del rilievo in mm, HxW float32, sul `riquadro` del foglio
    (punti, telaio di misura, y in giu') portato a `misura` (larghezza,
    altezza) in pixel. None se la lastra non si legge."""
    cartella = tempfile.mkdtemp(prefix="rilievo_")
    try:
        r = _ritaglio(pdf, page_no, riquadro, os.path.join(cartella, "r.pdf"))
        solo = next(iter(quali)) if len(quali) == 1 else None
        mappe = techink.mappe_lastre(r, 0, dpi, solo=solo)
    finally:
        shutil.rmtree(cartella, ignore_errors=True)
    h = None
    for nome, verso in quali.items():
        m = mappe.get(techink._norm(nome))
        if m is None:
            continue
        ink = (255.0 - m.astype(np.float32)) / 255.0
        ink[ink < PIENO * 0.5] = 0.0
        im = Image.fromarray((ink * (verso * ALTEZZA)).astype(np.float32))
        a = np.asarray(im.resize(tuple(misura), Image.BILINEAR), np.float32)
        h = a if h is None else h + a
    return h


def normali(h, px_mm):
    """La mappa delle normali di glTF da un'altezza in mm, `px_mm` pixel per
    mm: RGB lineare, piano = (128, 128, 255). La spalla si ammorbidisce qui."""
    from scipy.ndimage import gaussian_filter
    h = gaussian_filter(np.asarray(h, np.float32), SPALLA * px_mm)
    dy, dx = np.gradient(h, 1.0 / px_mm)
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(np.round((n * 0.5 + 0.5) * 255.0).astype(np.uint8))


def _riga(quali, h):
    """La riga per chi guarda il modello: quanto della grafica e' in rilievo,
    e di quanto."""
    quota = float((np.abs(h) >= PIENO * ALTEZZA).mean()) if h.size else 0.0
    su = [n for n, v in quali.items() if v > 0]
    giu = [n for n, v in quali.items() if v < 0]
    parti = []
    if su:
        parti.append("in rilievo di %.2f mm (%s)" % (ALTEZZA, ", ".join(su)))
    if giu:
        parti.append("in incavo di %.2f mm (%s)" % (ALTEZZA, ", ".join(giu)))
    return ("rilievo dal DT: il %.1f%% della grafica %s, con la spalla "
            "morbida; sul modello e' una mappa delle normali, la sagoma resta "
            "quella" % (100.0 * quota, " e ".join(parti)))


def _non_si_legge(quali):
    return ("rilievo: il file ha la lastra %s ma non si legge, il modello esce "
            "senza" % ", ".join(sorted(quali)))


def sulle_facce(pdf, panels, faces, girate=None, page_no=0, dpi=DPI):
    """Il rilievo sulle facce di un astuccio: a ogni faccia esterna che ne ha,
    la sua mappa delle normali in `f["normale"]`. La riga per chi guarda, o
    None se il file non ha lastre di rilievo.

    La mappa di una faccia e' fatta come la sua texture (`folding.
    rasterize_panels` e `artwork.gira_sulla_grafica`): il riquadro del suo
    pannello, girato degli stessi gradi (`girate`). La normale si calcola
    dopo il giro, sull'altezza gia' girata: girare una mappa delle normali
    vorrebbe dire girarne anche i vettori."""
    from .artwork import GIRO_TEXTURE
    quali = lastre(pdf, page_no)
    if not quali:
        return None
    nomi = sorted({f["name"] for f in faces if f["name"] in panels})
    if not nomi:
        return None
    x0 = min(panels[n].x0 for n in nomi)
    y0 = min(panels[n].y0 for n in nomi)
    x1 = max(panels[n].x1 for n in nomi)
    y1 = max(panels[n].y1 for n in nomi)
    s = dpi / 72.0
    W, H = max(1, int(round((x1 - x0) * s))), max(1, int(round((y1 - y0) * s)))
    try:
        h = altezze(pdf, quali, (x0, y0, x0 + W / s, y0 + H / s), (W, H),
                    page_no, dpi=dpi)
    except Exception:                                   # noqa: BLE001
        h = None
    if h is None or not np.any(h):
        return _non_si_legge(quali)
    px_mm = dpi / 25.4
    mappe = {}
    for n in nomi:
        p = panels[n]
        a = h[int(round((p.y0 - y0) * s)):int(round((p.y1 - y0) * s)),
              int(round((p.x0 - x0) * s)):int(round((p.x1 - x0) * s))]
        if not a.size or not np.any(a):
            continue
        g = (girate or {}).get(n)
        if g:
            a = np.asarray(Image.fromarray(a.astype(np.float32))
                           .transpose(GIRO_TEXTURE[g]), np.float32)
        mappe[n] = normali(a, px_mm)
    for f in faces:
        if f["name"] in mappe:
            f["normale"] = mappe[f["name"]]
    if not mappe:
        return None
    return _riga(quali, h)


def mappa_del_dt(pdf, riquadro, misura_tex, righe_dt, px_mm_tex, page_no=0):
    """`(mappa delle normali, riga)` per una texture fatta dal `riquadro` del
    foglio - in punti, telaio di misura - con sotto le sue strisce: la mappa
    copre la texture intera, e le strisce restano piane. `misura_tex` e'
    (larghezza, altezza) della texture in pixel, `righe_dt` quante righe sono
    il riquadro, `px_mm_tex` i suoi pixel per mm. `(None, None)` se il file
    non ha lastre di rilievo, o se non si leggono."""
    quali = lastre(pdf, page_no)
    if not quali:
        return None, None
    px_mm = min(float(px_mm_tex), DPI / 25.4)
    k = px_mm / float(px_mm_tex)
    W = max(1, int(round(misura_tex[0] * k)))
    H = max(1, int(round(misura_tex[1] * k)))
    H_dt = min(H, max(1, int(round(righe_dt * k))))
    try:
        h = altezze(pdf, quali, riquadro, (W, H_dt), page_no, dpi=px_mm * 25.4)
    except Exception:                                   # noqa: BLE001
        h = None
    if h is None or not np.any(h):
        return None, _non_si_legge(quali)
    tutta = np.zeros((H, W), np.float32)
    tutta[:H_dt] = h
    return normali(tutta, px_mm), _riga(quali, h)
