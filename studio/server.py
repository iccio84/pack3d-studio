#!/usr/bin/env python3
"""
Backend locale di pack3d studio.

    python server.py            # poi apri http://localhost:8000

Solo libreria standard: serve l'interfaccia e due endpoint che girano la
pipeline `pack3d`. Il PDF arriva come corpo binario grezzo, non come
multipart: dentro un iframe la fetch viene inoltrata con postMessage e una
FormData non e' clonabile, mentre un ArrayBuffer lo e'.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from urllib.parse import quote
import tempfile
import traceback
import threading
from collections import OrderedDict
from dataclasses import replace
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)      # il pacchetto pack3d/ sta accanto a questo file

try:
    import numpy as np
    from PIL import Image
except ImportError as e:                       # messaggio utile, non uno stack trace
    sys.exit("Manca una libreria (%s).\n"
             "Installa con:  pip install -r requirements.txt" % e.name)

from pack3d import dieline as dl, folding, exporters
from pack3d import flowpack as fpk
from pack3d.dieline import Panel, PT2MM
from pack3d.flowpack import Flowpack, fin_on_surface
from pack3d.exporters import _normals

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
        name="FULFIL Chocolate Hazelnut Whip",
        sheet=(481.78, 120.34, 481.78 + 142 / PT2MM, 120.34 + 141 / PT2MM),
        girth_span=(120.34 + 15 / PT2MM, 120.34 + 126 / PT2MM),
        W=36.0, T=19.5, L=116.0, end_fin=13.0, side_fin=15.0,
        back_a=18.0, back_b=18.0, web=141.0, step=142.0,
        fin_open=52.6, teeth=20, soft="morbido",
        drop_seps=["Coldseal", "White", "Stand Blau", "All",
                   "Label_ferrero", "Label_linked"],
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
        # Il ripiego era muto, e un modello costruito da un'analisi peggiore
        # non esce sbagliato: esce plausibile, che e' peggio.
        fp = fpk.analyze(pdf)
        ripiego = str(e)
    with _ANALISI_CHIAVE:
        _ANALISI[imp] = (box, fp, ripiego)
        while len(_ANALISI) > _ANALISI_MAX:
            _ANALISI.popitem(last=False)
        return _ANALISI[imp]


# --------------------------------------------------------------------------- #
# pulizia dell'artwork
# --------------------------------------------------------------------------- #
def strip_separations(src, dst, drop):
    """Toglie le lastre tecniche eliminando le operazioni di disegno.

    Colorarle di bianco non basta: un tratto tecnico sopra la grafica
    lascerebbe una riga bianca. Il filtro scende anche dentro i Form XObject,
    dove spesso stanno cold seal e bianco coprente.
    """
    import pypdf
    from pypdf.generic import ContentStream

    r = pypdf.PdfReader(src)
    w = pypdf.PdfWriter()
    w.append(r)
    drop = {d.lower() for d in drop}

    def names(res):
        out = set()
        cs = res.get("/ColorSpace")
        if not cs:
            return out
        for k, v in cs.get_object().items():
            try:
                o = v.get_object()
                if o[0] == "/Separation":
                    if str(o[1]).lstrip("/").replace("#20", " ").lower() in drop:
                        out.add(str(k))
                elif o[0] == "/DeviceN":
                    nm = [str(x).lstrip("/").replace("#20", " ").lower() for x in o[1]]
                    if nm and all(n in drop for n in nm):
                        out.add(str(k))
            except Exception:
                pass
        return out

    FILL, STROKE = {b"f", b"F", b"f*"}, {b"S", b"s"}
    BOTH = {b"B", b"B*", b"b", b"b*"}

    def filt(obj, res):
        bad = names(res)
        cs = ContentStream(obj, w)
        ncs = scs = None
        out = []
        for ops, op in cs.operations:
            if op == b"cs":
                ncs = str(ops[0])
            elif op == b"CS":
                scs = str(ops[0])
            if op in FILL and ncs in bad:
                out.append(([], b"n")); continue
            if op in STROKE and scs in bad:
                out.append(([], b"n")); continue
            if op in BOTH:
                fd, sd = ncs in bad, scs in bad
                if fd and sd:
                    out.append(([], b"n")); continue
                if fd:
                    out.append((ops, b"S")); continue
                if sd:
                    out.append((ops, b"f")); continue
            if op == b"sh" and ncs in bad:
                continue
            out.append((ops, op))
        cs.operations = out
        return cs

    def walk(res, seen):
        xo = res.get("/XObject")
        if not xo:
            return
        for _, v in xo.get_object().items():
            o = v.get_object()
            if o.get("/Subtype") != "/Form" or id(o) in seen:
                continue
            seen.add(id(o))
            sub = o.get("/Resources")
            if sub is None:
                continue
            o.set_data(filt(o, sub.get_object()).get_data())
            walk(sub.get_object(), seen)

    page = w.pages[0]
    res = page["/Resources"]
    page.replace_contents(filt(page.get_contents(), res))
    walk(res, set())
    with open(dst, "wb") as fh:
        w.write(fh)
    return dst


# --------------------------------------------------------------------------- #
# costruzione
# --------------------------------------------------------------------------- #
# Come si rimette dritta una grafica girata. Il verso e' lo STESSO
# dell'angolo, non l'opposto: pdfium misura l'angolo nello spazio del PDF, con
# la y in su, mentre la texture ha la y in giu', quindi il senso e' gia'
# rovesciato una volta. Verificato guardando le due direzioni affiancate.
GIRO_TEXTURE = {90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}

# Quanto puo' essere lontano da quadrato un pannello perche' girarlo di 90
# gradi non lo stiri. Vedi _gira_sulla_grafica.
QUADRATO = float(os.environ.get("PACK3D_QUADRATO", "0.9"))


def verso_della_grafica(pdf, panels, page_no=0):
    """Di quanto e' girata la grafica in ogni pannello. {} se non lo dice."""
    from pack3d import tracciati
    try:
        return tracciati.verso_grafica(
            pdf, {n: (p.x0, p.y0, p.x1, p.y1) for n, p in panels.items()}, page_no)
    except Exception:
        return {}


def _gira_sulla_grafica(tex, panels, verso):
    """Rimette dritte le texture seguendo la grafica. (fatte, non fatte).

    La regola e' che il modello segue la GRAFICA e non il disegno tecnico: il
    DT dice come e' impaginato il foglio, la grafica dice come si legge il
    pack in mano.

    Un solo limite, e non e' un compromesso: e' l'altra regola, quella che dice
    di non distorcere mai la grafica. Il pannello sul foglio e la faccia sul
    solido hanno le stesse proporzioni - vengono dalla stessa fustella - quindi
    girare la texture di 90 gradi la mappa su una faccia con le proporzioni
    scambiate. Su un pannello quasi quadrato non si vede; su un fianco stretto
    si', ed e' anche il caso in cui girare sarebbe sbagliato: su un fianco da
    38 x 191 il testo verticale E' il progetto, non un errore di impaginato,
    mentre su un pannello da 188 x 191 vuol dire che il foglio e' girato.
    Il rapporto di forma distingue i due casi.

    Dove non si puo' girare senza stirare, non si gira e lo si dichiara: la
    regola dice di seguire la grafica, non di consegnare grafica deformata.
    """
    fatte, no = [], []
    for nome, gradi in sorted(verso.items()):
        if not gradi or nome not in tex:
            continue
        p = panels[nome]
        lati = abs(p.x1 - p.x0), abs(p.y1 - p.y0)
        quadrato = min(lati) / max(max(lati), 1e-9) >= QUADRATO
        if gradi == 180 or quadrato:
            tex[nome] = tex[nome].transpose(GIRO_TEXTURE[gradi])
            fatte.append("%s di %d" % (nome, gradi))
        else:
            no.append("%s (%d gradi, %.0f x %.0f)"
                      % (nome, gradi, lati[0] * PT2MM, lati[1] * PT2MM))
    return fatte, no


def _senza_coperture(pdf, page_no=0):
    """(pdf da cui ritagliare la texture, nomi delle coperture togliute).

    Le lastre tecniche dichiarate per nome sono l'informazione piu' attendibile
    che un file possa dare, dopo i Processing Steps: `REGOLE.md` le mette al
    livello 3-4 dei cinque, sopra l'euristica su spessore e colore. Finora
    pero' le leggeva solo `tools.classify_technical`, che e' uno strumento per
    l'agente: la costruzione deterministica non le guardava, e strappava le
    separazioni solo se un caso calibrato le elencava a mano.

    Il caso che l'ha fatto vedere: su un astuccio Nutella Donut la vernice si
    chiama `Water Based Gloss Varnish` e copre tutto il pannello. pdfium la
    rende opaca, quindi la texture uscirebbe rosa piena. Nessuna euristica su
    spessore e colore la puo' prendere - non e' un tratto sottile, e' un pieno
    grande quanto la grafica - mentre il nome lo dice senza ambiguita'.

    Si strappano solo le COPERTURE - vernice, bianco coprente, cold seal - e
    non tutte le lastre tecniche: vedi techink.COPERTURE_FRASI per il perche',
    che e' misurato in secondi e in MB.

    E si toglie SOLO per la texture, mai per l'analisi: il disegno tecnico e'
    quello che fa misurare il pack, e togliendolo prima non si misura piu'
    niente.
    """
    from pack3d import techink
    try:
        import pypdf
        pagina = pypdf.PdfReader(pdf).pages[page_no]
        lastre = sorted(set(techink.technical_separations(
            pagina, prova=techink.copertura).values()))
    except Exception:
        return pdf, []
    if not lastre:
        return pdf, []
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        return strip_separations(pdf, tmp.name, lastre), lastre
    except Exception:
        # meglio una texture con un residuo tecnico che nessun modello
        return pdf, []


def avviso_quadricromia(pdf, page_no=0):
    """La riga sulla quadricromia, se il file ne ha bisogno.

    Costa una lettura di pypdf e una passeggiata nei dizionari delle risorse:
    centesimi di secondo e niente in memoria, misurati su tutto il parco.
    """
    from pack3d import techink
    try:
        import pypdf
        return techink.avviso_rgb(pypdf.PdfReader(pdf).pages[page_no])
    except Exception:
        return None


def build_carton(pdf, out_glb, quality="web"):
    dpi = 300 if quality == "alta" else 200
    d = dl.analyze(pdf)          # sull'originale: il DT e' quello che misura
    if not d.panels:
        raise ValueError("astuccio riconosciuto ma i pannelli non sono risolvibili")
    pulito, lastre = _senza_coperture(pdf)
    tex = folding.rasterize_panels(pulito, d.panels, dpi=dpi)
    # Il modello segue la GRAFICA, non il disegno tecnico. Il DT dice come e'
    # impaginato il foglio; la grafica dice come si legge il pack in mano, e
    # sono due cose diverse: su questo astuccio il pannello fronte ha tutto il
    # testo a 90 gradi e il retro a 270. Girata la texture, il marchio si legge
    # sul modello come si legge sul pack.
    giri, storti = _gira_sulla_grafica(tex, d.panels,
                                       verso_della_grafica(pulito, d.panels))
    faces = folding.build_faces(d.dims_mm, tex, layout=d.layout,
                                panels=d.panels)
    exporters.write_glb_mesh  # noqa: B018  (import usato sotto per i flowpack)
    exporters.write_glb(faces, out_glb)
    meta = ["astuccio %s%s" % (d.layout, "" if d.chiuso else " aperto"),
            "%.1f x %.1f x %.1f mm" % d.dims_mm]
    rgb = avviso_quadricromia(pdf)
    if rgb:
        meta.insert(0, rgb)
    if lastre:
        meta.append("coperture togliute per nome: %s" % ", ".join(lastre))
    if giri:
        meta.append("girato sul verso della grafica: %s" % ", ".join(giri))
    if storti:
        meta.append("GRAFICA GIRATA ma il pannello non e' quadrato, lasciato "
                    "com'e' per non stirarla: %s" % ", ".join(storti))
    return meta + [w for w in dl.check(d)]


def _flowpack_from_case(case):
    return Flowpack(W=case["W"], T=case["T"], L=case["L"], end_fin=case["end_fin"],
                    side_fin=case["side_fin"], back_a=case["back_a"],
                    back_b=case["back_b"], web_mm=case["web"], step_mm=case["step"],
                    sheet=case["sheet"], girth_span=case["girth_span"])


def sezione_da_agente(params):
    """Larghezza e spessore del pack CHIUSO, se l'agente li ha misurati.

    Le cordonature dicono dove il film e' cordonato, non che forma prende una
    volta riempito: su Kinder Bueno T2 i pannelli danno 50 x 11, ma il pack in
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
#   Milch-Schnitte T1  nastro 144   falda 14,0
#   Kinder Country     nastro 122   falda 16,0
#   Kinder Paradiso    nastro 165   falda 12,5
#   K Brioss T10 Promo nastro 420   falda  4,1
#   FULFIL             nastro 141   falda 15,0
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


def build_flowpack(pdf, out_glb, teeth, soft, case=None, quality="web",
                   sezione=None, scatola=False, pinne=None):
    """Costruisce il flowpack con le tecniche messe a punto sul campo.

    Quattro cose che la versione base non faceva, e che senza si vedono subito:

    1. Gonfiando, la sezione si arrotonda **a perimetro costante**: lo spessore
       cresce e la larghezza cala. Alzare solo lo spessore inventa film.
    2. La grafica si mappa **per pannello**, usando gli spigoli della sezione
       come nodi: con l'arco uniforme ogni fascia scivola.
    3. Le pinne portano la **zigrinatura** a triangoli equilateri, contata sul
       bordo della pinna.
    4. Le pinne non restano **mai a filo**: si aprono a farfalla verso la punta.
    """
    import math
    par = gonfiore(soft)
    nu, nv, dpi, tmax = (320, 420, 300, 2600) if quality == "alta" else (190, 260, 200, 1700)
    if case:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        clean = strip_separations(pdf, tmp.name, case["drop_seps"])
        lastre = list(case["drop_seps"])
        fp0 = _flowpack_from_case(case)
        box = None
        ripiego = None
    else:
        # Stessa analisi di /api/analyze, non una seconda uguale: il ripiego
        # muto (che su Milch-Schnitte T1 dava corpo e pinne 136,5 e 8,0 invece
        # di 138,7 e 6,9, con la grafica che scivolava sul fronte) resta
        # dichiarato, perche' il motivo viaggia insieme alle quote.
        box, fp0, ripiego = analisi_flowpack(pdf)
        # L'analisi e' fatta: ora, e non prima, si possono togliere le lastre
        # tecniche dichiarate per nome.
        clean, lastre = _senza_coperture(pdf)

    # NB: l'UnboundLocalError su 'avvisi' non nasceva qui. Nasceva in
    # do_POST, che quel nome lo assegnava solo sul ramo flowpack e lo
    # leggeva su tutti e due. Legare 'avvisi' dentro questa funzione non
    # tocca l'altra: sono due scope diversi, e qui il nome non si rilegge
    # mai. La correzione vera sta nel chiamante.
    avvisi_sez = []
    rgb = avviso_quadricromia(pdf)
    if rgb:
        avvisi_sez.append(rgb)
    if lastre:
        avvisi_sez.append("coperture togliute per nome: %s" % ", ".join(lastre))
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
        fp0 = replace(fp0, W=round(w_n, 2), T=round(t_n, 2))

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
    fp = fp0
    if fp0.pillow:
        # Un tubo piatto non ha un rapporto larghezza/spessore da tenere fermo:
        # gonfiandosi passa dalla lente al cerchio, e il cerchio e' il massimo
        # fisico - con quel film non si puo' essere piu' tondi. Il livello dice
        # quanto ci si avvicina, in frazione del diametro del cerchio.
        #
        # La scala e' tarata sul GLB di riferimento del K Tronky T1, che e'
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
        # perche' a sovrapposizione il giro lo da' il nastro meno il lembo.
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
        # Senza questo il Brioss usciva 155,9 x 59,7 invece di 148,9 x 57,0.
        scala = 1.0
    # superellipse_section torna il SEMIASSE, non la larghezza come faceva
    # soft_section_fit: senza il raddoppio width_end esce doppio e le pinne si
    # aprono fino al perimetro intero invece che a meta'
    # Quanto misura la fustella oltre il corpo — 37,5 mm sul Brioss — non e'
    # tutto pinna. Prima il tubo deve collassare, e la gola piegata sullo
    # spigolo costa mezzo spessore; quello che avanza e' la pinna vera. Con una
    # scatola dentro il collasso non puo' mangiare il corpo, perche' la scatola
    # tiene la sezione fino alla sua faccia: la gola sta tutta oltre. Sul
    # Brioss: 37,6 = 22,8 di gola piu' 14,8 di pinna, vedi GOLA_SU_SPESSORE.
    # La somma L/2 + end_fin non cambia, quindi le UV restano quelle e la
    # grafica non si sposta di un pixel.
    gola = 0.0
    if scatola:
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
    # dovrebbe allungarsi. E' il caso di Milch-Schnitte, pinne aperte e piu'
    # alte del pack, ed e' il 3. All'altro capo, quando il film avvolge una
    # scatola che arriva fino alla saldatura, non c'e' niente da appiattire: la
    # pellicola si ripiega sugli spigoli e la pinna esce larga esattamente
    # quanto la faccia. E' Kinder Brioss, ed e' l'1. Il 2 sta in mezzo.
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

    V, UV, T = fpk.build_mesh(
        fp, nu=nu, nv=nv, sec_exp=n_sez, sec_thickness=scala * fp.T,
        width_end=fin_open / sw,
        taper=gola if scatola else max(fp0.end_fin, 6.0), flare_pow=3.0, soft=True,
        serration=teeth > 0, serr_teeth=max(int(teeth), 1),
        fin_stations=36 if quality == "alta" else 26,
        bulge=par["bulge"], crimp_period=1.4, crimp_mm=0.32,
        wrinkle_mm=par["wrinkle_mm"])

    # (2) mappatura per pannello: gli spigoli della sezione fanno da nodi
    knots = _panel_knots(Ps, d, G, fp0)
    if knots:
        ks, kf = knots
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
        UV[:, 1] = np.interp(UV[:, 1] * G, ks, kf) / G
    UV = fpk.remap_to_sheet(UV, fp)

    grid = V.reshape(-1, nv + 1, 3)
    # (4) le pinne restano saldate e piatte: nessuna manipolazione dei lembi.
    # Quello che le rende "aperte" e' che il loro bordo e' PIU' ALTO della
    # sezione del pack, e a questo pensa width_end.
    V = grid.reshape(-1, 3)

    if fp.pillow:
        # a sovrapposizione non c'e' niente da appoggiare sul retro: il lembo
        # sta SOTTO l'altro bordo, quindi non si vede e non si modella. Una
        # falda a spessore zero uscirebbe come una lamina degenere.
        Vm, UVm, Tm = V, UV, T
    else:
        V2, UV2, T2 = fin_on_surface(grid, fp, G, nv, gap=0.5, fade=10.0)
        Vm = np.vstack([V, V2])
        UVm = np.vstack([UV, UV2])
        Tm = np.vstack([T, T2 + len(V)])
    if _normals(Vm, Tm)[int(np.argmax(Vm[:, 2]))][2] < 0:
        Tm = Tm[:, [0, 2, 1]]

    sh = fp.sheet
    if fp.ruotato:
        # lo steso e' stato analizzato trasposto: per ritagliarlo serve il
        # rettangolo vero della pagina, e la texture va rimessa nello stesso
        # telaio della UV, con il perimetro sulle righe
        sh = (sh[1], sh[0], sh[3], sh[2])
    # Rasterizzare a 200 dpi un foglio che poi write_glb_mesh rimpicciolisce
    # a tmax px di lato vuol dire produrre pixel per buttarli: sul K Brioss,
    # 7,5 milioni per tenerne 2. Il dpi si abbassa fino a quello che serve
    # davvero, mai piu' in su di quello chiesto - quindi sui fogli piccoli,
    # che sono gia' sotto il limite, non cambia niente.
    lato_pt = max(sh[2] - sh[0], sh[3] - sh[1])
    dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
    tex = folding.rasterize_panels(
        clean, {"film": Panel(sh[0], sh[1], sh[2], sh[3], "film")},
        dpi=dpi_tex, inset_px=0, clean=(case is None))["film"]
    if fp.ruotato:
        # rotazione, non trasposizione: trasporre e' una riflessione e
        # specchierebbe la grafica. Di 270 perche' e' il verso che lascia il
        # perimetro crescente come lo intende girth_span.
        tex = tex.transpose(Image.ROTATE_270)
    exporters.write_glb_mesh(Vm, UVm, Tm, tex, out_glb, tex_max=tmax)

    base = fin_open / max(int(teeth), 1)
    if fp.pillow:
        sez = ("sezione a ellisse %.1f x %.1f (giro %.1f invariato, lembo "
               "coperto %.1f)" % (2.0 * semiasse, fp.T, G,
                                  fp.sovrapposizione))
    else:
        sez = ("sezione %.1f x %.1f (perimetro %.1f invariato)"
               % (scala * fp.W, scala * fp.T, G))
    return ["flowpack%s, rigonfiamento %s"
            % (" a sovrapposizione" if fp.pillow else "", soft), sez,
            "corpo %.1f mm, pinne %.1f" % (fp0.L, fp.end_fin),
            ("pinne lisce" if teeth == 0 else
             "%d denti equilateri, base %.2f altezza %.2f mm"
             % (teeth, base, base * math.sqrt(3) / 2)),
            "mappatura per pannello" if knots else "mappatura per arco"] + avvisi_sez


def _panel_knots(Ps, d, G, fp):
    """Spigoli della sezione, per far cadere ogni fascia sul suo pannello."""
    if fp.pillow:
        # Un'ellisse non ha spigoli, quindi la ricerca per curvatura qui sotto
        # non trova niente e la verifica non scattava: la grafica poteva
        # ruotare attorno al tubo senza che nessuno se ne accorgesse. I nodi
        # di un tubo piatto sono le due PIEGHE, cioe' gli estremi dell'asse
        # maggiore, e lo steso dice dove devono cadere: a back_a dalla
        # cucitura e a back_a + fronte.
        try:
            ia = int(np.argmax(Ps[:-1, 0]))
            ib = int(np.argmin(Ps[:-1, 0]))
            ks = [0.0] + sorted([float(d[ia]), float(d[ib])]) + [G]
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


# Il viewer glamlab chiama questa API con le sue etichette: il suo
# BuildFromPdfPanel manda kind "cartotecnico", non "carton". Senza sinonimo
# quel valore non entrava in nessun ramo e ogni astuccio finiva dal solutore
# flowpack, che e' esattamente l'errore contro cui le regole mettono in
# guardia: la tipologia si dichiara, e se la dichiarazione non viene
# riconosciuta e' come non averla.
SINONIMI_KIND = {"cartotecnico": "carton", "astuccio": "carton",
                 "carton": "carton", "flowpack": "flowpack"}


def normalizza_kind(kind):
    if kind is None:
        return None
    return SINONIMI_KIND.get(str(kind).strip().lower(), kind)


KIND_NOTI = ("carton", "flowpack")


def analyze_pdf(pdf, kind=None):
    """`kind` arriva dall'utente: la tipologia si dichiara, non si indovina.
    Il riconoscimento automatico sbaglia (il solutore astuccio risolve anche
    certi flowpack) e sbagliare qui compromette tutto il resto."""
    kind = normalizza_kind(kind)
    if kind is not None and kind not in KIND_NOTI:
        # Cadere nel ramo flowpack e' peggio che fermarsi: e' lo stesso difetto
        # del sinonimo mancante, solo sull'altro capo. Su questo file - un
        # astuccio Nutella Donut - passando "auto" invece di niente il solutore
        # astuccio veniva saltato e usciva un flowpack.
        raise ValueError("tipologia '%s' non riconosciuta: dichiara "
                         "'carton' o 'flowpack'" % kind)
    case = CASI.get(_sig(pdf))
    if case and kind in (None, "flowpack"):
        return dict(kind="flowpack", title=case["name"],
                    teeth_default=case["teeth"], soft_default=case["soft"],
                    meta=["caso calibrato: " + case["name"],
                          "nastro %.0f x passo %.0f mm" % (case["web"], case["step"])])
    if kind in (None, "carton"):
        try:
            d = dl.analyze(pdf)
            if d.panels:
                meta = ["astuccio %s%s" % (d.layout, "" if d.chiuso
                                           else " aperto"),
                        "%.1f x %.1f x %.1f mm" % d.dims_mm]
                apertura = dl.dichiara_apertura(d)
                if apertura:
                    meta.append(apertura)
                rgb = avviso_quadricromia(pdf)
                if rgb:
                    meta.insert(0, rgb)
                return dict(kind="carton", title="Astuccio %s" % d.layout,
                            meta=meta)
        except Exception:
            if kind == "carton":
                raise
    # se fallisce anche il ripiego, l'errore va al client
    _box, fp, ripiego = analisi_flowpack(pdf)
    meta = ["flowpack", "nastro %.0f x passo %.0f mm" % (fp.web_mm, fp.step_mm),
            "corpo %.1f mm" % fp.L]
    if fp.pillow:
        # a sovrapposizione la sezione non c'e' nello steso: il tubo e' piatto
        # e la forma che prende gonfiandosi la decide il rigonfiamento. Quello
        # che lo steso dice davvero e' giro, fronte e lembo coperto.
        meta.append("tubo piatto: giro %.1f, fronte %.1f, lembo coperto %.1f mm"
                    % (fp.girth, fp.W, fp.sovrapposizione))
    else:
        meta.append("sezione %.1f x %.1f mm" % (fp.W, fp.T))
    sospetto = falda_sospetta(fp)
    if sospetto:
        # prima di costruire, non dopo: qui l'utente le quote le sta leggendo
        meta.insert(0, sospetto)
    rgb = avviso_quadricromia(pdf)
    if rgb:
        meta.insert(0, rgb)
    if ripiego is not None:
        # anche qui il ripiego si dichiara: questi cartellini sono la prima
        # cosa che l'utente legge, e finora tacevano
        meta.insert(0, "ANALISI AUTOMATICA FALLITA (%s): quote dal solutore "
                       "vecchio, da verificare" % ripiego[:70])
    return dict(kind="flowpack", title="Flowpack",
                teeth_default=20, soft_default="medio", meta=meta)


# --------------------------------------------------------------------------- #
# http
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    # HEAD risponde con le stesse intestazioni di GET e senza corpo. Il flag
    # lo dice a _send, cosi' le due risposte non possono divergere.
    _senza_corpo = False

    def log_message(self, fmt, *a):
        sys.stderr.write("  %s\n" % (fmt % a))

    def _cors(self):
        # l'interfaccia puo' stare su un dominio diverso dal backend
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Pack3d")
        # senza questo il browser nasconde l'header alla pagina, su altra origine
        self.send_header("Access-Control-Expose-Headers", "X-Pack3d-Meta")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, code, body, ctype="application/json", filename=None,
              meta=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if meta:
            # percent-encoded: un header HTTP e' latin-1 e non tollera accenti
            self.send_header("X-Pack3d-Meta", quote(
                json.dumps(meta, ensure_ascii=False)))
        if filename:
            self.send_header("Content-Disposition",
                             'attachment; filename="%s"' % filename)
        self._cors()
        self.end_headers()
        if not self._senza_corpo:
            self.wfile.write(body)

    def do_HEAD(self):
        # Render controlla la salute del servizio con HEAD, e
        # BaseHTTPRequestHandler senza do_HEAD risponde 501 a ogni controllo:
        # nel log di produzione si vede "Unsupported method ('HEAD')" a ogni
        # giro, dal primo istante dopo il deploy.
        self._senza_corpo = True
        try:
            self.do_GET()
        finally:
            self._senza_corpo = False

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            return self._send(200, json.dumps({"ok": True}))
        path = os.path.join(HERE, "pack3d_studio.html")
        with open(path, "rb") as fh:
            self._send(200, fh.read(), "text/html; charset=utf-8")

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return self._send(400, "Nessun file ricevuto")
            if n > MAX_UPLOAD:
                return self._send(413, "PDF troppo grande (limite %d MB)"
                                  % (MAX_UPLOAD // (1024 * 1024)))
            data = self.rfile.read(n)
            if not data.startswith(b"%PDF"):
                return self._send(400, "Il file caricato non e' un PDF")
            opts = json.loads(self.headers.get("X-Pack3d") or "{}")
            with tempfile.TemporaryDirectory() as td:
                pdf = os.path.join(td, "in.pdf")
                with open(pdf, "wb") as fh:
                    fh.write(data)
                kind = normalizza_kind(opts.get("kind") or None)
                if kind == "altro":
                    return self._send(400, "Tipologia non ancora supportata")
                if kind is not None and kind not in KIND_NOTI:
                    return self._send(400, "Tipologia '%s' non riconosciuta: "
                                           "dichiara 'carton' o 'flowpack'" % kind)
                if self.path.startswith("/api/analyze-ai"):
                    import agent
                    par, tr = agent.analyse(pdf, kind, opts)
                    par["_chiamate"] = [t["tool"] for t in tr]
                    return self._send(200, json.dumps(par, ensure_ascii=False))
                if self.path.startswith("/api/analyze"):
                    return self._send(200, json.dumps(analyze_pdf(pdf, kind)))
                if self.path.startswith("/api/build"):
                    if not _slots.acquire(blocking=False):
                        return self._send(503, "Server occupato: riprova fra qualche "
                                               "secondo")
                    # Da qui in giu' il posto e' preso e va restituito comunque
                    # vada. Prima analyze_pdf stava FUORI da qualsiasi
                    # protezione: su un PDF che non sa risolvere (K Tronky,
                    # "saldature di testa non riconosciute") lanciava, il posto
                    # non tornava indietro, e dopo MAX_JOBS tentativi il server
                    # rispondeva 503 a chiunque fino al riavvio.
                    try:
                        out = os.path.join(td, "out.glb")
                        case = CASI.get(_sig(pdf))
                        info = analyze_pdf(pdf, kind)
                        q = "alta" if str(opts.get("quality")) == "alta" else "web"
                        # Su TUTTI i rami: e' proprio sul ramo che se ne
                        # dimenticava che nasceva l'UnboundLocalError.
                        avvisi_ingresso = []
                        if info["kind"] == "carton":
                            # build_carton i suoi avvisi li restituiva gia', ed
                            # era il chiamante a buttarli e poi a leggere una
                            # variabile che su questo ramo non esisteva.
                            avvisi = build_carton(pdf, out, q)
                        else:
                            soft = opts.get("soft", "medio")
                            if str(soft).strip().lower() == "auto":
                                # "Scegli tu": il livello lo decide l'agente in
                                # /api/analyze-ai e torna qui dentro params
                                scelto = livello_da_agente(opts.get("params"))
                                if scelto is None:
                                    # Nessuna analisi allegata: gonfiore() cade
                                    # su 5 in silenzio mentre l'interfaccia ha
                                    # appena promesso che sceglieva l'AI. Un
                                    # ripiego muto che produce un modello
                                    # plausibile e' il difetto peggiore che
                                    # questo progetto possa avere.
                                    avvisi_ingresso.append(
                                        "RIGONFIAMENTO NON SCELTO DA NESSUNO: "
                                        "nessuna analisi AI allegata alla "
                                        "richiesta, uso il livello medio 5")
                                    soft = 5
                                else:
                                    soft = scelto
                            # la scatola puo' dirla l'agente o la casella
                            # dell'interfaccia: basta una delle due
                            scatola = (bool(opts.get("scatola"))
                                       or scatola_da_agente(opts.get("params")))
                            pinne = opts.get("pinne")
                            if pinne in (None, "", "auto"):
                                pinne = pinne_da_agente(opts.get("params"))
                            avvisi = build_flowpack(
                                pdf, out, int(opts.get("teeth", 20)),
                                str(soft), case, q,
                                sezione_da_agente(opts.get("params")),
                                scatola, pinne)
                        with open(out, "rb") as fh:
                            # gli avvisi della costruzione viaggiano in un
                            # header: il corpo e' il GLB. Finivano nel nulla,
                            # e con loro ogni diagnostica.
                            return self._send(200, fh.read(), "model/gltf-binary",
                                              filename="modello.glb",
                                              meta=avvisi_ingresso + list(avvisi))
                    finally:
                        _slots.release()
            return self._send(404, "endpoint sconosciuto")
        except Exception as e:
            traceback.print_exc()
            return self._send(500, "%s: %s" % (type(e).__name__, e))


# Tubo piatto a sovrapposizione: quanto e' spessa la sezione in frazione del
# diametro del cerchio, ai due estremi della scala di rigonfiamento. Il cerchio
# e' il massimo fisico: con quel film non si puo' essere piu' tondi. Il valore
# al livello 1 viene dalla taratura sul K Tronky T1, che al livello 5 deve
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
# bassa. 0,40 e' quella che riproduce le foto del Brioss: 37,6 = 22,8 di gola
# piu' 14,8 di pinna. Tarata su un pack solo.
GOLA_SU_SPESSORE = float(os.environ.get("PACK3D_GOLA", "0.40"))

MAX_UPLOAD = 60 * 1024 * 1024
# Uno, non due: una costruzione misurata arriva a 400 MB di picco e le
# istanze piccole hanno 512 MB di RAM. Vedi DEPLOY.md per i numeri.
MAX_JOBS = int(os.environ.get("PACK3D_MAX_JOBS", "1"))
_slots = threading.Semaphore(MAX_JOBS)

if __name__ == "__main__":
    # PORT e HOST arrivano dall'ambiente sui servizi di hosting; in locale
    # bastano gli argomenti. 0.0.0.0 serve per essere raggiungibili da fuori.
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("pack3d studio in ascolto su %s:%d" % (host, port))
    if host in ("0.0.0.0", "::"):
        print("  in locale:  http://localhost:%d" % port)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
