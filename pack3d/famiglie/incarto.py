"""
L'incarto: la chiusura dichiarata, l'immagine del prodotto e la
costruzione.
"""
from __future__ import annotations

import traceback

from .. import artwork
from .. import exporters
from .. import folding
from .. import incarto
from .. import lettura as lettura_pdf
from .. import nero
from .. import pralina
from .. import uovo
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from .comune import avviso_pagine, avviso_quadricromia, scrivi_lettura


def build_incarto(pdf, out_glb, quality="hd", lastre_extra=(),
                  colata_riquadro=None):
    """L'incarto a triangolo: il film attorno alla barretta, chiuso sulle
    testate. Vedi `pack3d.incarto`. Come il tubo a cono: la texture e' il
    foglio intero, pulito, e ogni punto della barretta prende la grafica dal
    suo posto sul foglio."""
    dpi, tmax = risoluzione(quality)
    pdf, n_pagine = artwork.pagina_unica(pdf)
    pdf, p, giro = incarto.sulla_tavola(pdf)
    if p is None:
        raise ValueError("incarto a triangolo: il DT non si legge come il "
                         "foglio di una barretta incartata (cinque fasce fra "
                         "righe intere, testate dritte sulla faccia)")
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        pdf, p.regione, "Incarto letto cosi'", incarto.dichiara(p)))
    conti = {}
    clean, lastre = artwork.senza_coperture(pdf, extra=lastre_extra,
                                            regione=p.regione, conti=conti)
    deciso_nero = nero.spia(clean, 0, dpi / 72.0)
    avvisi = []
    pagine = avviso_pagine(n_pagine)
    if pagine:
        avvisi.append(pagine)
    fuori = artwork.avviso_fuori_dt(conti)
    if fuori:
        avvisi.append(fuori)
    avvisi.extend(artwork.avvisi_gda(conti))
    rgb = avviso_quadricromia(clean, regione=p.regione)
    if rgb:
        avvisi.append(rgb)
    if lastre:
        avvisi.append("lastre tecniche e coperture tolte per nome: %s"
                      % ", ".join(lastre))
    avvisi.extend(p.avvisi)
    if giro:
        avvisi.append("foglio girato di %d gradi prima di costruire: l'incarto "
                      "si legge col passo in orizzontale e la scritta dritta" % giro)
    m = 1.0 / PT2MM
    x0, y0, x1, y1 = p.regione
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    lato_pt = max(x1 - x0, y1 - y0)
    dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
    tex = folding.rasterize_panels(
        clean, {"dt": Panel(x0, y0, x1, y1, "dt")}, dpi=dpi_tex, inset_px=0,
        clean=True, note=avvisi, nero_deciso=deciso_nero,
        colata_riquadro=colata_riquadro)["dt"]
    scala = dpi_tex / 72.0
    origine = (round(x0 * scala) / scala * PT2MM, round(y0 * scala) / scala * PT2MM)
    V, UV, T = incarto.maglia(p, origine, scala / PT2MM, tex.size)
    exporters.write_glb_mesh(V, UV, T, tex.convert("RGB"), out_glb, tex_max=tmax)
    return incarto.dichiara(p) + avvisi


def build_uovo(pdfs, out_glb, quality="hd"):
    """L'incarto avvolto: l'uovo incartato col collarino, dai due PDF - il
    foglio e il collarino, in qualunque ordine. Vedi `pack3d.uovo`. La
    texture e' un atlante: la grafica del foglio, quella del collarino e il
    rovescio del film."""
    foglio, collarino = uovo.riconosci(pdfs)
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        foglio.pdf, foglio.regione, "Incarto avvolto letto cosi'",
        uovo.dichiara(foglio, collarino)))
    _dpi, tmax = risoluzione(quality)
    return uovo.costruisci(foglio, collarino, out_glb, tex_max=min(tmax, 4096))


def build_pralina(pdfs, info, out_glb, quality="hd"):
    """L'incarto avvolto in tre pezzi: la pralina, con la stagnola senza
    grafica, il bollino e il pirottino. `pdfs` sono i file dei due pezzi con
    la grafica, in qualunque ordine (`pack3d.pralina.riconosci`). La texture
    e' un atlante: il pirottino e il bollino; la stagnola e' oro pieno con la
    trama nella mappa delle normali."""
    bol, pir = pralina.riconosci(pdfs, info.get("nomi"))
    scrivi_lettura(out_glb, lambda: _lettura_pralina(pdfs, bol, pir))
    _dpi, tmax = risoluzione(quality)
    return pralina.costruisci(bol, pir, out_glb, tex_max=min(tmax, 4096))


def _lettura_pralina(pdfs, bol, pir):
    """La lettura della pralina: la pagina del bollino, coi cartellini."""
    import pypdf
    k = 0 if pralina.leggi(pdfs[0]).pezzo == "bollino" else 1
    pg = pypdf.PdfReader(pdfs[k]).pages[0]
    regione = (0.0, 0.0, float(pg.mediabox.width), float(pg.mediabox.height))
    return lettura_pdf.generica(pdfs[k], regione, "Pralina incartata letta cosi'",
                                pralina.dichiara(bol, pir))


def immagine_in_pdf(dati):
    """Un PDF di una pagina con l'immagine `dati` (JPEG, PNG o WebP), un pixel
    per punto: la grafica di un pezzo d'incarto che arriva come immagine
    (il bollino, il pirottino) entra cosi' nella strada dei PDF - la coda, il
    controllo, il parco - senza cambiare nient'altro. Un JPEG ci va coi suoi
    byte (nessuna ricompressione); le altre immagini senza perdita."""
    import io
    import zlib

    from PIL import Image
    im = Image.open(io.BytesIO(dati))
    w, h = im.size
    if im.format == "JPEG" and im.mode in ("RGB", "L"):
        flusso, filtro = dati, "/DCTDecode"
        colori = "/DeviceRGB" if im.mode == "RGB" else "/DeviceGray"
    else:
        rgb = im.convert("RGBA")
        bianco = Image.new("RGB", rgb.size, (255, 255, 255))
        bianco.paste(rgb, mask=rgb.split()[3])
        flusso, filtro, colori = zlib.compress(bianco.tobytes(), 9), "/FlateDecode", "/DeviceRGB"
    disegno = b"q %d 0 0 %d 0 0 cm /Im0 Do Q" % (w, h)
    oggetti = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
        b"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>" % (w, h),
        b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s "
        b"/BitsPerComponent 8 /Filter %s /Length %d >>\nstream\n" % (
            w, h, colori.encode(), filtro.encode(), len(flusso)) + flusso + b"\nendstream",
        b"<< /Length %d >>\nstream\n" % len(disegno) + disegno + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posti = []
    for k, o in enumerate(oggetti, 1):
        posti.append(len(out))
        out += b"%d 0 obj\n" % k + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(oggetti) + 1)
    for p in posti:
        out += b"%010d 00000 n \n" % p
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(oggetti) + 1, xref))
    return bytes(out)


# Come si chiude l'incarto: "pieghe", il foglio attorno al prodotto e chiuso
# con le pieghe sulle testate (le barrette, `pack3d.incarto`); "avvolto", il
# foglio che avvolge tutto il prodotto: per ora l'uovo incartato col
# collarino (`pack3d.uovo`). Senza dichiarazione, a pieghe.
CHIUSURE_INCARTO = {"pieghe": "pieghe", "a pieghe": "pieghe",
                    "piegato": "pieghe", "barretta": "pieghe",
                    "avvolto": "avvolto", "avviluppato": "avvolto",
                    "avvolgente": "avvolto", "ovetto": "avvolto"}


def chiusura_incarto(valore):
    """"pieghe" o "avvolto"; ValueError per tutto il resto."""
    if valore in (None, ""):
        return "pieghe"
    v = CHIUSURE_INCARTO.get(str(valore).strip().lower())
    if v is None:
        raise ValueError("La chiusura dell'incarto si dice con 'pieghe' (le "
                         "barrette) o 'avvolto' (tipo l'ovetto)")
    return v


def analisi_incarto_dichiarato(pdf, chiusura, pdfs=None, senza=(), nomi=None):
    """L'incarto dichiarato dalla pagina: a pieghe, il foglio della barretta
    (`_analisi_incarto`); avvolto, l'uovo incartato col collarino, dai due
    PDF `pdfs` (`pack3d.uovo`), o la pralina, coi pezzi `senza` grafica (i
    loro numeri, da 1: la stagnola) e i file del bollino e del pirottino
    (`pack3d.pralina`). Si ferma con l'errore che dice cosa manca, e il caso
    va in coda."""
    senza = list(senza or [])
    n = (len(pdfs) if pdfs is not None else 1) + len(senza)
    if senza:
        # un pezzo senza grafica: il codice conosce la pralina avvolta, la
        # stagnola senza grafica col bollino e il pirottino
        if chiusura != "avvolto" or n != 3 or len(senza) != 1:
            raise ValueError("incarto %s in %d %s, %d senza grafica: con un pezzo "
                             "senza grafica il codice conosce la pralina avvolta in "
                             "tre pezzi - la stagnola senza grafica, il bollino e "
                             "il pirottino" % ("avvolto" if chiusura == "avvolto"
                                               else "a pieghe", n,
                                               "pezzo" if n == 1 else "pezzi", len(senza)))
        files = list(pdfs or [pdf])
        bol, pir = pralina.riconosci(files, nomi)
        return dict(kind="pralina", title="Pralina incartata",
                    meta=pralina.dichiara(bol, pir), nomi=list(nomi or []))
    if chiusura == "avvolto":
        # l'avvolto che il codice conosce e' l'uovo: due pezzi, il foglio e
        # il collarino. Con altri pezzi il caso va in coda
        if n != 2:
            raise ValueError("incarto avvolto in %d %s: il codice conosce l'uovo "
                             "in due pezzi, il foglio e il collarino" % (n, "pezzo" if n == 1 else "pezzi"))
        foglio, collarino = uovo.riconosci(list(pdfs or [pdf]))
        return dict(kind="uovo", title="Uovo incartato col collarino",
                    meta=uovo.dichiara(foglio, collarino) + foglio.avvisi
                    + collarino.avvisi)
    if n > 1:
        # un incarto a pieghe in piu' pezzi (un foglio interno e uno esterno,
        # una fascetta): il codice ne conosce uno solo, il caso va in coda
        raise ValueError("incarto a pieghe in %d pezzi: il codice sa costruire "
                         "un pezzo solo, il foglio della barretta" % n)
    letto = _analisi_incarto(pdf, quarto=True)
    if letto is None:
        raise ValueError("incarto a pieghe: il DT non si legge come il foglio "
                         "di una barretta incartata (vuole cinque fasce fra "
                         "righe intere, la faccia in mezzo con le testate "
                         "dritte e i fianchi con le testate inclinate)")
    return letto


def _analisi_incarto(pdf, quarto=False):
    """I cartellini dell'incarto a triangolo, o None se non lo e': il film
    attorno a una barretta rigida, chiuso sulle testate (`pack3d.incarto`).
    Il flowpack non lo rifiuta, lo risolve male - le pinne seghettate al
    posto delle testate -: si prova prima, e su un flowpack esce subito
    (vuole cinque fasce fra righe intere e le testate dritte sulla faccia di
    mezzo)."""
    try:
        letto, ic, _giro = incarto.sulla_tavola(pdf, quarto=quarto)
    except Exception:
        traceback.print_exc()
        return None
    if ic is None:
        return None
    meta = incarto.dichiara(ic) + list(ic.avvisi)
    rgb = avviso_quadricromia(letto, regione=ic.regione)
    if rgb:
        meta.insert(0, rgb)
    return dict(kind="incarto", title="Incarto a triangolo", meta=meta)
