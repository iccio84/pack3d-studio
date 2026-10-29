"""
Il flowpack: l'analisi del PDF, il verso sulla grafica, i parametri che
sceglie l'agente e la costruzione (`build_flowpack`).
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
import hashlib
import os
import threading
import traceback

from PIL import Image
import numpy as np

from .. import artwork
from .. import controllo
from .. import dieline as dl
from .. import exporters
from .. import flowpack as fpk
from .. import folding
from .. import lettura as lettura_pdf
from .. import materiali
from .. import nero
from .. import quote as quotature
from .. import steso as lo_steso
from .. import verifica
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from ..exporters import _normals
from ..flowpack import Flowpack
from ..flowpack import fin_on_surface
from .comune import avviso_pagine, avviso_quadricromia, scrivi_lettura


# gonfiore: raccordo, esponente spigolo, grinza, pancia, rastremazione
# Il rigonfiamento e' una scala continua 1-10: rigido 1-3, medio 4-6,
# morbido 7-10. Le tre fasce restano come etichette per l'utente, ma i
# parametri si interpolano sul livello, cosi' "medio 4" e "medio 6" non sono
# la stessa cosa.
FASCE = {"rigido": 2, "medio": 5, "morbido": 8}
ANCORE = {   # livello -> raccordo, esponente, grinza, pancia, rastremazione
    1:  dict(soft_r=4.5, soft_n=2.0, wrinkle_mm=0.00, bulge=0.008, taper=6.0),
    5:  dict(soft_r=7.5, soft_n=2.4, wrinkle_mm=0.35, bulge=0.030, taper=16.0),
    10: dict(soft_r=11.0, soft_n=2.8, wrinkle_mm=0.75, bulge=0.060, taper=30.0),
}


def gonfiore(valore):
    """Parametri di forma per un livello 1-10, o per un'etichetta."""
    if isinstance(valore, str):
        v = FASCE.get(valore.strip().lower())
        if v is None:
            try:
                v = float(valore)
            except ValueError:
                v = 5
    else:
        v = float(valore)
    v = max(1.0, min(10.0, v))
    lo, hi = (1, 5) if v <= 5 else (5, 10)
    t = (v - lo) / (hi - lo)
    a, b = ANCORE[lo], ANCORE[hi]
    return {k: a[k] + (b[k] - a[k]) * t for k in a}


GONFIORE = {k: gonfiore(k) for k in FASCE}

# casi gia' calibrati: l'analizzatore automatico non copre ogni impaginato,
# quindi i flowpack risolti a mano restano disponibili tramite la firma della
# pagina (larghezza x altezza in punti, arrotondate).
CASI = {
    (1672, 737): dict(
        name="barretta proteica",
        sheet=(481.78, 120.34, 481.78 + 142 / PT2MM, 120.34 + 141 / PT2MM),
        girth_span=(120.34 + 15 / PT2MM, 120.34 + 126 / PT2MM),
        W=36.0, T=19.5, L=116.0, end_fin=13.0, side_fin=15.0,
        back_a=18.0, back_b=18.0, web=141.0, step=142.0,
        fin_open=52.6, teeth=20, soft="morbido",
        drop_seps=["Coldseal", "White", "Stand Blau", "All", "Label_*"],
    ),
}


def _sig(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        p = pdf.pages[0]
        return (int(p.width), int(p.height))


# Analisi gia' fatte: impronta del file -> (bbox, Flowpack, motivo del ripiego).
# Sono tre oggetti piccoli, non le rasterizzazioni: la memoria qui non pesa.
_ANALISI = OrderedDict()
_ANALISI_MAX = 8
_ANALISI_CHIAVE = threading.Lock()


def _impronta(pdf):
    """sha256 del file.

    Non `_sig`: quella e' la misura della pagina, e due artwork diversi dello
    stesso formato hanno la stessa firma. Per il registro dei casi calibrati,
    scritto a mano, puo' bastare; per una memoria automatica sarebbe il modo
    di costruire il pack sbagliato con le quote di un altro.
    """
    h = hashlib.sha256()
    with open(pdf, "rb") as fh:
        for blocco in iter(lambda: fh.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def analisi_flowpack(pdf):
    """Analisi automatica del flowpack, fatta una volta sola per file.

    L'interfaccia chiama /api/analyze per i cartellini e subito dopo
    /api/build: senza memoria la stessa analisi si rifaceva da capo, e non e'
    poco - sette secondi e mezzo di CPU e trecento MB, due volte. Su
    un'istanza piccola e' la differenza fra farcela e non farcela.
    """
    imp = _impronta(pdf)
    with _ANALISI_CHIAVE:
        if imp in _ANALISI:
            _ANALISI.move_to_end(imp)
            return _ANALISI[imp]
    # Si rasterizza QUI, una volta, alla risoluzione piu' alta che serva: da
    # qui in avanti find_blocks (100 dpi) e la texture riscalano quella invece
    # di rifarla. Senza, il primo che chiede e' find_blocks a 100 e l'analisi
    # deve comunque rifarla piu' grande.
    dl.render_page(pdf, 0, fpk.SCALA_ANALISI)

    box, _dt = printed_bbox(pdf)
    ripiego = None
    try:
        fp = fpk.analyze_auto(pdf, bbox=box)
    except Exception as e:
        # Secondo tentativo, sul RIQUADRO DELLA FUSTELLA invece che
        # sull'ingombro stampato. Non sono la stessa cosa: sul T1 al
        # cioccolato fresco la grafica scende sotto il tracciato - c'e' una striscia di
        # fondo bianco che il disegno non comprende - e misurando lo stampato
        # il nastro veniva 121 mm invece di 115. Con quel numero le fasce non
        # chiudono e il file non si costruisce; con la fustella si risolve.
        #
        # Si paga solo qui, cioe' solo sui file che altrimenti non uscirebbero
        # affatto: rileggere i tracciati sono otto secondi, e chi si risolve al
        # primo colpo non li paga. Vedi `fpk.riquadro_fustella`.
        primo = str(e)
        fp = ripiego = None
        try:
            riq = fpk.riquadro_fustella(pdf, stampato=box)
            if riq and riq != box:
                fp = fpk.analyze_auto(pdf, bbox=riq)
                fp.warnings.append(
                    "riquadro preso dalla fustella e non dallo stampato: "
                    "la grafica esce dal tracciato, e misurando lo stampato "
                    "le fasce non chiudevano")
        except Exception:
            fp = None
        if fp is None:
            # Terzo tentativo, sulle COPIE del DT: le copie tecniche e la
            # miniatura sono lo stesso disegno in scala, senza grafica sopra.
            # E' la regola "se non capisci le dimensioni prendi come
            # riferimento la miniatura". Vedi `tools.quote_dalla_copia`.
            try:
                from pack3d.tools import quote_dalla_copia
                fp = quote_dalla_copia(pdf)
            except Exception:
                fp = None
        if fp is None:
            # Il ripiego era muto, e un modello costruito da un'analisi
            # peggiore non esce sbagliato: esce plausibile, che e' peggio. E
            # guarda solo il DT con la grafica: sulla pagina intera misurava
            # anche quote, copie tecniche e cartiglio.
            fp = fpk.analyze(pdf, bbox=box)
            ripiego = primo
    with _ANALISI_CHIAVE:
        _ANALISI[imp] = (box, fp, ripiego)
        while len(_ANALISI) > _ANALISI_MAX:
            _ANALISI.popitem(last=False)
        return _ANALISI[imp]


# I versi gia' decisi: impronta del file -> (giro, avviso). Come _ANALISI:
# /api/analyze e /api/build chiedono lo stesso file, e la prova costa
# un'analisi.
_VERSO_FP = OrderedDict()


def flowpack_sulla_grafica(pdf):
    """`(pdf, giro, avviso, verso)`: lo steso di un flowpack nel verso della
    grafica, e i gradi orari di cui sul foglio tornato e' girato il testo del
    fronte - zero se si legge dritto o se il testo vivo non c'e'.

    E' `artwork.astuccio_sulla_grafica` per il flowpack, e per la stessa
    ragione: uno steso non deve dare un pack diverso secondo come sta sulla
    tavola. Il solutore gli 90 gradi li regge gia' - traspone i suoi ingressi
    e ritrova le pinne - ma la texture seguiva il FOGLIO: girato lo steso di
    mezzo giro, il T1 della barretta fresca usciva a testa in giu', e sul T1 della merendina
    al mandarino girato di un quarto la colata, che si allinea su un'onda
    orizzontale, si incollava storta e la fascia rossa spariva.

    Il verso lo da' il testo vivo del FRONTE (`fpk.fronte_in_pagina`): se e'
    girato, si gira la pagina (`artwork.pagina_girata`) e si rifa' l'analisi,
    e il giro vale solo se sul foglio girato lo steso si risolve senza ripiego
    e il fronte si legge dritto. Da li' in avanti tutto - colata, nero,
    testate, texture - lavora sullo steso com'e' negli originali del parco,
    che si leggono tutti col fronte dritto. Senza testo vivo sul fronte il
    verso non si conosce e il foglio resta com'e'.

    Un caso calibrato non passa di qui: le sue quote sono scritte a mano sul
    foglio com'e'.
    """
    from pack3d import tracciati
    imp = _impronta(pdf)
    with _ANALISI_CHIAVE:
        noto = _VERSO_FP.get(imp)
    if noto is None:
        giro, avviso, resta = 0, None, 0

        def verso(p):
            _box, fp, ripiego = analisi_flowpack(p)
            if ripiego is not None:
                return None
            return tracciati.verso_grafica(
                p, {"front": fpk.fronte_in_pagina(fp)}).get("front", -1)

        try:
            g = verso(pdf)
        except Exception:
            g = None
        if g == -1:
            # Detto, non taciuto: e' l'unico caso in cui il pack puo' ancora
            # dipendere da come lo steso sta sulla tavola.
            avviso = ("verso della grafica non letto: sul fronte non c'e' "
                      "testo vivo (scritte vettorializzate), e lo steso resta "
                      "com'e' sulla tavola - il verso va controllato sul "
                      "modello")
        elif g:
            girato = artwork.pagina_girata(pdf, (360 - g) % 360)
            try:
                dritto = girato != pdf and verso(girato) == 0
            except Exception:
                dritto = False
            if dritto:
                giro = (360 - g) % 360
                avviso = ("steso girato di %d gradi prima di risolvere: sulla "
                          "tavola la grafica del fronte era girata, e pinne, "
                          "retro e colata si leggono nel suo verso" % giro)
            else:
                resta = g
                avviso = ("la grafica del fronte e' girata di %d gradi sullo "
                          "steso, ma girato il foglio non si risolve col "
                          "fronte dritto: resta letto com'e' sulla tavola" % g)
        noto = (giro, avviso, resta)
        with _ANALISI_CHIAVE:
            _VERSO_FP[imp] = noto
            while len(_VERSO_FP) > _ANALISI_MAX:
                _VERSO_FP.popitem(last=False)
    giro, avviso, resta = noto
    return ((artwork.pagina_girata(pdf, giro) if giro else pdf), giro, avviso,
            resta)


def _flowpack_from_case(case):
    return Flowpack(W=case["W"], T=case["T"], L=case["L"], end_fin=case["end_fin"],
                    side_fin=case["side_fin"], back_a=case["back_a"],
                    back_b=case["back_b"], web_mm=case["web"], step_mm=case["step"],
                    sheet=case["sheet"], girth_span=case["girth_span"])


def sezione_da_agente(params):
    """Larghezza e spessore del pack CHIUSO, se l'agente li ha misurati.

    Le cordonature dicono dove il film e' cordonato, non che forma prende una
    volta riempito: sul croccante T2 i pannelli danno 50 x 11, ma il pack in
    mano e' 41 x 20. Hanno lo stesso perimetro, quindi dalla fustella non si
    distinguono: il rapporto puo' arrivare solo da chi guarda il prodotto.
    """
    if not isinstance(params, dict):
        return None
    q = params.get("quote")
    if not isinstance(q, dict):
        return None
    try:
        w, t = float(q.get("larghezza")), float(q.get("spessore"))
    except (TypeError, ValueError):
        return None
    return (w, t) if w > 0 and t > 0 else None


def livello_da_agente(params):
    """Il livello 1-10 scelto dall'agente con "Scegli tu", se l'ha riportato."""
    if not isinstance(params, dict):
        return None
    pc = params.get("parametri_costruzione")
    try:
        return max(1.0, min(10.0, float(pc.get("rigonfiamento"))))
    except (AttributeError, TypeError, ValueError):
        return None


def pinne_da_agente(params):
    """Apertura delle pinne 1-3, se l'agente l'ha decisa."""
    if not isinstance(params, dict):
        return None
    pc = params.get("parametri_costruzione")
    try:
        return max(1.0, min(3.0, float(pc.get("apertura_pinne"))))
    except (AttributeError, TypeError, ValueError):
        return None


def nello_spessore_scelto(opts):
    """Il rigonfiamento del flowpack a pinna nello spessore invece che nel
    rapporto del DT: `"gonfio": "spessore"` fra le opzioni del caso. Una
    scelta del pack, come il livello (`flowpack.sezione_rigonfiata`)."""
    return str(opts.get("gonfio", "")).strip().lower() == "spessore"


def saldatura_scelta(opts):
    """La saldatura delle pinne 0-3 scelta nella pagina: quanto si vedono le
    nervature delle ganasce. Se non la dice, 3: le nervature di sempre."""
    try:
        return max(0, min(3, int(opts.get("saldatura", 3))))
    except (TypeError, ValueError):
        return 3


def aree_da_agente(params):
    """Le lastre delle aree riservate che l'agente ha riconosciuto guardando.

    E' il caso dei file che l'area riservata non la dichiarano da nessuna
    parte - niente livello, niente nome di lastra, niente scritta sopra il
    riquadro - dove la lettura automatica non ha niente da leggere e l'unica
    cosa che resta e' guardare. L'agente indica il riquadro, `area_riservata`
    trova la lastra e gliela MOSTRA, e quello che passa di qui e' gia' stato
    confermato a occhio.

    Vuoto se non c'e' analisi allegata: allora il file resta come prima, che
    e' il comportamento di sempre, e il build lo dichiara.
    """
    if not isinstance(params, dict):
        return []
    pc = params.get("parametri_costruzione")
    voci = pc.get("aree_riservate") if isinstance(pc, dict) else None
    if not isinstance(voci, (list, tuple)):
        return []
    return [str(v).strip() for v in voci if str(v).strip()]


def materiali_dichiarati(valore):
    """`{lastra: ruolo}` dichiarato nella richiesta, o None.

    I ruoli sono quelli di `materiali.RUOLI`. Serve al caso che li sa gia' -
    il parco, che costruisce senza AI, o la routine che riprende un caso in
    coda - e vince sulla lettura: e' quello che qualcuno ha guardato. Una voce
    con un ruolo che non esiste si scarta, il resto vale.
    """
    if not isinstance(valore, dict):
        return None
    fuori = {str(k).strip(): v for k, v in valore.items()
             if str(k).strip() and v in materiali.RUOLI}
    return fuori or None


# I ruoli delle lastre che l'AI ha letto, per file: la correzione rifa' la
# costruzione, e la domanda non va rifatta. Pochi, come le altre memorie.
_MATERIALI_AI = {}
_MATERIALI_AI_MAX = 8


def leggi_materiali(pdf, foglio, dichiarati, note):
    """La `materiali.Lettura` del foglio, coi ruoli che l'AI legge quando ne
    mancano. In `note` le righe da dire. Mai un'eccezione: senza lettura il
    film resta plastica, come prima."""
    try:
        lettura = materiali.leggi(pdf, foglio, dichiarati=dichiarati)
    except Exception as e:
        traceback.print_exc()
        note.append("materiali dai DT non letti (%s): il film resta plastica" % e)
        return None
    if lettura is None:
        return None
    irrisolte = lettura.irrisolte()
    if irrisolte and not dichiarati and controllo.attivo():
        chiave = artwork._impronta(pdf)
        scelta = _MATERIALI_AI.get(chiave)
        if scelta is None:
            scelta = controllo.ruoli_lastre(pdf)
            if "errore" not in scelta and chiave:
                if len(_MATERIALI_AI) >= _MATERIALI_AI_MAX:
                    _MATERIALI_AI.pop(next(iter(_MATERIALI_AI)))
                _MATERIALI_AI[chiave] = scelta
        if "errore" in scelta:
            note.append("materiali dai DT: le lastre %s stanno in copie del DT "
                        "senza un titolo leggibile e l'AI non ha risposto (%s): "
                        "il film resta plastica"
                        % (", ".join(irrisolte), scelta["errore"]))
        else:
            lettura.assegna(scelta["ruoli"], "ai")
    elif irrisolte:
        note.append("materiali dai DT: le lastre %s stanno in copie del DT senza "
                    "un titolo leggibile, e senza AI non so cosa sono"
                    % ", ".join(irrisolte))
    senza = materiali.avviso_senza_bianco(lettura)
    if senza:
        note.append(senza)
    return lettura


def colata_da_agente(params):
    """Il riquadro della colata che l'agente ha indicato guardando.

    Serve ai file che la colata non la mettono su un livello suo - sul parco
    di prova otto su nove - dove il codice non ha niente da misurare e
    l'ombra resta azzurra. L'agente indica la banda, `colata_a_occhio` gliela
    MOSTRA prima e dopo, e quello che passa di qui e' gia' stato confermato a
    occhio. Il livello, quando c'e', viene comunque prima.

    `None` se non c'e' analisi allegata, o se il riquadro non e' quattro
    numeri: un riquadro mezzo scritto e' peggio di nessun riquadro.
    """
    if not isinstance(params, dict):
        return None
    pc = params.get("parametri_costruzione")
    r = pc.get("colata") if isinstance(pc, dict) else None
    if not isinstance(r, dict):
        return None
    try:
        v = tuple(float(r[k]) for k in ("x_mm", "y_mm", "w_mm", "h_mm"))
    except (KeyError, TypeError, ValueError):
        return None
    return v if v[2] > 0 and v[3] > 0 else None


def scatola_da_agente(params):
    """Se il film avvolge un corpo rigido che arriva fino alla saldatura.

    Non e' la stessa cosa del rigonfiamento: un pack puo' essere teso sul
    prodotto senza contenere una scatola. Quello che cambia e' la pinna, e
    cambia per un motivo meccanico: le ganasce appiattiscono un tubo solo se
    dentro c'e' aria. Con una scatola dentro non c'e' niente da appiattire.
    """
    if not isinstance(params, dict):
        return False
    pc = params.get("parametri_costruzione")
    if not isinstance(pc, dict):
        return False
    return bool(pc.get("avvolge_scatola"))


def printed_bbox(pdf):
    """Riquadro del blocco stampato, in punti PDF.

    Senza questo si misura l'intera tavola, che contiene anche le viste
    tecniche e i cartigli: da li' escono pack larghi quanto il foglio.
    """
    try:
        from pack3d.tools import find_blocks
        b = [x for x in find_blocks(pdf)["blocchi"] if x["tipo"] == "stampato"]
        if not b:
            return None, None
        b = b[0]
        mm = 1.0 / PT2MM
        box = (b["x_mm"] * mm, b["y_mm"] * mm,
               (b["x_mm"] + b["w_mm"]) * mm, (b["y_mm"] + b["h_mm"]) * mm)
        return box, b.get("maschera_dt_x_mm")
    except Exception:
        return None, None


# Falde misurate sui pack che conosciamo, dal piu' piccolo al piu' grande:
#
#   T1 della barretta fresca  nastro 144   falda 14,0
#   T1 ai cereali     nastro 122   falda 16,0
#   T1 farcito    nastro 165   falda 12,5
#   brioche T10 Promo nastro 420   falda  4,1
#   barretta proteica             nastro 141   falda 15,0
#
# Fra 4 e 16 mm, su nastri che vanno da 122 a 420. E' fisica, non statistica:
# la falda e' il lembo che schiacciano le ganasce, e le ganasce non diventano
# piu' grandi perche' il sacchetto lo e'. Il solutore invece accetta una falda
# fino al 25% del nastro, che su 420 mm vuol dire 105: un valore che non e'
# una falda, e' un quarto del film.
FALDA_VISTA_MAX = 16.0


def falda_sospetta(fp):
    """Avviso se la falda risolta non somiglia a nessuna falda mai misurata.

    Non rifiuta niente: una quota fuori scala puo' essere giusta su un pack
    che non abbiamo mai visto. Ma un modello costruito su una falda sbagliata
    esce plausibile invece che evidentemente rotto - il difetto che questo
    progetto ha gia' pagato tre volte - e allora almeno lo dice.
    """
    if fp.side_fin <= FALDA_VISTA_MAX * 1.5:
        return None
    return ("FALDA FUORI SCALA: %.1f mm, contro i %.0f mm della piu' grande "
            "mai misurata e %.1f di spessore del pack. Se il pack sembra "
            "troppo sottile e' questo: il solutore ha scelto le pieghe "
            "sbagliate, e nastro e passo restano giusti lo stesso."
            % (fp.side_fin, FALDA_VISTA_MAX, fp.T))


def build_flowpack(pdf, out_glb, teeth, soft, case=None, quality="hd",
                   sezione=None, scatola=False, pinne=None, lastre_extra=(),
                   colata_riquadro=None, materiali_dich=None,
                   materiali_ai=None, saldatura=3, nello_spessore=False):
    """Costruisce il flowpack con le tecniche messe a punto sul campo.

    Quattro cose che la versione base non faceva, e che senza si vedono subito:

    1. Gonfiando, la sezione si arrotonda **a perimetro costante**: lo spessore
       cresce e la larghezza cala. Alzare solo lo spessore inventa film.
    2. La grafica si mappa **per pannello**, usando gli spigoli della sezione
       come nodi: con l'arco uniforme ogni fascia scivola.
    3. Le pinne portano la **zigrinatura** - denti alti 2/3 dell'equilatero,
       smussati - contata sul bordo della pinna.
    4. Le pinne non restano **mai a filo**: si aprono a farfalla verso la punta.

    Le pinne sono saldate, i due strati uniti; `saldatura` (0-3) dice quanto
    si vedono le nervature delle ganasce: 0 nessuna, 3 piene.
    """
    import math
    par = gonfiore(soft)
    nu, nv = (320, 420) if quality == "alta" else (190, 260)
    dpi, tmax = risoluzione(quality)
    # Una pagina sola: le altre sono lo stesso pack in altre lingue, e da qui
    # in avanti non le vede nessuno. Vedi `artwork.pagina_unica`.
    pdf, n_pagine = artwork.pagina_unica(pdf)
    conti = {}
    giro = None
    verso_fronte = 0
    # di quanti gradi orari il foglio di lavoro e' girato rispetto al PDF:
    # la texture ci torna alla fine (`pack3d.steso`)
    gradi = 0
    note_mat = []
    if case:
        # anche qui le lastre dell'agente: un caso calibrato elenca a mano
        # quello che sapeva allora, non quello che si vede oggi guardando. E
        # anche qui i box area, che si tolgono su tutti i modelli: vedi
        # `artwork.senza_coperture`.
        fp0 = _flowpack_from_case(case)
        lettura = leggi_materiali(pdf, fpk.foglio_in_pagina(fp0),
                                  materiali_dich, note_mat)
        clean, lastre = artwork.senza_coperture(
            pdf, extra=list(lastre_extra) + materiali.da_togliere(lettura),
            regione=fpk.foglio_in_pagina(fp0),
            conti=conti, fisse=case["drop_seps"])
        box = None
        ripiego = None
    else:
        # Nel verso della grafica: da qui in avanti `pdf` e' lo steso girato,
        # se sulla tavola stava girato, e con lui il riquadro della colata
        # che l'agente ha indicato guardando il foglio com'era. Vedi
        # `flowpack_sulla_grafica`.
        sorgente = pdf
        pdf, gradi, giro, verso_fronte = flowpack_sulla_grafica(pdf)
        colata_riquadro = artwork.riquadro_girato(sorgente, colata_riquadro,
                                                  gradi)
        # Stessa analisi di /api/analyze, non una seconda uguale: il ripiego
        # muto (che sul T1 della barretta fresca dava corpo e pinne 136,5 e 8,0 invece
        # di 138,7 e 6,9, con la grafica che scivolava sul fronte) resta
        # dichiarato, perche' il motivo viaggia insieme alle quote.
        box, fp0, ripiego = analisi_flowpack(pdf)
        # Il materiale si legge sul file intero, prima della pulizia: le
        # copie del DT che lo dicono stanno fuori dallo steso. Se il film e'
        # metallizzato, il grigio che il DT disegna per l'alluminio non e' un
        # inchiostro, e va via con le altre lastre tecniche.
        lettura = leggi_materiali(pdf, fpk.foglio_in_pagina(fp0),
                                  materiali_dich, note_mat)
        # L'analisi e' fatta, e con lei le quote: ora, e non prima, si tolgono
        # le lastre tecniche dichiarate per nome e TUTTO quello che sta fuori
        # dallo steso - quote, copie tecniche, legenda, cartiglio, miniature.
        # Servivano a leggere le misure; alla costruzione darebbero solo
        # penne tecniche contate male, un nero deciso sulle scritte della
        # legenda, una colata misurata sulla pastiglia del cartiglio.
        clean, lastre = artwork.senza_coperture(
            pdf, extra=list(lastre_extra) + materiali.da_togliere(lettura),
            regione=fpk.foglio_in_pagina(fp0), conti=conti)
    # la lettura del PDF, da mettere accanto al modello (`pack3d.lettura`):
    # accanto al GLB, dove il server la va a prendere. Mai un errore: se non
    # si disegna, il modello si costruisce lo stesso
    scrivi_lettura(out_glb, lambda: lettura_pdf.flowpack(pdf, fp0, gradi))
    # Il nero sul file pulito, prima di rendere: vedi `nero.spia`. Sugli
    # Spaces la memoria per il fork di Ghostscript c'e'.
    deciso_nero = nero.spia(clean, 0, dpi / 72.0)

    # NB: l'UnboundLocalError su 'avvisi' non nasceva qui. Nasceva in
    # do_POST, che quel nome lo assegnava solo sul ramo flowpack e lo
    # leggeva su tutti e due. Legare 'avvisi' dentro questa funzione non
    # tocca l'altra: sono due scope diversi, e qui il nome non si rilegge
    # mai. La correzione vera sta nel chiamante.
    avvisi_sez = []
    # l'analisi com'e' uscita dal DT, prima che la sezione dell'agente la
    # cambi: e' su questa che si controlla il fronte
    analisi = fp0 if case is None else None
    pagine = avviso_pagine(n_pagine)
    if pagine:
        avvisi_sez.append(pagine)
    if giro:
        avvisi_sez.append(giro)
    fuori = artwork.avviso_fuori_dt(conti)
    if fuori:
        avvisi_sez.append(fuori)
    avvisi_sez.extend(artwork.avvisi_gda(conti))
    rgb = avviso_quadricromia(clean, regione=fpk.foglio_in_pagina(fp0))
    if rgb:
        avvisi_sez.append(rgb)
    # Quello che l'analisi ha da dire - testate dal DT, steso ruotato,
    # rientri diversi - finiva nel Flowpack e da li' da nessuna parte.
    avvisi_sez.extend(fp0.warnings)
    if lastre:
        avvisi_sez.append("lastre tecniche e coperture tolte per nome: %s"
                          % ", ".join(lastre))
    avvisi_sez.extend(note_mat)
    # I ruoli letti dall'AI tornano a chi chiama: un caso che va in coda li
    # porta con se', e la routine, che costruisce senza AI, rifa' lo stesso
    # modello. Quelli dal nome o dal titolo li ritrova da sola.
    if materiali_ai is not None and lettura is not None:
        materiali_ai.update({n: v["ruolo"] for n, v in lettura.lastre.items()
                             if v["fonte"] == "ai" and v["ruolo"]})
    sospetto = falda_sospetta(fp0)
    if sospetto:
        avvisi_sez.append(sospetto)
    if ripiego is not None:
        avvisi_sez.append("ANALISI AUTOMATICA FALLITA (%s): ripiego sul "
                          "solutore vecchio, quote e grafica da verificare"
                          % ripiego[:70])
    if sezione:
        # Dall'agente il RAPPORTO, dal film il PERIMETRO. Il perimetro la
        # fustella lo misura bene e non si tocca; e' il rapporto che non sa
        # dare, perche' 50 x 11 e 41 x 20 hanno lo stesso perimetro e la
        # differenza sta nel prodotto dentro, non nel disegno.
        w_a, t_a = sezione
        t_n = fp0.girth / (2.0 * (1.0 + w_a / t_a))
        w_n = fp0.girth / 2.0 - t_n
        avvisi_sez.append("sezione dall'analisi AI: %.1f x %.1f, riportata sul "
                          "perimetro del film come %.1f x %.1f"
                          % (w_a, t_a, w_n, t_n))
        # E la cucitura si sposta di meta' della differenza. Il film non si
        # allunga: dal centro del fronte alla cucitura ci sono gli stessi
        # millimetri di film comunque si riempia il pack, quindi se il fronte
        # chiuso e' piu' stretto della fascia del DT la cucitura sul retro si
        # avvicina allo spigolo di (W - W')/2 - 4,5 mm sul croccante T2, 50 x 11
        # sulla fustella e 41 x 20 in mano. Tenendo fermo `back_a` i nodi del
        # giro sommavano a W + W' + 2T' invece che al perimetro, e il riscalo
        # che li riporta sul giro stirava la grafica fra un nodo e l'altro. Il
        # centro del fronte no: li' il riscalo compensa, e la verifica del
        # fronte lo dava gia' a posto anche prima.
        #
        # Su un tubo piatto a pinna la sezione il DT non la dice proprio: se
        # l'agente la da', il pack ha i suoi fianchi, e non e' piu' piatto.
        sposta = (fp0.W - w_n) / 2.0
        fp0 = replace(fp0, W=round(w_n, 2), T=round(t_n, 2),
                      back_a=round(max(fp0.back_a - sposta, 0.5), 2),
                      back_b=round(max(fp0.back_b - sposta, 0.5), 2),
                      piatto=False)

    # (1) la sezione si arrotonda a perimetro costante
    liv = FASCE.get(str(soft).strip().lower(), None)
    if liv is None:
        try:
            liv = float(soft)
        except (TypeError, ValueError):
            # "auto" o valore non riconosciuto: se l'agente ha gia' deciso usa
            # la sua scelta, altrimenti il centro scala
            liv = 5.0
    # Il rigonfiamento cambia la FORMA, non la taglia: il film che c'e' nello
    # steso e' quello, e gonfiare non ne aggiunge. Le due chiusure pero'
    # partono da forme diverse, e la scala vuol dire cose diverse: qui sotto
    # la pinna, in fondo la sovrapposizione.
    liv = max(1.0, min(10.0, liv))
    # a pinna il rigonfiamento nello spessore, se e' stato scelto per il pack
    fp = replace(fp0, nello_spessore=bool(nello_spessore))
    if fp0.tubo_piatto:
        # Un tubo piatto non ha un rapporto larghezza/spessore da tenere fermo:
        # gonfiandosi passa dalla lente al cerchio, e il cerchio e' il massimo
        # fisico - con quel film non si puo' essere piu' tondi. Il livello dice
        # quanto ci si avvicina, in frazione del diametro del cerchio.
        #
        # La scala e' tarata sul GLB di riferimento del wafer T1, che e'
        # l'unica misura che abbiamo per questa famiglia: sezione a ellisse di
        # rapporto 1,466 e bbox 26,7 x 18,2 su un giro di 71, cioe' 0,806 del
        # diametro del cerchio. Il livello 5 ci cade sopra.
        #
        # La scala e' volutamente STRETTA - da 1,85 di rapporto a 1,00 - e non
        # copre i wrap davvero piatti: allargarla vorrebbe dire inventare
        # numeri che nessun pack misurato conferma, e spostare il centro della
        # scala via dall'unico riferimento che c'e'. Il giorno che arriva un
        # pack piatto a sovrapposizione, si allarga con quello in mano.
        n_sez = SEZ_ELLISSE
        scala = 1.0
        pienezza = PILLOW_LENTE + (PILLOW_CERCHIO - PILLOW_LENTE) * (liv - 1) / 9.0
        # Lo spessore va messo DENTRO il Flowpack, non passato a parte: a
        # valle fp.T lo usano le nervature delle ganasce, l'apertura delle
        # pinne e i cartellini. Con T a zero la nervatura divide per la
        # protezione da zero e la mesh esplode - misurato: vertici a
        # cinque milioni di millimetri. La proprieta' `girth` non ne soffre,
        # perche' su un tubo piatto il giro lo da' il nastro, meno il lembo a
        # sovrapposizione o le due fasce della pinna.
        fp = replace(fp, T=round(pienezza * fp0.girth / math.pi, 2))
        avvisi_sez.append("tubo piatto gonfiato al %.0f%% del cerchio "
                          "(livello %g)" % (100.0 * pienezza, liv))
    else:
        # A pinna la sezione va dal rettangolo teso sul prodotto all'ellisse
        # piena d'aria, tenendo fermi il rapporto larghezza/spessore MISURATO
        # nello steso e il perimetro del film. La scala che serve a tornare sul
        # perimetro gonfia il pack in entrambe le direzioni.
        n_sez = SEZ_RETTANGOLO + (SEZ_ELLISSE - SEZ_RETTANGOLO) * (liv - 1) / 9.0
        scala = fpk.sezione_rigonfiata(fp, n_sez)
    if scatola:
        # Il riscalo a perimetro costante dice che una forma piu' tonda, con lo
        # stesso film, e' piu' grande: vale quando dentro c'e' aria. Con una
        # scatola la sezione la detta la scatola, e i pochi millimetri che la
        # superellisse taglia agli spigoli se li prende la piega, non il pack.
        # Senza questo la brioche usciva 155,9 x 59,7 invece di 148,9 x 57,0.
        scala = 1.0
    # superellipse_section torna il SEMIASSE, non la larghezza come faceva
    # soft_section_fit: senza il raddoppio width_end esce doppio e le pinne si
    # aprono fino al perimetro intero invece che a meta'
    # Quanto misura la fustella oltre il corpo — 37,5 mm sulla brioche — non e'
    # tutto pinna. Prima il tubo deve collassare, e la gola piegata sullo
    # spigolo costa mezzo spessore; quello che avanza e' la pinna vera. Con una
    # scatola dentro il collasso non puo' mangiare il corpo, perche' la scatola
    # tiene la sezione fino alla sua faccia: la gola sta tutta oltre. Sul
    # brioche: 37,6 = 22,8 di gola piu' 14,8 di pinna, vedi GOLA_SU_SPESSORE.
    # La somma L/2 + end_fin non cambia, quindi le UV restano quelle e la
    # grafica non si sposta di un pixel.
    #
    # Ma solo se la gola non la dice gia' il DT. Quando disegna la saldatura
    # E dove finisce il prodotto, la testata e' gia' divisa: la pinna finisce
    # alla saldatura, la gola sta fra lei e il prodotto, e il corpo la
    # comprende. Sul wafer da colazione T10 le quote del file sono 20 | 37,5 |
    # 215 | 37,5 | 20: corpo 290 con la gola, pinna 20. Dividendo la pinna
    # un'altra volta ne restavano 2 mm, e il pack usciva una scatola senza
    # pinne con la grafica delle testate stirata di 2,07 volte.
    gola = 0.0
    if scatola and fp0.gola > 0:
        gola = fp0.gola
        avvisi_sez.append("oltre la scatola %.1f mm: %.1f di gola piu' %.1f di "
                          "pinna, come li disegna il DT"
                          % (fp0.gola + fp0.end_fin, gola, fp.end_fin))
    elif scatola:
        gola = min(GOLA_SU_SPESSORE * fp0.T, max(fp0.end_fin - 2.0, 0.0))
        fp = replace(fp, L=round(fp0.L + 2.0 * gola, 2),
                     end_fin=round(fp0.end_fin - gola, 2))
        avvisi_sez.append("oltre la scatola %.1f mm: %.1f di gola piu' %.1f di "
                          "pinna" % (fp0.end_fin, gola, fp.end_fin))

    Ps, d, semiasse = fpk.superellipse_section(fp, n_sez, thickness=scala * fp.T)
    sw = 2.0 * semiasse
    G = d[-1]
    # Quanto si apre la pinna, su una scala di tre.
    #
    # Un tubo si appiattisce perche' dentro c'e' aria, e appiattito misura meta'
    # perimetro: quello e' il massimo geometrico, oltre il quale il film
    # dovrebbe allungarsi. E' il caso del T1 della barretta fresca, pinne aperte e piu'
    # alte del pack, ed e' il 3. All'altro capo, quando il film avvolge una
    # scatola che arriva fino alla saldatura, non c'e' niente da appiattire: la
    # pellicola si ripiega sugli spigoli e la pinna esce larga esattamente
    # quanto la faccia. E' la brioche, ed e' l'1. Il 2 sta in mezzo.
    #
    # Non e' deducibile dal rigonfiamento: dice come si comporta il film alle
    # ganasce, non che forma prende il corpo.
    ap = pinne if pinne is not None else (1.0 if scatola else 3.0)
    ap = max(1.0, min(3.0, float(ap)))
    fin_open = sw + (FIN_OPEN_RATIO * G / 2.0 - sw) * (ap - 1.0) / 2.0
    if ap < 3.0:
        avvisi_sez.append("apertura pinne %g/3: bordo %.1f mm contro i %.1f di "
                          "meta' perimetro" % (ap, fin_open, G / 2.0))
    if scatola and liv > 3:
        avvisi_sez.append("rigonfiamento %g su un pack che avvolge una "
                          "scatola: di norma e' 1" % liv)

    # Dove il tubo comincia a schiacciarsi. Con una scatola dentro lo decide
    # la gola; se no, prima il DT - la zona fra la saldatura e la fine del
    # prodotto, quando la segna uguale dai due lati - e solo dove tace la
    # regola di sempre, mai piu' corta della pinna.
    rastremo = gola if scatola else (fp0.gola or max(fp0.end_fin, 6.0))
    # E la spalla deve starci col film. Dalla sezione piena alla saldatura il
    # tubo cala di mezzo spessore, e il film, che non si allunga, quel calo lo
    # copre solo se la spalla e' abbastanza lunga: sul T1 farcito la gola del
    # DT e' 10 mm e il calo 14,1, e dieci millimetri di film su una discesa
    # di quattordici sono una grafica stirata fino a 3,7 volte - la scritta
    # LATTE del bollino. Allora la spalla comincia prima, dentro il prodotto,
    # come fa un prodotto morbido che il film tira giu' sugli spigoli: la
    # saldatura resta dov'e' e con lei tutte le linee del DT. Con una scatola
    # no: li' la sezione la tiene la scatola fino alla sua faccia.
    # sulla pinna saldata resta, dello spessore, solo il filo fra i due strati
    flat_end = min(1.0, PINNA_SALDATA_MM / max(0.5 * scala * fp.T, 1e-6))
    calo = 0.5 * scala * fp.T * (1.0 - flat_end)
    spalla = rastremo
    # mai oltre meta' del mezzo corpo: una sezione piena deve restare
    voluta = min(SPALLA_SU_CALO * calo, fp.L / 4.0)
    if not scatola and voluta > rastremo + 0.5:
        spalla = round(voluta, 1)
        avvisi_sez.append("spalla di %.1f mm invece di %.1f: il tubo cala di "
                          "%.1f mm fino alla saldatura e il film, che non si "
                          "allunga, lo copre solo cosi'; la spalla comincia "
                          "%.1f mm dentro il prodotto"
                          % (spalla, rastremo, calo, spalla - rastremo))
    # (2) mappatura per pannello: gli spigoli della sezione fanno da nodi. Si
    # calcolano prima della mesh perche' servono anche a lei: nella gola e
    # nella pinna il giro si rimisura sul film, e il film lo dicono i nodi.
    knots = _panel_knots(Ps, d, G, fp0)
    spigoli = knots
    if knots and fp.nello_spessore and not fp0.tubo_piatto:
        # Gonfio nello spessore gli spigoli servono solo alla verifica: la
        # grafica sta sul giro alla sua distanza dal centro del fronte, dove
        # la mette la cucitura (`superellipse_section`). Portare le pieghe
        # stampate sugli spigoli stirava le fasce: il flowpack 30 x 12 al
        # livello 9 ha gli spigoli a 14,5 | 27,5 | 14,5 contro i pannelli
        # 12 | 30 | 12, il fronte stretto dell'8% e i fianchi stirati del 21%.
        knots = (list(knots[1]), list(knots[1]))
    saldatura = max(0, min(3, int(saldatura)))
    # Dopo la griglia (righe di nv + 1 vertici, le prime `ng`, e i suoi `tg`
    # triangoli) c'e' il bordo dentato: chi rilegge la mesh a righe guarda
    # solo la griglia.
    V, UV, T, ng = fpk.build_mesh(
        fp, nu=nu, nv=nv, sec_exp=n_sez, sec_thickness=scala * fp.T,
        width_end=fin_open / sw,
        taper=spalla, flat_end=flat_end, flare_pow=3.0, soft=True,
        serration=teeth > 0, serr_teeth=max(int(teeth), 1),
        fin_stations=36 if quality == "alta" else 26,
        bulge=par["bulge"], crimp_period=1.4,
        crimp_mm=NERVATURA_MM * saldatura / 3.0,
        wrinkle_mm=par["wrinkle_mm"], giro=_giro_film(knots, G, fp0),
        spalla_sul_film=True, griglia=True)
    tg = 2 * (ng // (nv + 1) - 1) * nv
    v_denti = UV[ng:, 1].copy()

    if spigoli:
        ks, kf = spigoli
        # La regola dice di verificare il modello mappato contro l'AW con una
        # misura, fascia per fascia, prima di finalizzare. Qui si puo' fare da
        # soli: lo scarto fra dove cade lo spigolo sulla sezione e dove lo
        # vuole la fasciatura dello steso. Simmetrico e piccolo e' la
        # superellisse che taglia lo spigolo, ed e' fisiologico; sbilanciato o
        # grande vuol dire grafica che scivola attorno al tubo.
        # Due cose diverse dentro gli stessi numeri. Gli scarti a segni
        # alterni sono la superellisse che taglia gli spigoli: il film sopra
        # l'arrotondamento appartiene un po' al fianco e un po' al retro, e
        # l'interpolazione qui sotto lo sistema. Uno scarto tutto dallo stesso
        # lato invece e' una ROTAZIONE dell'origine, cioe' grafica che scivola
        # attorno al tubo, e l'interpolazione non la puo' correggere perche'
        # le sposta anche i riferimenti. La media distingue i due casi.
        scarti = [a - b for a, b in zip(ks, kf)]
        rotazione = abs(sum(scarti) / len(scarti))
        peggio = max(abs(s) for s in scarti)
        if rotazione > 0.01 * G:
            avvisi_sez.append("GRAFICA RUOTATA di %.1f mm sul giro di %.1f: "
                              "controlla la cucitura" % (rotazione, G))
        else:
            avvisi_sez.append("mappatura verificata: rotazione %.1f mm, spigoli "
                              "entro %.1f mm su un giro di %.1f"
                              % (rotazione, peggio, G))
        ks, kf = knots
        UV[:, 1] = np.interp(UV[:, 1] * G, ks, kf) / G
    UV = fpk.remap_to_sheet(UV, fp)
    # il film sulle testate: pinne e spalle non sono un piano, e la grafica ci
    # deve cadere come ci cade il film. Dopo i nodi e il riporto sullo steso,
    # perche' e' il film vero che si misura.
    dente = fpk.altezza_dente(fin_open / max(int(teeth), 1)) if teeth > 0 else 0.0
    avvisi_sez.append(verifica.testate_flowpack(V[:ng], UV[:ng], T[:tg], fp,
                                                spalla, dente, ap >= 3.0)[1])
    # PRIMA della mappatura: le UV sono il DT steso, e se le testate non
    # cadono sulle sue linee la grafica andra' fuori posto comunque la si
    # mappi. E le misure del disegno contro le quote che il file scrive.
    #
    # Anche per un caso tarato a mano: le sue misure sono state prese una
    # volta, su quel file, e il DT e' ancora li' per confermarle. Le linee
    # vengono dall'analisi del disegno; se il disegno non si legge - ed e'
    # spesso il motivo per cui un caso e' stato tarato - lo si dice.
    linee = fp0
    if case is not None:
        try:
            _box, linee, _rip = analisi_flowpack(pdf)
        except Exception:
            linee = None
    if linee is not None:
        avvisi_sez.append(verifica.uvw_flowpack(linee, fp, rastremo, scatola,
                                                spalla)[1])
    else:
        avvisi_sez.append("UVW contro il DT: il disegno di questo file non si "
                          "legge in automatico, le testate sono quelle del "
                          "caso tarato: da controllare sulla miniatura")
    riscontro = quotature.riscontro_testate(pdf, fp0.step_mm,
                                            fp0.end_fin, fp0.gola)
    if riscontro:
        avvisi_sez.append(riscontro)
    # e la miniatura, che e' il riscontro quando le quote sono in curve: sul
    # DT come l'ha letto l'analisi, non sulla sezione ritoccata dall'agente
    letto = analisi if case is None else linee
    miniatura = (quotature.riscontro_miniature(pdf, letto)
                 if letto is not None else None)
    if miniatura:
        avvisi_sez.append(miniatura)

    grid = V[:ng].reshape(-1, nv + 1, 3)
    # (4) le pinne restano saldate e piatte: nessuna manipolazione dei lembi.
    # Quello che le rende "aperte" e' che il loro bordo e' PIU' ALTO della
    # sezione del pack, e a questo pensa width_end.

    if fp.pillow:
        # a sovrapposizione non c'e' niente da appoggiare sul retro: il lembo
        # sta SOTTO l'altro bordo, quindi non si vede e non si modella. Una
        # falda a spessore zero uscirebbe come una lamina degenere.
        Vm, UVm, Tm = V, UV, T
    else:
        V2, UV2, T2 = fin_on_surface(grid, fp, G, nv, gap=0.5, fade=10.0,
                                     u_tubo=UV[:ng].reshape(-1, nv + 1, 2)[:, :, 0])
        UV[ng:] = fpk.falda_sui_denti(UV[ng:], v_denti, fp, G, nv)
        Vm = np.vstack([V, V2])
        UVm = np.vstack([UV, UV2])
        Tm = np.vstack([T, T2 + len(V)])
    if _normals(Vm, Tm)[int(np.argmax(Vm[:, 2]))][2] < 0:
        Tm = Tm[:, [0, 2, 1]]

    # lo steso analizzato trasposto si ritaglia dal rettangolo vero della
    # pagina, e la texture va poi rimessa nello stesso telaio della UV, con il
    # perimetro sulle righe
    sh = fpk.foglio_in_pagina(fp)
    # Rasterizzare piu' fine di quanto write_glb_mesh poi terra' vuol dire
    # produrre pixel per buttarli. Il dpi si abbassa fino a quello che serve
    # davvero, mai piu' in su di quello chiesto - quindi sui fogli che stanno
    # sotto il lato massimo, cioe' quasi tutti in HD, non cambia niente.
    lato_pt = max(sh[2] - sh[0], sh[3] - sh[1])
    dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
    tex = folding.rasterize_panels(
        clean, {"film": Panel(sh[0], sh[1], sh[2], sh[3], "film")},
        dpi=dpi_tex, inset_px=0, clean=True,
        note=avvisi_sez, nero_deciso=deciso_nero,
        colata_riquadro=colata_riquadro)["film"]
    foglio = tex
    # Il materiale, nel telaio dello steso com'e' uscito: le copie del DT
    # stanno sulla tavola come lui. Solo se cambia davvero qualcosa - sul
    # T1 ai cereali alluminio e white plate coprono la stessa parte del
    # film, e il metallo non resta da nessuna parte.
    colore, mr = tex, None
    if lettura is not None and lettura.applicabile():
        try:
            mas = materiali.maschere(pdf, lettura, foglio.size)
            colore, mr, q_met, q_opa = materiali.mappe_pbr(foglio, mas)
            if materiali.con_effetto(q_met, q_opa):
                avvisi_sez.append(materiali.riga(lettura, q_met, q_opa))
            else:
                colore, mr = tex, None
                avvisi_sez.append(materiali.riga(lettura, 0, 0)
                                  + ": il film resta plastica")
        except Exception as e:
            traceback.print_exc()
            colore, mr = tex, None
            avvisi_sez.append("materiali dai DT non applicati (%s): il film "
                              "resta plastica" % e)
    if fp.ruotato:
        # rotazione, non trasposizione: trasporre e' una riflessione e
        # specchierebbe la grafica. Di 270 perche' e' il verso che lascia il
        # perimetro crescente come lo intende girth_span.
        stessa = colore is tex
        tex = tex.transpose(Image.ROTATE_270)
        colore = tex if stessa else colore.transpose(Image.ROTATE_270)
        if mr is not None:
            mr = mr.transpose(Image.ROTATE_270)
    # DOPO la mappatura: il fronte dell'AW sul fronte del modello. Il fronte
    # e' quello del DT, cioe' dell'analisi: se l'agente ha cambiato la sezione
    # e' proprio lo spostamento che si vuole vedere.
    avvisi_sez.append(verifica.fronte_flowpack(
        V[:ng], UV[:ng], nv, analisi if analisi is not None else fp0,
        tex, foglio, dpi_tex / 72.0)[1])
    # Il modello finito si gira attorno alla normale del fronte perche' il
    # marchio si legga orizzontale e dritto: il tubo si costruisce coricato,
    # e su uno steso col testo attraverso il passo il pack sta in piedi.
    # Dopo le verifiche, che il giro attorno al fronte non tocca: il centro
    # del fronte resta al centro e la sua normale davanti.
    marchio = verifica.giro_del_marchio(
        V[:ng], UV[:ng], nv, analisi if analisi is not None else fp0, verso_fronte)
    if marchio:
        Vm = verifica.gira_attorno_al_fronte(Vm, marchio)
        avvisi_sez.append(
            "modello girato di %d gradi attorno al fronte perche' il marchio "
            "si legga orizzontale e dritto%s" % (
                marchio, ": il pack sta in piedi, con le pinne in alto e in "
                "basso" if marchio in (90, 270) else ""))
    # La texture e' lo steso del PDF (`pack3d.steso`): il film nel verso in
    # cui sta sul foglio. Il film coricato si e' girato di 90 gradi orari
    # (ROTATE_270), e il foglio di lavoro di `gradi`: tornano indietro tutti
    # e due, con le UV e la mappa del metallo.
    colore, UVm, mr = lo_steso.nel_verso_del_pdf(
        gradi + (90 if fp.ruotato else 0), colore, UVm, mr)
    exporters.write_glb_mesh(Vm, UVm, Tm, colore, out_glb, tex_max=tmax, mr=mr)
    # a modello finito, la grafica del fronte: troppo stirata e' un DIFETTO
    with open(out_glb, "rb") as fh:
        avvisi_sez += verifica.grafica_flowpack(fh.read())

    base = fin_open / max(int(teeth), 1)
    if fp.pillow:
        sez = ("sezione a ellisse %.1f x %.1f (giro %.1f invariato, lembo "
               "coperto %.1f)" % (2.0 * semiasse, fp.T, G,
                                  fp.sovrapposizione))
    elif fp.piatto:
        sez = ("sezione a ellisse %.1f x %.1f (giro %.1f invariato, pinna "
               "%.1f sul retro)" % (2.0 * semiasse, fp.T, G, fp.side_fin))
    else:
        sez = ("sezione %.1f x %.1f (perimetro %.1f invariato%s)"
               % (sw if fp.nello_spessore else scala * fp.W, scala * fp.T, G,
                  ", gonfio nello spessore" if fp.nello_spessore else ""))
    return ["flowpack%s, rigonfiamento %s"
            % (" a sovrapposizione" if fp.pillow else
               " a tubo piatto" if fp.piatto else "", soft), sez,
            "corpo %.1f mm, pinne %.1f" % (fp0.L, fp.end_fin),
            ("pinne lisce" if teeth == 0 else
             "%d denti smussati, base %.2f altezza %.2f mm (2/3 "
             "dell'equilatero)" % (teeth, base, fpk.altezza_dente(base))),
            "saldatura delle pinne %d/3%s" % (
                saldatura, ": senza nervature" if saldatura == 0 else ""),
            "mappatura sul film, dal centro del fronte"
            if knots and fp.nello_spessore and not fp0.tubo_piatto else
            "mappatura per pannello" if knots else "mappatura per arco"] + avvisi_sez


def _giro_film(knots, G, fp):
    """Nodi e larghezze di fronte e retro, sul film, per `build_mesh`.

    Le larghezze vengono dai nodi stessi, che sono gia' riportati sul giro
    della sezione: prese dal Flowpack sarebbero in un'altra scala appena il
    perimetro della fasciatura non torna al decimo con quello della sezione.
    """
    if not knots:
        tot = fp.W + 2.0 * fp.T + fp.back_a + fp.back_b
        s = G / tot if tot > 0 else 1.0
        return None, None, fp.W * s, (fp.back_a + fp.back_b) * s
    ks, kf = knots
    if len(kf) == 4:        # tubo piatto: cucitura, piega, piega, cucitura
        return ks, kf, kf[2] - kf[1], kf[1] + (G - kf[2])
    return ks, kf, kf[3] - kf[2], kf[1] + (G - kf[4])


def _panel_knots(Ps, d, G, fp):
    """Spigoli della sezione, per far cadere ogni fascia sul suo pannello."""
    if fp.tubo_piatto:
        # Un'ellisse non ha spigoli, quindi la ricerca per curvatura qui sotto
        # non trova niente e la verifica non scattava: la grafica poteva
        # ruotare attorno al tubo senza che nessuno se ne accorgesse. I nodi
        # di un tubo piatto sono le due PIEGHE, cioe' gli estremi dell'asse
        # maggiore, e lo steso dice dove devono cadere: a back_a dalla
        # cucitura e a back_a + fronte.
        #
        # Nell'ordine in cui le incontra il film: prima la piega a +y, a
        # back_a dalla cucitura, poi l'altra mezzo giro dopo. Ordinarle per
        # valore sbagliava quando il retro sta tutto da un lato - il T1 al
        # cioccolato fresco - e la cucitura cade sulla seconda piega: quella veniva a
        # zero, prima dell'altra, e il fronte finiva sul retro.
        try:
            ia = int(np.argmax(Ps[:-1, 0]))
            ib = int(np.argmin(Ps[:-1, 0]))
            da, db = float(d[ia]), float(d[ib])
            if db <= da:
                db += G
            ks = [0.0, da, min(db, G), G]
            kf = [0.0, fp.back_a, fp.back_a + fp.W, fp.back_a + fp.W + fp.back_b]
            if kf[-1] <= 0:
                return None
            return ks, [x * G / kf[-1] for x in kf]
        except Exception:
            return None
    try:
        t = np.gradient(Ps, axis=0)
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        cr = np.abs(np.arctan2(t[:-1, 0] * t[1:, 1] - t[:-1, 1] * t[1:, 0],
                               (t[:-1] * t[1:]).sum(1))) / np.maximum(np.diff(d), 1e-9)
        hot = cr > cr.max() * 0.25
        groups, cur = [], []
        for i, h in enumerate(hot):
            if h:
                cur.append(i)
            elif cur:
                groups.append(cur); cur = []
        if cur:
            groups.append(cur)
        if len(groups) != 4:
            return None
        mid = sorted(float(np.average(d[g], weights=cr[g])) for g in groups)
        ks = [0.0] + mid + [G]
        kf = [0.0, fp.back_a, fp.back_a + fp.T, fp.back_a + fp.T + fp.W,
              fp.back_a + 2 * fp.T + fp.W, fp.back_a + 2 * fp.T + fp.W + fp.back_b]
        if kf[-1] <= 0:
            return None
        kf = [x * G / kf[-1] for x in kf]
        return ks, kf
    except Exception:
        return None


def _dice_film(pdf):
    """Il file dice da se' di essere un film da flowpack?

    Il cartiglio Artworkr del cliente lo scrive nella descrizione - "T1 0018 |
    WRAPPING/FILM" - e il disegno tecnico di un film ha FASCIA e PASSO, cioe'
    nastro e passo. Su tutti i file che abbiamo, WRAPPING lo porta ogni
    flowpack e nessun astuccio.
    """
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        try:
            testo = doc[0].get_textpage().get_text_range().upper()
        finally:
            doc.close()
    except Exception:
        return False
    return "WRAPPING" in testo or ("FASCIA" in testo and "PASSO" in testo)


def _analisi_flowpack_dichiarata(pdf, esigente=False):
    """I cartellini del flowpack. Con `esigente` fallisce invece di ripiegare
    sul solutore vecchio: e' la prova che si fa prima dell'astuccio, e un
    ripiego li' vorrebbe dire scegliere la famiglia su una lettura muta."""
    pdf, _gradi, giro, _verso = flowpack_sulla_grafica(pdf)
    _box, fp, ripiego = analisi_flowpack(pdf)
    if esigente and ripiego is not None:
        raise ValueError("flowpack non risolto: %s" % ripiego)
    meta = ["flowpack", "nastro %.0f x passo %.0f mm" % (fp.web_mm, fp.step_mm),
            "corpo %.1f mm" % fp.L]
    if giro:
        meta.append(giro)
    if fp.pillow:
        # a sovrapposizione la sezione non c'e' nello steso: il tubo e' piatto
        # e la forma che prende gonfiandosi la decide il rigonfiamento. Quello
        # che lo steso dice davvero e' giro, fronte e lembo coperto.
        meta.append("tubo piatto: giro %.1f, fronte %.1f, lembo coperto %.1f mm"
                    % (fp.girth, fp.W, fp.sovrapposizione))
    elif fp.piatto:
        # lo stesso, chiuso a pinna: giro, fronte e le due fasce della pinna
        meta.append("tubo piatto a pinna: giro %.1f, fronte %.1f, pinna %.1f mm"
                    % (fp.girth, fp.W, fp.side_fin))
    else:
        meta.append("sezione %.1f x %.1f mm" % (fp.W, fp.T))
    sospetto = falda_sospetta(fp)
    if sospetto:
        # prima di costruire, non dopo: qui l'utente le quote le sta leggendo
        meta.insert(0, sospetto)
    rgb = avviso_quadricromia(pdf, regione=fpk.foglio_in_pagina(fp))
    if rgb:
        meta.insert(0, rgb)
    if ripiego is not None:
        # anche qui il ripiego si dichiara: questi cartellini sono la prima
        # cosa che l'utente legge, e finora tacevano
        meta.insert(0, "ANALISI AUTOMATICA FALLITA (%s): quote dal solutore "
                       "vecchio, da verificare" % ripiego[:70])
    return dict(kind="flowpack", title="Flowpack",
                teeth_default=20, soft_default="medio", meta=meta)


# Tubo piatto a sovrapposizione: quanto e' spessa la sezione in frazione del
# diametro del cerchio, ai due estremi della scala di rigonfiamento. Il cerchio
# e' il massimo fisico: con quel film non si puo' essere piu' tondi. Il valore
# al livello 1 viene dalla taratura sul wafer T1, che al livello 5 deve
# uscire con rapporto 1,466 come il suo GLB di riferimento.
PILLOW_LENTE = float(os.environ.get("PACK3D_PILLOW_LENTE", "0.65"))
PILLOW_CERCHIO = float(os.environ.get("PACK3D_PILLOW_CERCHIO", "1.0"))

# esponente della superellisse ai due estremi della scala di rigonfiamento:
# alto = rettangolo (film teso sul prodotto), 2 = ellisse (pack pieno d'aria)
SEZ_RETTANGOLO = float(os.environ.get("PACK3D_SEZ_RIGIDO", "10"))
SEZ_ELLISSE = float(os.environ.get("PACK3D_SEZ_MORBIDO", "2"))

# quanto il bordo della pinna sfrutta meta' perimetro: 1.0 e' il massimo fisico
FIN_OPEN_RATIO = float(os.environ.get("PACK3D_FIN_OPEN", "1.0"))
# Quanto del film oltre il corpo se lo mangia la gola, in frazione di spessore.
# Il limite geometrico e' 0,5: la gola piegata a 45 gradi sullo spigolo costa
# mezzo spessore. Sul pack vero pero' una parte di quel film si ripiega di lato
# come orecchia invece di accorciare la pinna, quindi la frazione utile e' piu'
# bassa. 0,40 e' quella che riproduce le foto della brioche: 37,6 = 22,8 di gola
# piu' 14,8 di pinna. Tarata su un pack solo.
GOLA_SU_SPESSORE = float(os.environ.get("PACK3D_GOLA", "0.40"))
# La spalla, fuori dalla scatola, lunga almeno tante volte il calo del tubo
# dalla sezione piena alla saldatura. Con la rampa morbida della mesh il punto
# piu' ripido ha pendenza 1,87 volte il calo sulla lunghezza: a 1,7 e' 1,1,
# cioe' 48 gradi, e il film ci si stende stirato di 1,2 in modo uniforme
# (misurato sul bollino del T1 farcito: era 2,5 in media e 3,7 di punta).
SPALLA_SU_CALO = float(os.environ.get("PACK3D_SPALLA", "1.7"))
# La pinna e' saldata: i due strati del film si toccano. Fra le loro facce si
# lasciano pochi centesimi di millimetro, quanto basta perche' un viewer che
# disegna anche le facce posteriori non le confonda. Prima restava il 3,5%
# del mezzo spessore, quasi un millimetro sul pane ripieno piu' le nervature che
# spingevano i due strati in fuori: la pinna usciva aperta, col bordo doppio.
# E' meta' della distanza fra i due strati, in mm.
PINNA_SALDATA_MM = 0.04
# Le nervature delle ganasce sulla pinna alla saldatura piena (3/3): quanto
# si alza il film sulla cresta. La scala della pagina va da 0 (pinna liscia)
# a 3, e il 3 e' il rigato di prima: tarato sul pane ripieno, al centro della pinna
# le righe hanno lo stesso contrasto (9,4 contro 8,6; con 0,32 mm sull'onda
# fitta erano 14,4).
NERVATURA_MM = 0.15
