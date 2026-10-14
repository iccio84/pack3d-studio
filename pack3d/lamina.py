"""
La lamina: il foil - a caldo o a freddo - che il DT dichiara su una lastra sua.

Un foil non e' un inchiostro qualsiasi. E' un film metallico trasferito sul
cartoncino (a caldo con una matrice, a freddo con una colla stampata), e
sopra si puo' stampare: sul coperchio esagonale del Kusschen Darkchoc e' la
cornice ramata, e nella legenda del foglio c'e' scritto `cold foil copper
Kurz 404`. Il file lo dice con una tinta piatta che si chiama come la
lavorazione - `..._ColdFoilCopper_Kurz404` - e un'alternativa di colore che
il PDF usa per fingere il rame: arancio, piatto.

Il colore resta quello della texture: e' l'alternativa che il grafico ha
scelto per far vedere il metallo, e gli inchiostri sopra il foil lo
filtrano. Quello che manca e' la luce: dove c'e' la lastra il materiale e'
metallo, liscio, e dove non c'e' resta carta. Sul modello e' la mappa
metallo/ruvidita' di glTF (`metallicRoughnessTexture`), come il film
metallizzato del flowpack (`materiali.py`): ruvidita' nel verde, metallo nel
blu.

Strette di proposito: un "Silver" o un PANTONE 877 C sono inchiostri
metallici stampati, non una lamina, e qui non si trattano.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile

import numpy as np
from PIL import Image

from . import techink

# Come si chiama la lastra di una lamina: foil, Folie (Heissfolie,
# Kaltfolie), lamina, stampa a caldo, hot stamping. "Foil" senza spazi
# dentro un nome solo (`ColdFoilCopper`) vale: si cerca la parola dentro.
_LAMINA = re.compile(r"foil|folie|lamina|hot\s*stamp|stampa\s*a\s*caldo")
# La stessa parola in una voce della legenda, e le parole del prefiltro (il
# testo della pagina in minuscolo).
_VOCE = re.compile(r"(?i)\S*(?:foil|folie|lamina|hot\s*stamp|stampa\s*a\s*caldo)\S*.*")
_PAROLE = ("foil", "folie", "lamina", "stamp", "caldo")

DPI = 150.0
PIENO = 0.25              # quota d'inchiostro per dire che la lastra c'e'
QUOTA_MINIMA = 0.002      # meno di cosi' e' un campione, non una lamina
RUVIDITA_LAMINA = 0.22    # un foil e' quasi uno specchio, ma non del tutto


def e_lamina(nome):
    """Vero se il nome della lastra dice una lamina."""
    return bool(_LAMINA.search(techink._norm(nome)))


def lastre(pdf, page_no=0, legenda=None):
    """I nomi delle lastre di lamina della pagina, ordinati: vuoto se non ce
    n'e'. Costa la lettura delle risorse della pagina, non una resa.

    Se nessuna lastra si chiama come una lamina, si guarda la legenda di
    `legenda` (il file con la legenda, di solito il foglio prima della
    pulizia; senza, `pdf`): su un astuccio da 16 il foil oro e' una tinta
    piatta qualsiasi, `PANTONE 113 C`, e la lamina la dice solo la voce
    "Coldfoil Gold ... KURZ 220" accanto al suo campione giallo. Si
    legge come le aree riservate (`techink.aree_riservate`), dal campione
    davanti alla voce; la resa costa solo se nel testo c'e' una parola della
    lamina."""
    import pypdf
    try:
        pagina = pypdf.PdfReader(pdf).pages[page_no]
        nomi = set(techink.technical_separations(
            pagina, prova=e_lamina).values())
    except Exception:                                   # noqa: BLE001
        return []
    if not nomi:
        try:
            nomi = set(techink.aree_riservate(
                legenda or pdf, page_no, cerca=_VOCE, parola=_PAROLE,
                solo_campione=True))
        except Exception:                               # noqa: BLE001
            nomi = set()
    return sorted(nomi)


def copertura(pdf, quali, riquadro, misura, page_no=0, dpi=DPI):
    """Dove c'e' la lamina, HxW float32 in [0, 1], sul `riquadro` del foglio
    (punti, telaio di misura, y in giu') portato a `misura` (larghezza,
    altezza) in pixel. None se la lastra non si legge."""
    from .materiali import _ritaglio
    cartella = tempfile.mkdtemp(prefix="lamina_")
    try:
        r = _ritaglio(pdf, page_no, riquadro, os.path.join(cartella, "r.pdf"))
        solo = quali[0] if len(quali) == 1 else None
        mappe = techink.mappe_lastre(r, 0, dpi, solo=solo)
    finally:
        shutil.rmtree(cartella, ignore_errors=True)
    c = None
    for nome in quali:
        m = mappe.get(techink._norm(nome))
        if m is None:
            continue
        ink = (255.0 - m.astype(np.float32)) / 255.0
        ink = np.where(ink >= PIENO, 1.0, ink / PIENO).astype(np.float32)
        a = np.asarray(Image.fromarray(ink).resize(tuple(misura), Image.BILINEAR),
                       np.float32)
        c = a if c is None else np.maximum(c, a)
    return c


def mappa(pdf, riquadro, misura_tex, px_mm_tex, carta, page_no=0,
          legenda=None):
    """`(mappa metallo/ruvidita', riga)` per una texture fatta dal `riquadro`
    del foglio - in punti, telaio di misura - di `misura_tex` pixel,
    `px_mm_tex` per mm. Fuori dalla lamina la ruvidita' e' `carta`, quella
    che il materiale avrebbe senza mappa. `(None, None)` se il file non ha
    lastre di lamina; `(None, riga)` se ce l'ha ma non si legge, o copre
    troppo poco."""
    quali = lastre(pdf, page_no, legenda)
    if not quali:
        return None, None
    px_mm = min(float(px_mm_tex), DPI / 25.4)
    k = px_mm / float(px_mm_tex)
    W = max(1, int(round(misura_tex[0] * k)))
    H = max(1, int(round(misura_tex[1] * k)))
    try:
        c = copertura(pdf, quali, riquadro, (W, H), page_no, dpi=px_mm * 25.4)
    except Exception:                                   # noqa: BLE001
        c = None
    if c is None or float(c.mean()) < QUOTA_MINIMA:
        return None, ("lamina: il file ha la lastra %s ma sul DT non si legge, "
                      "il modello esce senza metallo" % ", ".join(quali))
    mr = np.empty((H, W, 3), np.uint8)
    mr[..., 0] = 255
    mr[..., 1] = np.round((c * RUVIDITA_LAMINA + (1 - c) * carta) * 255)
    mr[..., 2] = np.round(c * 255)
    return Image.fromarray(mr), (
        "lamina dal DT: il %.1f%% della grafica e' foil (%s); sul modello e' "
        "metallo, col colore della texture" % (100.0 * float(c.mean()),
                                               ", ".join(quali)))
