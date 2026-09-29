"""
Riconoscimento dell'arte tecnica in un artwork PDF.

Tre livelli, dal certo allo stimato:

1. **Processing Steps (ISO 19593-1)** — lo standard nato dal Ghent Workgroup.
   Gli oggetti non stampati stanno su livelli (OCG) marcati con metadati
   normalizzati, divisi in sette gruppi: Structural, Dimensions, Braille,
   Legend, Position, White, Varnish. Se il file e' conforme la lettura e'
   esatta e non serve indovinare nulla.
2. **Nomi delle separazioni** — quando i Processing Steps non ci sono ma le
   tinte piatte sono dichiarate. La norma stessa aiuta: un oggetto tecnico che
   si sovrappone alla grafica *deve* essere una tinta piatta in sovrastampa e
   *non puo'* chiamarsi All, None, Cyan, Magenta, Yellow o Black.
3. **Euristica** — spessore a filo di capello e colore. E' una stima, e va
   dichiarata come tale.

Il livello 2 e' insidioso: su Kinder Bueno Dark il nero era davvero fustella,
quindi il nome da solo non basta a decidere e conviene incrociare con lo
spessore.
"""
from __future__ import annotations

import re as _re

# gruppi ISO 19593-1 che non vanno mai stampati sul modello 3D
ISO_GROUPS = {
    "structural", "dimensions", "braille", "legend",
    "position", "positions", "white", "varnish",
}

# tipi a nome fisso del gruppo Structural (piu' quelli di Position)
ISO_TYPES = {
    "cutting", "partialcutting", "reversepartialcutting",
    "creasing", "reversecreasing", "cuttingcreasing",
    "reversecuttingcreasing", "partialcuttingcreasing",
    "reversepartialcuttingcreasing", "drilling", "gluing",
    "foilstamping", "coldfoilstamping", "embossing", "debossing",
    "perforating", "bleed", "varnishfree", "inkfree", "inkvarnishfree",
    "folding", "punching", "stapling",
    "hologram", "barcode", "contentarea", "codingmarking", "imprinting",
}

# Frasi che collocano una separazione fra le lastre tecniche, confrontate per
# SOTTOSTRINGA e non per nome intero.
#
# Il confronto per nome intero e' quello che c'era, e non regge: i nomi veri
# sono composti. Su un astuccio Nutella Donut la vernice si chiama "Water
# Based Gloss Varnish" e l'insieme conteneva "varnish", "gloss varnish" e
# "waterbased varnish" - tre voci, nessuna delle quali e' quel nome. La
# vernice restava quindi dentro l'artwork, e pdfium la rende opaca: copriva
# tutto il pannello di rosa.
#
# Qui stanno solo le frasi abbastanza lunghe da non prendere niente per
# sbaglio. Le sigle corte stanno sotto.
FRASI_TECNICHE = (
    "varnish", "vernice", "lack", "coating",
    "dieline", "die line", "die-line", "cutcontour", "cut contour",
    "thru-cut", "thrucut", "kiss cut", "kisscut", "cutter", "cutting",
    "crease", "cordonatura", "creasing",
    "perf", "glue", "gluelap", "coldseal", "cold seal",
    "opaque white", "underprint",
    "technical", "tecnico", "stanz", "fustella",
    "braille", "registration", "reg mark", "eyemark", "eye mark",
    "legend", "dimension", "infopanel", "info panel", "job ticket",
    "print free", "printfree", "ink free", "inkfree",
    "best before area", "bar code area", "barcode area",
    "covered area", "neutral area", "text area",
    "gda area", "area gda", "gda box", "gda panel",
)

# Nomi corti o ambigui: qui la sottostringa farebbe danni - "cut" prenderebbe
# mezzo dizionario, "td" qualunque parola con quelle due lettere - e si
# confrontano interi.
SIGLE_TECNICHE = {
    "all", "none", "cut", "td", "dt", "white", "bianco", "bleed",
    "abbondanza", "fold", "falz", "rill", "taglio", "stand", "stand blau",
    "label", "check", "note", "notes", "gda",
}

# tenuto per chi lo importava: e' l'unione delle due, nella forma vecchia
VENDOR_NAMES = set(FRASI_TECNICHE) | SIGLE_TECNICHE

# nomi di livello che indicano arte tecnica, anche fuori dallo standard ISO
OCG_TECH = {
    "technical-drawing", "technical drawing", "technicaldrawing", "dieline",
    "dimensions", "dimension", "notes", "note", "check", "legend",
    "white", "varnish", "coldseal", "cold seal", "eyemark", "eye mark",
    "infopanel", "info panel", "info mad-e", "braille", "reg marks",
    "print free area", "best before area", "bar code area", "covered area",
    "neutral area", "text area",
    "gda", "gda area", "area gda",
    "guides and grids", "guides", "grids", "guide", "griglia", "griglie",
    "guide e griglie", "cutter", "cut", "fustella", "tracciato",
}

# lastre tecniche gia' incontrate, per nome della tinta
LASTRE_NOTE = {
    "pantone 3405 c": "Technical Drawing", "pantone 346 c": "Dimensions",
    "pantone 571 c": "Print Free Area", "pantone 350 c": "Best Before Area",
    "pantone 341 c": "Bar Code Area", "pantone 1565 c": "COVERED Area",
    "coldseal": "Cold seal", "white": "Bianco coprente",
    "stand blau": "Disegno tecnico", "all": "Registro",
}

RESERVED = {"all", "none", "cyan", "magenta", "yellow", "black"}


def _norm(s):
    return str(s).lstrip("/").replace("#20", " ").strip().lower()


def processing_steps(reader, page):
    """OCG marcati come Processing Steps, secondo ISO 19593-1.

    La norma vive nel dizionario dell'OCG; le implementazioni usano chiavi
    diverse per lo stesso concetto, quindi si cerca qualunque chiave che parli
    di processing step invece di fissarne una sola.
    """
    found = {}
    root = reader.trailer["/Root"]
    oc = root.get("/OCProperties")
    if not oc:
        return found
    for ref in oc.get("/OCGs", []):
        try:
            g = ref.get_object()
        except Exception:
            continue
        name = _norm(g.get("/Name", ""))
        group = ptype = None
        for k, v in g.items():
            if "procstep" in str(k).lower() or "processingstep" in str(k).lower():
                val = _norm(v if not hasattr(v, "get_object") else v.get_object())
                if val in ISO_GROUPS:
                    group = val
                elif val in ISO_TYPES:
                    ptype = val
        if group is None and name in ISO_GROUPS:
            group = name          # livello nominato come il gruppo
        if group is None and ptype is None and name in OCG_TECH:
            group = "structural"  # nome di livello esplicitamente tecnico
        if group or ptype:
            found[ref.idnum if hasattr(ref, "idnum") else id(g)] = dict(
                name=name, group=group, type=ptype)
    return found


# Le lastre che COPRONO la grafica, invece di tracciarla.
#
# La distinzione non e' di comodo, e' quella che decide chi le puo' togliere.
# Una fustella, una quota, un retino print-free sono TRATTI: sottili, e
# l'euristica su spessore e colore li prende. Una vernice, un bianco coprente,
# un cold seal sono PIENI grandi quanto la grafica: nessuna euristica sul
# tratto li puo' vedere, e pdfium li rende opachi. Sull'astuccio Nutella Donut
# la `Water Based Gloss Varnish` copriva tutto il pannello di rosa.
#
# Solo queste si strappano per nome nella costruzione. Le altre restano
# all'euristica, e non per pigrizia: strappare anche quelle costa una passata
# di pypdf sul flusso di contenuto, e su Colazione erano 7 secondi e 100 MB di
# picco in piu' - oltre il tetto dei 512 MB - per togliere tratti che la
# maschera del disegno tecnico prendeva gia'.
# La GDA sta qui, e non fra i soli nomi tecnici, per una ragione precisa.
#
# La GDA - la dichiarazione nutrizionale con le sue caselle - appartiene al
# disegno tecnico: e' il tecnico che ne riserva il posto, non il grafico che la
# disegna. Quando pero' un file la mette nel livello della grafica, ed accade,
# quel riquadro e' un PIENO grande come la casella: l'euristica sul tratto non
# lo vede, e sul modello resterebbe stampato. Toglierla per nome e' l'unico
# modo di scartarla, e il costo lo paga solo il file che ce l'ha davvero.
# Quello che vale per la GDA vale per tutta la sua famiglia. `COVERED Area`,
# `TEXT AREA`, `Best Before Area`, `Bar Code Area`, `Print Free Area`,
# `Neutral Area` sono aree riservate esattamente come lei: rettangoli PIENI
# grandi quanto la casella, con la scritta in bianco dentro. Stanno gia' fra i
# nomi tecnici, ma finche' non sono state anche coperture l'unica cosa che
# poteva toglierle era l'euristica sul tratto, che un pieno non lo vede: sulla
# texture di K Colazione Piu' restavano stampate sul pack due fasce `TEXT
# AREA`, una `COVERED AREA` e un riquadro `BEST BEFORE AREA`.
COPERTURE_FRASI = (
    "varnish", "vernice", "lack", "coating",
    "cold seal", "coldseal", "opaque white", "underprint", "coprente",
    "gda area", "area gda", "gda box", "gda panel",
    "covered area", "text area", "best before area",
    "bar code area", "barcode area", "print free area", "printfree area",
    "neutral area", "area riservata",
)
# "white" solo intero: come sottostringa prenderebbe "White Chocolate", che e'
# un colore dell'artwork. Stessa cosa per "gda", che intero non e' il nome di
# nessun inchiostro.
COPERTURE_SIGLE = {"white", "bianco", "gda"}

# I BOX AREA si tolgono sempre, come la GDA, su ogni modello 3D: flowpack,
# astucci e vassoi. E' la regola, detta cosi' dopo il Nutella B-ready T2 e il
# Kinder Country. Per nome e' un box area ogni lastra che si CHIAMA area,
# anche se la frase non e' fra quelle qui sopra: sul B-ready c'e' `PIN CODE
# Area`, che non c'era, e domani ci sara' un `LOT Area`. Nessun inchiostro si
# chiama cosi'.
#
# Tranne la promo. L'`AREA PROMO` della legenda del K Brioss (FERRERO_1765...)
# e' tutta la fascia gialla con "Scopri il mondo di Quelli della COLAZIONE" e
# "VINCI l'esclusivo SET COLAZIONE": e' la grafica della promo, e si stampa.
AREA_NOME = _re.compile(r"\barea\b")


def area(nome):
    """Vero se questa lastra e' un box area: si toglie sempre, come la GDA."""
    n = _norm(nome)
    if n in RESERVED or "promo" in n:
        return False
    return n == "gda" or n.startswith("gda ") or bool(AREA_NOME.search(n))


# I box area che sono VUOTI per definizione: il posto di un testo, di un
# codice, di una data, o un posto dove non si stampa. Dentro c'e' solo la
# didascalia. Gli altri possono avere grafica sotto: la COVERED AREA e' la
# fascia che la pinna nasconde, e sul Kinder Cards T2 porta la cialda e la
# banda rossa; e un'area che non si conosce - una `Emboss Area`, una
# `Varnish Free Area` - si tratta come lei.
_VUOTE = _re.compile(
    r"\b(gda|text|best\s*before|bar\s*code|barcode|ean|pin\s*code|pincode|"
    r"alphanumeric|lot|print\s*free|printfree|neutral|reserved|"
    r"riservata|testo|codice|lotto|scadenza)\b")


def vuota(nome):
    """Vero se questo box area - per nome della lastra o per didascalia - e'
    vuoto per definizione: dentro si spegne anche quello che ha il colore
    della didascalia. Vedi `strati.dividi`."""
    n = _norm(nome)
    return ("covered" not in n and "coperta" not in n
            and bool(_VUOTE.search(n)))


def copertura(nome):
    """Vero se questa lastra copre la grafica invece di tracciarla."""
    n = _norm(nome)
    if n in RESERVED:
        return False
    return (n in COPERTURE_SIGLE or any(f in n for f in COPERTURE_FRASI)
            or area(n))


# Le lastre che DISEGNANO il disegno tecnico, per come si chiamano: il tratto
# e anche i suoi pieni. Sul Nutella B-ready T2 la lastra "Technical Drawing
# light" dipinge una banda piena di 2 mm sul fianco, che l'euristica sul
# tratto non vede - e' un pieno - e che sul modello era una riga verde.
#
# Solo frasi che lo dicono. Niente sigle corte, niente tinte imparate da un
# file (`LASTRE_NOTE`: il Pantone 346 e' le quote su un Kinder e grafica su
# un altro, e toglierlo per nome cancellava il 9% di un pannello del Pingui
# T6), niente `All`: il registro, che sul K Brioss STD dipinge anche testo e
# toglierlo cambiava il 2% della texture. E niente tacca di fotocentratura,
# che si stampa davvero.
DISEGNO_FRASI = (
    "technical", "tecnico", "dieline", "die line", "die-line",
    "cutcontour", "cut contour", "thru-cut", "thrucut", "kiss cut", "kisscut",
    "cutter", "cutting", "crease", "creasing", "cordonatura", "stanz",
    "fustella", "dimension", "legend",
)


def disegno(nome):
    """Vero se questa lastra traccia il DT o lo copre: si toglie per nome."""
    n = _norm(nome)
    if n in RESERVED:
        return False
    return copertura(n) or any(f in n for f in DISEGNO_FRASI)


def tecnica(nome):
    """Vero se il nome di questa separazione la colloca fra le lastre tecniche.

    Cyan, Magenta, Yellow e Black non lo sono mai: sono i colori di processo.
    `All` invece si', perche' e' il registro.
    """
    n = _norm(nome)
    if n in RESERVED:
        return n == "all"
    if n in SIGLE_TECNICHE or n in LASTRE_NOTE or n in ISO_TYPES or n in ISO_GROUPS:
        return True
    return any(f in n for f in FRASI_TECNICHE)


def technical_separations(page, dentro_i_form=True, prova=None):
    """Separazioni il cui nome le colloca fra le lastre tecniche.

    Con `prova` si cambia il criterio: `copertura` per le sole lastre che
    coprono la grafica, che sono quelle che la costruzione strappa.

    Si scende anche nei Form XObject: una vernice o un bianco coprente ci
    stanno dentro piu' spesso che a livello di pagina.
    """
    prova = prova or tecnica
    out, visti = {}, set()

    def giro(res):
        if res is None:
            return
        res = res.get_object()
        if id(res) in visti:
            return
        visti.add(id(res))
        cs = res.get("/ColorSpace")
        if cs:
            for key, val in cs.get_object().items():
                try:
                    o = val.get_object()
                    if o[0] == "/Separation":
                        names = [_norm(o[1])]
                    elif o[0] == "/DeviceN":
                        names = [_norm(x) for x in o[1]]
                    else:
                        continue
                except Exception:
                    continue
                for n in names:
                    if prova(n):
                        out[str(key)] = n
                        break
        if not dentro_i_form:
            return
        xo = res.get("/XObject")
        if xo:
            for _, v in xo.get_object().items():
                try:
                    o = v.get_object()
                    if o.get("/Subtype") == "/Form":
                        giro(o.get("/Resources"))
                except Exception:
                    pass

    giro(page.get("/Resources"))
    return out


# --------------------------------------------------------------------------- #
# quadricromia o RGB
# --------------------------------------------------------------------------- #
# La regola e' della stampa, non del gusto: un'immagine RGB in macchina la
# converte chi stampa, e il colore lo decide lui e non il file.
#
# Per la SOVRASTAMPA invece l'RGB non e' un problema, e qui si era creduto il
# contrario. Un oggetto RGB in sovrastampa stampa la quadricromia e lascia
# stare le tinte piatte che trova: sul Kinder Choco Fresh T1 e sul KP T1
# Mandarino l'ombra della colata e' un'immagine RGB indicizzata, ciano, in
# sovrastampa sul rosso in tinta piatta, e il rosso sotto resta - l'ombra
# c'e'. Sembrava di no perche' Ghostscript, sotto un'immagine RGB con una
# maschera morbida, la tinta piatta la cancella. Adesso la sovrastampa la
# simula `strati` (vedi *la sovrastampa delle immagini*), e l'avviso sull'RGB
# resta per il colore, non per la colata.
#
# Si guardano le IMMAGINI, non gli spazi colore dichiarati, e per un motivo
# misurato: gli spazi RGB dichiarati ci sono quasi sempre - sul K Tronky T1 ce
# n'e' uno usato 23 volte, e quel file l'utente l'ha validato - perche' li usa
# anche l'arte tecnica, che dalla texture viene via comunque. Una immagine
# grande in RGB invece e' grafica che si vede, ed e' esattamente il caso della
# colata.
_FISSI = {"/DeviceGray": 1, "/DeviceRGB": 3, "/DeviceCMYK": 4,
          "/G": 1, "/RGB": 3, "/CMYK": 4, "/CalGray": 1, "/CalRGB": 3,
          "/Lab": 3, "/Pattern": 0}

# Quante volte l'immagine piu' piccola che vale la pena segnalare. Un logo o
# una iconcina in RGB non sposta niente; una colata, una foto di prodotto, un
# fondo fotografico stanno tutti sopra il mezzo megapixel.
RGB_MINIMO_PX = 500_000


def canali_spazio(cs):
    """Canali di uno spazio colore, o None se non si capisce.

    Un `/Indexed` conta i canali della sua base: la tavolozza e' fatta di
    quelli, ed e' lei a dire in che spazio sta davvero l'immagine.
    """
    try:
        o = cs.get_object() if hasattr(cs, "get_object") else cs
    except Exception:
        return None
    if not isinstance(o, list):
        return _FISSI.get(str(o))
    try:
        fam = str(o[0])
    except Exception:
        return None
    if fam == "/ICCBased":
        try:
            return int(o[1].get_object().get("/N"))
        except Exception:
            return None
    if fam == "/Indexed":
        return canali_spazio(o[1])
    if fam == "/Separation":
        return 1
    if fam == "/DeviceN":
        try:
            return len(o[1])
        except Exception:
            return None
    return _FISSI.get(fam)


def rgb(cs):
    """Vero se questo spazio colore e' RGB.

    Contare i canali non basta: un `/DeviceN` di tre inchiostri ha tre canali
    ed e' tinta piatta in tutto e per tutto, sovrastampa compresa.
    """
    try:
        o = cs.get_object() if hasattr(cs, "get_object") else cs
    except Exception:
        return False
    if not isinstance(o, list):
        return str(o) in ("/DeviceRGB", "/RGB", "/CalRGB")
    try:
        fam = str(o[0])
    except Exception:
        return False
    if fam == "/Indexed":
        return rgb(o[1])
    if fam == "/ICCBased":
        return canali_spazio(o) == 3
    return fam in ("/DeviceRGB", "/RGB", "/CalRGB")


def immagini_rgb(page, minimo=RGB_MINIMO_PX, dentro_i_form=True):
    """Le immagini RGB dell'artwork, dalla piu' grande, come (nome, w, h)."""
    out, visti = [], set()

    def giro(res):
        if res is None:
            return
        try:
            res = res.get_object()
        except Exception:
            return
        if id(res) in visti:
            return
        visti.add(id(res))
        xo = res.get("/XObject")
        if not xo:
            return
        try:
            voci = list(xo.get_object().items())
        except Exception:
            return
        for key, val in voci:
            try:
                o = val.get_object()
            except Exception:
                continue
            sub = o.get("/Subtype")
            if sub == "/Form":
                if dentro_i_form:
                    giro(o.get("/Resources"))
            elif sub == "/Image" and rgb(o.get("/ColorSpace")):
                try:
                    w, h = int(o.get("/Width", 0)), int(o.get("/Height", 0))
                except Exception:
                    continue
                if w * h >= minimo:
                    out.append((w * h, str(key), w, h))

    giro(page.get("/Resources"))
    out.sort(key=lambda t: -t[0])
    return [(k, w, h) for _, k, w, h in out]


def avviso_rgb(page, dentro=None):
    """La riga da mostrare a chi costruisce, o niente se il file e' a posto.

    `dentro`, se c'e', e' l'insieme delle misure in pixel delle immagini che
    stanno sul DT (`tracciati.immagini_nel_riquadro`): le altre sono note -
    il logo dello studio nel cartiglio - e non si contano.
    """
    im = immagini_rgb(page)
    if dentro is not None:
        im = [x for x in im if (x[1], x[2]) in dentro]
    if not im:
        return None
    k, w, h = im[0]
    quali = ("l'immagine %s (%dx%d px) e' a tre canali" % (k, w, h) if len(im) == 1
             else "%d immagini sono in RGB, la piu' grande %s (%dx%d px)"
                  % (len(im), k, w, h))
    return ("GRAFICA IN RGB: %s. Va fornita in quadricromia: un'immagine RGB "
            "in macchina la converte chi stampa, e il colore lo decide lui e "
            "non il file." % quali)


def classify(pdf_path, page_no: int = 0):
    """Come va trattato il disegno tecnico di questo file.

    Restituisce il livello usato, cosa scartare e quanto ci si puo' fidare.
    """
    import pypdf
    r = pypdf.PdfReader(pdf_path)
    page = r.pages[page_no]

    steps = processing_steps(r, page)
    if steps:
        vero_iso = any(v.get("type") for v in steps.values())
        drop = {k: v for k, v in steps.items()
                if (v["group"] or "") in ISO_GROUPS}
        return dict(level=1 if vero_iso else 2,
                    method="Processing Steps ISO 19593-1" if vero_iso
                           else "nomi dei livelli OCG",
                    certainty="esatta" if vero_iso else "alta",
                    ocgs=drop, separations={},
                    detail=sorted({v["group"] for v in drop.values() if v["group"]}))

    seps = technical_separations(page)
    if seps:
        return dict(level=3, method="nomi delle separazioni",
                    certainty="alta, da incrociare con lo spessore",
                    ocgs={}, separations=seps, detail=sorted(set(seps.values())))

    return dict(level=4, method="euristica su spessore e colore",
                certainty="stimata", ocgs={}, separations={}, detail=[])


# --- Le aree riservate che il file scrive, ma non nomina -------------------
#
# Il caso: K Colazione Piu'. Il foglio ha due fasce `TEXT AREA`, una `COVERED
# AREA` e un riquadro `BEST BEFORE AREA` - aree riservate, la stessa famiglia
# della GDA - e finivano stampate sulla texture. Nel file non c'e' niente che
# lo dica: nessun livello, e le lastre si chiamano `PANTONE 1595 C`,
# `PANTONE 1565 C`, `PANTONE 346 C`. Numeri di colore, non nomi di mestiere.
#
# Il registro `LASTRE_NOTE` non salva: e' costruito su altri file e su questo
# sbaglia due volte su due. Dice `PANTONE 350 C = Best Before Area`, e su
# Colazione quella lastra e' il DISEGNO TECNICO; dice `PANTONE 346 C =
# Dimensions`, e li' e' la BEST BEFORE AREA. E' la stessa lezione del disegno
# tecnico: un numero Pantone e' un colore, e un colore non dice mai a cosa
# serve una lastra.
#
# Quello che il file dice davvero e' scritto sopra l'area, in lettere: dentro
# ogni riquadro c'e' il suo nome, in bianco, come testo vero ed estraibile. Da
# li' si parte, e la lastra si trova guardando CHI DIPINGE SOTTO LA SCRITTA:
# una passata `tiffsep` di Ghostscript a bassa risoluzione da' una mappa
# d'inchiostro per separazione, e sotto ogni etichetta c'e' una lastra sola.
#
#     TEXT AREA (x2)     -> PANTONE 1595 C     inchiostro 93%
#     COVERED AREA       -> PANTONE 1565 C     inchiostro 89%
#     BEST BEFORE AREA   -> PANTONE 346 C      inchiostro 89%
#
# Niente colore, niente geometria, niente registro: l'etichetta e la lastra
# sotto. Costa 1,1 s a 36 dpi su un foglio da 460 x 330 mm, e lo paga solo il
# file che le etichette ce le ha davvero - sul parco sono tre su nove.
from .dieline import PT2MM

# Le didascalie da cui si impara una lastra. Strette di proposito: dicono
# "... AREA" per intero, perche' la lastra che sta sotto si toglie TUTTA. Un
# "EAN CODE" scritto accanto al codice a barre vero, sulla grafica, non deve
# far strappare il fondo. E niente promo: vedi `area`.
_AREE = (r"gda|covered|text|best\s*before|bar\s*code|barcode|"
         r"print\s*free|printfree|neutral|reserved|"
         r"pin\s*code|pincode|alphanumeric(\s*code)?|lot(\s*code)?|ean(\s*code)?")
ETICHETTA_RISERVATA = _re.compile(
    r"(?i)\b(" + _AREE + r")\s*area\b"
    r"|\barea\s+(gda|testo|riservata|codice|lotto|scadenza)\b")

# Il NOME di un'area riservata scritto sull'artwork: e' la didascalia del
# posto, non la cosa che ci andra', e sul pack non si stampa mai. Sono le
# etichette qui sopra piu' il posto del codice a barre scritto per esteso -
# "POSITIONING AREA FOR EAN CODE (if requested)" sul Kinder Cards T2 - e il
# codice scritto da solo, "EAN CODE" sul Nutella B-ready T2. Qui si puo'
# largheggiare: si spegne la scritta, e solo dentro un box area tolto.
NOME_RISERVATA = _re.compile(
    r"(?i)\b(" + _AREE + r"|positioning)\s*area\b"
    r"|\barea\s+(gda|testo|riservata|codice|lotto|scadenza)\b"
    r"|\bean\s*code\b")

# quanto inchiostro deve esserci sotto l'etichetta perche' sia un'area piena e
# non una scritta appoggiata sulla grafica
INCHIOSTRO_MINIMO = 0.5   # quota di lastra su quel pixel
PIENO_MINIMO = 0.60       # quota di pixel pieni nell'intorno dell'etichetta
VICINO = 150.0            # punti: quanto puo' stare lontana la riga di sopra
# Il campione della legenda: un pieno davanti alla didascalia, grande da uno a
# dieci corpi e staccato al piu' di quattro. Sul Kinder Country e' un
# quadrato di 14 punti a 6,5 punti dalla scritta, che ha corpo 6,5.
CAMPIONE_CORPI = (0.8, 10.0)
CAMPIONE_STACCO = 4.0
# larghezza media di un carattere, in corpi: basta a trovare il centro della
# scritta, non a misurarla
LARGHEZZA_CARATTERE = 0.55


def mappe_lastre(pdf, page_no=0, dpi=36, processo=False, solo=None,
                 senza_immagini=False):
    """`{nome lastra: mappa d'inchiostro}` con una passata `tiffsep`.

    Nelle mappe 255 e' niente inchiostro e 0 e' il pieno. Le lastre di
    processo restano fuori, perche' il processo non riserva mai un'area: e'
    la grafica. Con `processo=True` ci sono anche loro - serve a chi cerca
    il nero, vedi `nero.py`.

    Con `solo="black"` si carica quella lastra e basta. Non e' pignoleria:
    un foglio ne ha una dozzina, e chi cerca il nero le altre undici le
    terrebbe in memoria per buttarle. Su un container da 512 MB quello e'
    il genere di spreco che fa fallire un build.

    Con `senza_immagini` la pagina si rende senza le immagini
    (`-dFILTERIMAGE`): e' quello che c'e' SOTTO un'immagine, e serve a chi
    simula la sovrastampa, vedi `strati.sovrastampa`.

    Vuota se Ghostscript non c'e' o se la passata non riesce: chi chiama deve
    sapersela cavare senza, perche' il modello si costruisce comunque.
    """
    import glob
    import os
    import shutil
    import subprocess
    import tempfile

    gs = shutil.which("gs")
    if not gs:
        return {}
    import numpy as np
    from PIL import Image

    cartella = None
    try:
        cartella = tempfile.mkdtemp(prefix="lastre_")
        esito = subprocess.run(
            [gs, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-dMaxSpots=40",
             "-sDEVICE=tiffsep", "-r%g" % dpi]
            + (["-dFILTERIMAGE"] if senza_immagini else [])
            + ["-dFirstPage=%d" % (page_no + 1), "-dLastPage=%d" % (page_no + 1),
               "-sOutputFile=" + os.path.join(cartella, "p.tif"), pdf],
            capture_output=True, timeout=180)
        if esito.returncode != 0:
            return {}
        fuori = {}
        for percorso in glob.glob(os.path.join(cartella, "p(*.tif")):
            nome = _re.search(r"\((.*)\)\.tif$", os.path.basename(percorso))
            if not nome:
                continue
            n = _norm(nome.group(1))
            if n in RESERVED and not processo:
                continue
            if solo is not None and n != _norm(solo):
                continue
            fuori[n] = np.asarray(Image.open(percorso).convert("L"))
        return fuori
    except Exception:
        return {}
    finally:
        if cartella:
            shutil.rmtree(cartella, ignore_errors=True)


def _forse_etichette(pdf, page_no=0):
    """Vero se nel testo della pagina compare la parola `area`.

    Prefiltro, e costa quasi niente: da 0,01 a 0,15 secondi contro i 2,9 che
    l'estrazione del testo di pypdf costa sul K Brioss STD.

    Il testo lo legge pdfium, che decodifica i font e scende nei form. Prima
    si cercava `AREA` nei byte del flusso della pagina, e bastava un font a
    glifi codificati per non vederla: sul Kinder Paradiso T1 la legenda dice
    "Covered Area", "Print Free Area", "Best Before Area", "Bar Code Area" e
    "Pin code area", e i box restavano tutti stampati sul pack. Stesso difetto
    sull'astuccio Pingui T6. Si cerca la parola anche dentro altre - pdfium
    su una didascalia girata e spezzata restituisce "BESAREA": un falso si'
    costa una lettura, un falso no costa un box stampato.
    """
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        try:
            testo = doc[page_no].get_textpage().get_text_range()
        finally:
            doc.close()
        return "area" in (testo or "").lower()
    except Exception:
        return True   # nel dubbio si guarda davvero


def _etichette(pdf, page_no=0):
    """[(x, y, dx, dy, corpo, lunghezza, etichetta)] delle aree riservate
    scritte sulla pagina.

    `(x, y)` e' dove comincia la scritta, nello spazio della pagina (y in su),
    `(dx, dy)` la direzione in cui si legge, `corpo` l'altezza del carattere e
    `lunghezza` quanto e' lunga, stimata: servono a trovarne il CENTRO e il
    campione della legenda che le sta davanti. Prima si guardava solo dove
    comincia, e senza la matrice della pagina: sul Kinder Country "Bar Code
    Area" comincia a un millimetro dal bordo del suo riquadro, e li' attorno
    la lastra piena era il 57%, sotto la soglia.

    Un'etichetta puo' essere spezzata su due righe, e su K Colazione Piu' lo
    e': `BEST BEFORE` e `AREA` arrivano come due frammenti. Si ricuce solo
    quando il frammento e' la parola `AREA` da sola - condizione stretta, e la
    coda di un'etichetta e' l'unica cosa che la soddisfa - e solo se il
    frammento prima e' li' accanto.
    """
    import math
    import pypdf
    trovate = []
    precedente = [None]

    def vis(testo, cm, tm, font, size):
        testo = (testo or "").strip()
        if not testo:
            return
        try:
            a, b, c, d, e, f = (float(v) for v in cm)
            ta, tb, tc, td, te, tf = (float(v) for v in tm)
        except (TypeError, ValueError):
            return
        x, y = te * a + tf * c + e, te * b + tf * d + f
        ux, uy = ta * a + tb * c, ta * b + tb * d
        n = math.hypot(ux, uy) or 1.0
        corpo = abs(float(size or 0.0)) * math.hypot(tc * a + td * c,
                                                     tc * b + td * d)
        riga = [x, y, ux / n, uy / n, corpo or 1.0,
                LARGHEZZA_CARATTERE * (corpo or 1.0) * len(testo)]
        m = ETICHETTA_RISERVATA.search(testo)
        if m is None and testo.upper() == "AREA" and precedente[0]:
            prima, dove = precedente[0]
            if abs(dove[0] - x) <= VICINO and abs(dove[1] - y) <= VICINO:
                m = ETICHETTA_RISERVATA.search(prima + " " + testo)
                if m:
                    riga = list(dove)
        if m:
            trovate.append(tuple(riga) + (m.group(0).strip(),))
        precedente[0] = (testo, riga)

    pypdf.PdfReader(pdf).pages[page_no].extract_text(visitor_text=vis)
    return trovate


def _oggetti(pdf, page_no=0):
    """`(scritte, pieni)`: i riquadri `(x0, y0, x1, y1)` degli oggetti testo e
    dei percorsi pieni della pagina, nello spazio della pagina (y in su).

    Le scritte servono a controllare pypdf, che a volte ripete un testo con
    la posizione di un altro: sul Kinder Cards T2 "Best Before Area" torna
    una seconda volta sulla banda rossa, dove non c'e' scritto niente, e
    sotto c'e' il Kinder ORANGE. I pieni sono dove si cercano i campioni
    della legenda.
    """
    import ctypes
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    from .tracciati import _componi, _matrice

    scritte, pieni = [], []
    lati = [ctypes.c_float() for _ in range(4)]
    pieno, tratto = ctypes.c_int(), ctypes.c_int()

    def giro(cont, quanti, prendi, m):
        for i in range(quanti(cont)):
            o = prendi(cont, i)
            t = raw.FPDFPageObj_GetType(o)
            if t == raw.FPDF_PAGEOBJ_FORM:
                giro(o, raw.FPDFFormObj_CountObjects, raw.FPDFFormObj_GetObject,
                     _componi(m, _matrice(o)))
                continue
            if t == raw.FPDF_PAGEOBJ_TEXT:
                dove = scritte
            elif t == raw.FPDF_PAGEOBJ_PATH:
                raw.FPDFPath_GetDrawMode(o, ctypes.byref(pieno),
                                         ctypes.byref(tratto))
                if not pieno.value:
                    continue
                dove = pieni
            else:
                continue
            if not raw.FPDFPageObj_GetBounds(o, *(ctypes.byref(v) for v in lati)):
                continue
            sx, giu, dx, su = (v.value for v in lati)
            xs = [m[0] * px + m[2] * py + m[4] for px in (sx, dx) for py in (giu, su)]
            ys = [m[1] * px + m[3] * py + m[5] for px in (sx, dx) for py in (giu, su)]
            dove.append((min(xs), min(ys), max(xs), max(ys)))

    doc = pdfium.PdfDocument(pdf)
    try:
        page = doc[page_no]
        giro(page.raw, raw.FPDFPage_CountObjects, raw.FPDFPage_GetObject,
             (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    finally:
        doc.close()
    return scritte, pieni


def _campione(x, y, dx, dy, corpo, pieni):
    """Il pieno che sta davanti alla didascalia, sulla sua riga: il campione
    di colore della legenda, o None.

    Tutto si misura lungo la riga - la direzione della scritta e la sua
    perpendicolare - cosi' vale anche per una legenda girata.
    """
    vx, vy = -dy, dx               # verso l'alto della scritta
    lo, hi = CAMPIONE_CORPI
    migliore, stacco_min = None, None
    for x0, y0, x1, y1 in pieni:
        w, h = x1 - x0, y1 - y0
        if not (lo * corpo <= w <= hi * corpo and lo * corpo <= h <= hi * corpo):
            continue
        cx, cy = (x0 + x1) / 2.0 - x, (y0 + y1) / 2.0 - y
        t, u = cx * dx + cy * dy, cx * vx + cy * vy
        mt = (abs(dx) * w + abs(dy) * h) / 2.0
        mu = (abs(vx) * w + abs(vy) * h) / 2.0
        stacco = -(t + mt)          # quanto finisce prima della scritta
        if not (-0.3 * corpo <= stacco <= CAMPIONE_STACCO * corpo):
            continue
        # sulla riga: il pieno copre almeno un terzo del corpo del testo
        if min(u + mu, 0.8 * corpo) - max(u - mu, -0.2 * corpo) < 0.3 * corpo:
            continue
        if stacco_min is None or stacco < stacco_min:
            migliore, stacco_min = (x0, y0, x1, y1), stacco
    return migliore


def aree_riservate(pdf, page_no=0, dpi=36):
    """`{nome della lastra: etichetta}` delle aree riservate del file.

    Si legge quello che il file scrive - `COVERED AREA`, `TEXT AREA`, `BEST
    BEFORE AREA`, `GDA AREA` - e si guarda quale separazione dipinge sotto la
    scritta. Vedi il commento qui sopra per il perche' non si puo' fare in
    nessun altro modo.

    E se sotto la scritta non c'e' niente, si guarda DAVANTI: e' la legenda,
    col suo campione di colore. Sul Kinder Country la fascia arancione a
    tratteggio sotto la pinna non ha nessuna scritta sopra; il suo nome sta
    solo in legenda, "COVERED Area" accanto a un quadrato di PANTONE 1565 C.
    Vedi `_campione`.

    Vuoto se Ghostscript non c'e', se il file non scrive niente, o se ne'
    sotto l'etichetta ne' nel suo campione c'e' una lastra piena: in tutti
    quei casi non si e' imparato niente e non si tocca niente. Non costa
    nulla sui file senza etichette, che e' la maggioranza.
    """
    import shutil

    if not shutil.which("gs") or not _forse_etichette(pdf, page_no):
        return {}
    try:
        etichette = _etichette(pdf, page_no)
    except Exception:
        return {}
    if not etichette:
        return {}

    import numpy as np
    import pypdf

    try:
        mb = pypdf.PdfReader(pdf).pages[page_no].mediabox
        sx, sy = float(mb.left), float(mb.bottom)
        alto = float(mb.top) - sy
        lastre = mappe_lastre(pdf, page_no, dpi)
        if not lastre:
            return {}
        s = dpi / 72.0

        def piena(x0, y0, x1, y1):
            """La lastra piena nel riquadro (spazio della pagina), o None."""
            a0 = int(np.floor((x0 - sx) * s))
            a1 = int(np.ceil((x1 - sx) * s))
            b0 = int(np.floor((alto - (y1 - sy)) * s))
            b1 = int(np.ceil((alto - (y0 - sy)) * s))
            migliore, quota = None, 0.0
            for nome, mappa in lastre.items():
                h, w = mappa.shape
                z = mappa[max(0, b0):min(h, b1), max(0, a0):min(w, a1)]
                if not z.size:
                    continue
                # tiffsep: 255 = niente inchiostro, 0 = pieno
                q = float(((255 - z.astype(np.int16)) / 255.0
                           >= INCHIOSTRO_MINIMO).mean())
                if q > quota:
                    migliore, quota = nome, q
            return migliore if quota >= PIENO_MINIMO else None

        raggio = 72.0 / 6.0   # ~2 mm attorno al centro della scritta, in punti
        scritte, pieni = _oggetti(pdf, page_no)
        fuori = {}
        for x, y, dx, dy, corpo, lung, etichetta in etichette:
            # la scritta c'e' davvero, dove pypdf dice che comincia?
            if not any(a0 - corpo <= x <= a1 + corpo
                       and b0 - corpo <= y <= b1 + corpo
                       for a0, b0, a1, b1 in scritte):
                continue
            cx = x + dx * lung / 2.0 - dy * 0.35 * corpo
            cy = y + dy * lung / 2.0 + dx * 0.35 * corpo
            nome = piena(cx - raggio, cy - raggio, cx + raggio, cy + raggio)
            if nome is None:
                c = _campione(x, y, dx, dy, corpo, pieni)
                if c is not None:
                    # un filo di margine: il bordo del campione e' mezzo pixel
                    m = min(1.0, (c[2] - c[0]) / 4.0, (c[3] - c[1]) / 4.0)
                    nome = piena(c[0] + m, c[1] + m, c[2] - m, c[3] - m)
            if nome is not None:
                fuori.setdefault(nome, etichetta)
        return fuori
    except Exception:
        return {}


def lastra_nel_riquadro(pdf, x_mm, y_mm, w_mm, h_mm, page_no=0, dpi=36):
    """Quale lastra dipinge, piena, dentro questo riquadro.

    E' il modo in cui un riquadro *indicato a occhio* diventa una rimozione
    *esatta*: l'agente guarda il foglio e dice dove sta l'area riservata, il
    codice guarda chi ci mette l'inchiostro e toglie quella lastra per nome.
    L'errore dell'agente vale qualche millimetro di innesco, perche' il bordo
    vero non lo decide lui: lo decide la lastra.

    Il riquadro e' in millimetri dall'angolo in alto a sinistra del foglio,
    come per `measure_region` e `clean_artwork`.

    Restituisce `{}` se dentro il riquadro non c'e' nessuna lastra piena:
    vuol dire che li' non c'e' un'area riservata, e non si tocca niente.

    **Non decide da solo che sia un'area riservata.** Una lastra piena dentro
    un rettangolo puo' benissimo essere il fondo della grafica: su K Colazione
    Piu' la fascia `TEXT AREA` copre il 6,5% del foglio e `Kinder ORANGE`, che
    e' grafica, il 7,9%. Nessuna soglia separa le due cose - misurato - quindi
    la conferma e' l'occhio, e `copertura_foglio_pct` serve solo a dire quanto
    c'e' in gioco.
    """
    import numpy as np

    lastre = mappe_lastre(pdf, page_no, dpi)
    if not lastre:
        return {}
    s = dpi / 72.0
    x0, y0 = int(round(x_mm / PT2MM * s)), int(round(y_mm / PT2MM * s))
    x1 = int(round((x_mm + w_mm) / PT2MM * s))
    y1 = int(round((y_mm + h_mm) / PT2MM * s))
    migliore, quota, copertura = None, 0.0, 0.0
    for nome, mappa in lastre.items():
        h, w = mappa.shape
        z = mappa[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
        if z.size == 0:
            continue
        inchiostro = (255 - z.astype(np.int16)) / 255.0
        q = float((inchiostro >= INCHIOSTRO_MINIMO).mean())
        if q > quota:
            tutta = (255 - mappa.astype(np.int16)) / 255.0
            migliore, quota = nome, q
            copertura = float((tutta >= INCHIOSTRO_MINIMO).mean())
    if not migliore or quota < PIENO_MINIMO:
        return {}
    return dict(lastra=migliore, pieno_pct=round(100 * quota, 1),
                copertura_foglio_pct=round(100 * copertura, 2))
