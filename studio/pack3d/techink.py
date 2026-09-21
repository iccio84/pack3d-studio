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
    "covered area", "neutral area",
)

# Nomi corti o ambigui: qui la sottostringa farebbe danni - "cut" prenderebbe
# mezzo dizionario, "td" qualunque parola con quelle due lettere - e si
# confrontano interi.
SIGLE_TECNICHE = {
    "all", "none", "cut", "td", "dt", "white", "bianco", "bleed",
    "abbondanza", "fold", "falz", "rill", "taglio", "stand", "stand blau",
    "label", "check", "note", "notes",
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
COPERTURE_FRASI = (
    "varnish", "vernice", "lack", "coating",
    "cold seal", "coldseal", "opaque white", "underprint", "coprente",
)
# "white" solo intero: come sottostringa prenderebbe "White Chocolate", che e'
# un colore dell'artwork
COPERTURE_SIGLE = {"white", "bianco"}


def copertura(nome):
    """Vero se questa lastra copre la grafica invece di tracciarla."""
    n = _norm(nome)
    if n in RESERVED:
        return False
    return n in COPERTURE_SIGLE or any(f in n for f in COPERTURE_FRASI)


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
