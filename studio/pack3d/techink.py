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

# nomi ricorrenti nei file che i Processing Steps non ce l'hanno
VENDOR_NAMES = {
    "dieline", "die line", "die-line", "cutcontour", "cut contour",
    "cut", "thru-cut", "thrucut", "kiss cut", "kisscut",
    "crease", "cordonatura", "fold", "falz", "rill",
    "perf", "perfo", "perforation", "glue", "gluelap", "coldseal", "cold seal",
    "white", "bianco", "opaque white", "underprint",
    "varnish", "vernice", "lack", "gloss varnish", "matt varnish",
    "waterbased varnish", "uv varnish", "spot varnish",
    "technical", "tecnico", "stanze", "stanz", "taglio", "fustella",
    "braille", "bleed", "abbondanza", "registration", "reg marks",
    "all", "none", "legend", "dimension", "dimensions",
    "print free", "printfree", "print free area", "ink free", "inkfree",
    "stand", "stand blau", "label", "eyemark", "eye mark",
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
        if group or ptype:
            found[ref.idnum if hasattr(ref, "idnum") else id(g)] = dict(
                name=name, group=group, type=ptype)
    return found


def technical_separations(page):
    """Separazioni il cui nome le colloca fra le lastre tecniche."""
    out = {}
    res = page.get("/Resources") or {}
    cs = res.get("/ColorSpace")
    if not cs:
        return out
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
            if n in RESERVED and n != "all":
                continue
            if n in VENDOR_NAMES or n in ISO_TYPES or n in ISO_GROUPS:
                out[str(key)] = n
                break
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
        drop = {k: v for k, v in steps.items()
                if (v["group"] or "") in ISO_GROUPS}
        return dict(level=1, method="ISO 19593-1 Processing Steps",
                    certainty="esatta", ocgs=drop, separations={},
                    detail=sorted({v["group"] for v in drop.values() if v["group"]}))

    seps = technical_separations(page)
    if seps:
        return dict(level=2, method="nomi delle separazioni",
                    certainty="alta, da incrociare con lo spessore",
                    ocgs={}, separations=seps, detail=sorted(set(seps.values())))

    return dict(level=3, method="euristica su spessore e colore",
                certainty="stimata", ocgs={}, separations={}, detail=[])
