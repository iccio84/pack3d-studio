"""
Quello che le costruzioni delle famiglie hanno in comune: gli avvisi
sulle pagine e sulla quadricromia, le tinte dei materiali, la pellicola e il
rilievo, la lettura accanto al GLB, i nomi delle famiglie.
"""
from __future__ import annotations

import traceback


from .. import ballotin
from .. import folding
from .. import lamina
from .. import lettura as lettura_pdf
from .. import vassoio


# --------------------------------------------------------------------------- #
# costruzione
# --------------------------------------------------------------------------- #
def avviso_quadricromia(pdf, page_no=0, regione=None):
    """La riga sulla quadricromia, se il file ne ha bisogno.

    Costa una lettura di pypdf e una passeggiata nei dizionari delle risorse:
    centesimi di secondo e niente in memoria, misurati su tutto il parco.

    Con `regione` - il riquadro del DT - contano solo le immagini disegnate
    sul DT: fuori ci sono le note, e il logo RGB dello studio nel cartiglio
    non e' grafica del pack.
    """
    from pack3d import techink, tracciati
    try:
        import pypdf
        dentro = (None if regione is None else
                  tracciati.immagini_nel_riquadro(pdf, regione, page_no))
        return techink.avviso_rgb(pypdf.PdfReader(pdf).pages[page_no], dentro)
    except Exception:
        return None


def avviso_pagine(pdf):
    """La riga sulle pagine, se il file ne ha piu' di una.

    Si lavora sempre e solo sulla PRIMA pagina: un artwork su piu' pagine e'
    quasi sempre lo stesso pack ripetuto per lingua - sul T2 di cialde
    "64-GERMANY" e "01-ITALY", identici tranne il piede - e mescolarle vuol
    dire misurare un pack su una pagina e stamparne un altro. Lo si dice,
    perche' chi ha caricato il file sappia quale pagina e' diventata il
    modello. Le altre la costruzione non le vede proprio: vedi
    `artwork.pagina_unica`, che torna anche quante erano - ed e' quel numero
    che si passa qui, perche' la copia di pagine ne ha una.
    """
    if isinstance(pdf, int):
        n = pdf
    else:
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(pdf)
            try:
                n = len(doc)
            finally:
                doc.close()
        except Exception:
            return None
    if n <= 1:
        return None
    return ("il PDF ha %d pagine: si usa solo la prima, le altre di solito "
            "sono lo stesso pack in altre lingue" % n)


# Le tinte delle strisce sotto lo steso, coi nomi dei loro materiali: sul
# modello diventano colori pieni (`steso.senza_strisce`)
TINTE_VASSOIO = {vassoio.INTERNO: "interno", vassoio.TAGLIO: "taglio"}
TINTE_BALLOTIN = {ballotin.INTERNO: "interno", ballotin.TAGLIO: "taglio"}
# il tubo ha in piu' il rovescio in piena luce: la bocca rimboccata, fuori
TINTE_TUBO = {**TINTE_BALLOTIN, folding.INTERNO: "rovescio"}


# Il viewer glamlab chiama questa API con le sue etichette: il suo
# BuildFromPdfPanel manda kind "cartotecnico", non "carton". Senza sinonimo
# quel valore non entrava in nessun ramo e ogni astuccio finiva dal solutore
# flowpack, che e' esattamente l'errore contro cui le regole mettono in
# guardia: la tipologia si dichiara, e se la dichiarazione non viene
# riconosciuta e' come non averla.
SINONIMI_KIND = {"cartotecnico": "carton", "astuccio": "carton",
                 "carton": "carton", "flowpack": "flowpack",
                 "vassoio": "vassoio", "espositore": "vassoio",
                 "display": "vassoio", "tray": "vassoio",
                 "coppa": "coppa", "coppa conica": "coppa", "cup": "coppa",
                 "bicchiere": "coppa", "sleeve": "coppa", "tappo": "coppa",
                 # il cono gelato col lid e' della stessa famiglia: pezzi
                 # tondi, uno steso a settore e una chiusura
                 "cono": "coppa", "cono gelato": "coppa", "cone": "coppa",
                 "lid": "coppa",
                 # la busta stand-up col soffietto, vedi `pack3d.pouch`
                 "pouch": "pouch", "doypack": "pouch", "stand-up": "pouch",
                 "standup": "pouch", "busta": "pouch", "bag": "pouch",
                 # un vassoio coi suoi flowpack dentro, vedi `pack3d.riempimento`
                 "riempimento": "riempimento", "riempimenti": "riempimento",
                 "vassoio pieno": "riempimento", "filling": "riempimento",
                 # un foglio che avvolge un prodotto: a pieghe (la barretta)
                 # o avvolto tutto (l'ovetto), vedi `analisi_incarto_dichiarato`
                 "incarto": "incarto", "incarti": "incarto",
                 "wrapping": "incarto", "wrapper": "incarto"}


def normalizza_kind(kind):
    if kind is None:
        return None
    return SINONIMI_KIND.get(str(kind).strip().lower(), kind)


KIND_NOTI = ("carton", "flowpack", "vassoio", "coppa", "pouch", "riempimento",
             "incarto")
# come l'utente ha chiamato il pack, per il controllo dell'AI
NOMI_KIND = {"carton": "cartotecnico", "flowpack": "flowpack",
             "vassoio": "vassoio espositore", "coppa": "coppa o cono gelato",
             "pouch": "pouch (busta stand-up col soffietto sul fondo)",
             "riempimento": "riempimento (un vassoio espositore coi suoi flowpack)",
             "incarto": "incarto (un foglio di carta, alluminio o plastica che "
                        "avvolge un prodotto)"}


def dichiarazione(kind, pezzi):
    """La tipologia dichiarata, a parole: "cartotecnico in 2 pezzi"."""
    nome = NOMI_KIND.get(kind, "non dichiarata")
    return nome + (" in %d pezzi" % pezzi if pezzi > 1 else "")


# La pellicola delle finestre. Un astuccio con la finestra di solito ha una
# lastra di plastica trasparente sottilissima incollata dall'interno, ma non
# sempre: la pagina lo chiede ogni volta che l'analisi trova una finestra
# (`finestre_da_chiedere`), e la risposta arriva come opzione `pellicola`.
# Senza, le finestre restano aperte, come sono sempre state.
SENZA_PELLICOLA = ("finestre senza pellicola, come dichiarato: aperte, si vede "
                   "dentro")


def rilievo_sicuro(fa, *args, coppia=False, **kw):
    """Il rilievo non deve mai fermare una costruzione: se leggerlo si rompe,
    il modello esce senza, e la riga lo dice."""
    try:
        return fa(*args, **kw)
    except Exception as e:                          # noqa: BLE001
        traceback.print_exc()
        riga = ("rilievo: la lastra c'e' ma la mappa non si e' fatta (%s), il "
                "modello esce senza" % e)
        return (None, riga) if coppia else riga


# la ruvidita' della carta di un GLB a una maglia (`exporters.write_glb_mesh`):
# fuori dalla lamina la mappa la tiene com'era
RUVIDITA_MAGLIA = 0.42
# e quella del cartoncino dell'astuccio (`exporters._write_glb_steso`)
RUVIDITA_CARTA = 0.85


def lamina_della_tela(pdf, riquadro, misura_tex, misura_tela, px_mm, nome,
                      avvisi, carta=RUVIDITA_MAGLIA, legenda=None):
    """La mappa metallo/ruvidita' della lamina sulla `tela` (la texture del
    `riquadro`, `misura_tex` pixel, con sotto le strisce fino a
    `misura_tela`), o None. Come il rilievo, la lamina non deve mai fermare
    una costruzione: se leggerla si rompe il modello esce senza, e la riga
    lo dice."""
    from PIL import Image
    try:
        mr, riga = lamina.mappa(pdf, riquadro, misura_tex, px_mm, carta,
                                legenda=legenda)
    except Exception as e:                          # noqa: BLE001
        traceback.print_exc()
        mr, riga = None, ("lamina: la lastra c'e' ma la mappa non si e' "
                          "fatta (%s), il modello esce senza metallo" % e)
    if riga:
        avvisi.append("%s: %s" % (nome, riga))
    if mr is None:
        return None
    k = mr.width / float(misura_tex[0])
    fondo = (255, round(carta * 255), 0)
    tutta = Image.new("RGB", (max(1, round(misura_tela[0] * k)),
                              max(1, round(misura_tela[1] * k))), fondo)
    tutta.paste(mr, (0, 0))
    return tutta


def pellicola_sicura(fa, *args, **kw):
    """La pellicola, o None se farla si rompe: le finestre restano aperte, e
    la riga della pellicola lo dice (`riga_pellicola`)."""
    try:
        return fa(*args, **kw)
    except Exception:                               # noqa: BLE001
        traceback.print_exc()
        return None


def riga_pellicola(quante, fatta, margine):
    """La riga per chi guarda il modello, quando la pellicola e' chiesta."""
    if not fatta:
        return ("pellicola chiesta ma non messa: non ho trovato dove reggerla "
                "sulle finestre, che restano aperte")
    return ("pellicola trasparente sulle finestre (%d): una lastra di plastica "
            "sottilissima incollata dall'interno, %g mm oltre il bordo - nel "
            "GLB e' il nodo 'pellicola'; le viste del controllo non la "
            "mostrano, le finestre vi si vedono aperte" % (quante, margine))


def scrivi_lettura(out_glb, fai):
    """La lettura del PDF accanto al GLB (`pack3d.lettura`): `fai()` la
    disegna. Mai un errore: se non si disegna, il modello si costruisce lo
    stesso e la pagina non apre la finestra."""
    try:
        dati = fai()
        if dati:
            with open(out_glb + lettura_pdf.ACCANTO, "wb") as fh:
                fh.write(dati)
    except Exception:
        traceback.print_exc()
