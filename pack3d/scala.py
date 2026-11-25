"""
La scala del disegno, dalle quote: il punto 4 del piano di robustezza.

Il codice misura il pack sul disegno, in millimetri della pagina. Quasi
sempre il disegno e' in scala 1:1, ma non sempre: una tavola grande mandata
ridotta, un DT disegnato a meta' per stare sul foglio. Allora tutto viene
grande la meta', e le cifre delle quote, che dicono il doppio delle linee,
non tornano con niente (sugli astucci votavano anche il verso del foglio).

Chi ha disegnato le quote ha scritto la scala senza saperlo: il numero che
sta su una linea di quota diviso la lunghezza della linea. Qui si leggono, su
ogni pagina, prima di ogni lettura:

- **la quota misurata**: un numero scritto come testo, vicino a una linea
  sottile parallela (il numero sopra, o nel buco della linea), con le due
  estremita' della linea chiuse da un tratto perpendicolare - le linee di
  richiamo, o i lati del disegno. Conta solo vicino al disegno principale e
  se misura almeno `PARTE` del suo lato: le cifre di una tabella o di un
  riquadro piccolo si accordano per caso con qualsiasi scala;
- **la scala del cartiglio**: «scala 1:2», «scale», «Massstab», «echelle».

Se la scala non e' 1:1 il PDF si riscrive ingrandito (`riscrivi`) e prende
il posto di quello caricato: la lettura, il punteggio, il riscontro delle
quote, la texture e il controllo lavorano su un disegno 1:1, come sempre.
Lo spessore dei tratti non cambia per chi legge le penne: pdfium lo da' nel
telaio del tratto, senza la matrice aggiunta.

Quando si applica, da sola (le scelte del proprietario del 24 novembre 2026,
pack3d-casi `lavori/robustezza/punto4_scala.md`):

- almeno due quote distinte sulla stessa scala solita (1:4, 1:2, 2:1, 4:1),
  una che misura il disegno intero o quasi (`INTERA`), nessuna che dica 1:1;
- una quota sola, se il cartiglio dice la stessa scala;
- almeno tre quote d'accordo entro lo 0,5% su un rapporto non solito (un PDF
  stampato «adatta alla pagina»), dichiarato; vicino a 1:1 resta 1:1.

Le contraddizioni - quote contro quote, quote contro cartiglio, una quota
sola senza cartiglio, il cartiglio da solo - sono un **dubbio di scala**:
la scala con piu' quote (o quella del PDF), il dubbio scritto in cima ai
dettagli, e un DIFETTO (`difetti`) che manda il caso in coda anche col
controllo dell'AI d'accordo: un pack grande la meta' con la grafica giusta
all'AI puo' sembrare giusto. Senza quote, la scala del PDF, come prima.
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field

from .dieline import PT2MM

# il numero sulla linea diviso la linea: le scale solite oltre 1:1
SOLITE = (0.25, 0.5, 2.0, 4.0)
# quanto puo' sbagliare una quota per dirsi su una scala: mm della quota, o
# questa parte del suo valore
SCARTO_MM = 0.5
SCARTO_REL = 0.005
# un rapporto non solito vale con tante quote d'accordo entro questa parte;
# entro `QUASI_UNO` da 1 e' un arrotondamento del PDF, e resta 1:1
LIBERE = 3
LIBERE_REL = 0.005
QUASI_UNO = 0.03
# la quota: numero e linea a meno di questo (mm della pagina), il numero nel
# buco della linea fino a tanto, l'estremita' chiusa entro tanto
VICINO = 4.0
BUCO = 30.0
CHIUSA = 1.0
# una cella di tabella: una linea per parte del numero, a meno di tanto (mm)
CELLA = 3.0
# un tratto piu' spesso non e' una linea di quota (pt)
SOTTILE = 1.2
# la quota conta se misura almeno questa parte del lato del disegno; e una
# quota d'insieme ne misura almeno tanto
PARTE = 0.15
INTERA = 0.6
# un altro disegno della tavola ha almeno questa parte delle linee del principale
ALTRO = 0.02
# i numeri sotto non misurano niente di utile (raggi, tolleranze)
MINIMO = 3.0
# quante pagine si guardano
PAGINE = 6

CARTIGLIO = re.compile(
    r"(?i)(?<![a-z])(?:scala|scale|massstab|maßstab|[eé]chelle|escala)"
    r"\s*[:=.]?\s*(\d{1,3}(?:[.,]\d{1,2})?)\s*[:/]\s*(\d{1,3}(?:[.,]\d{1,2})?)(?![\d.,])")


@dataclass
class Quota:
    valore: float           # il numero scritto
    linea: float            # la linea che misura, mm della pagina
    asse: int               # 0 orizzontale, 1 verticale
    intera: bool            # misura il disegno intero o quasi

    @property
    def rapporto(self):
        return self.valore / self.linea

    def scala(self):
        """La scala solita (o 1) su cui sta, o None."""
        for s in (1.0,) + SOLITE:
            if abs(self.valore - s * self.linea) <= max(SCARTO_MM, SCARTO_REL * self.valore):
                return s
        return None

    def __str__(self):
        return "%s su una linea di %s mm" % (_n(self.valore), _n(self.linea))


@dataclass
class Pagina:
    numero: int
    quote: list = field(default_factory=list)
    cartiglio: tuple | None = None      # (testo, fattore)


@dataclass
class Scala:
    """La scala di un PDF: `fattore` per cui moltiplicare il disegno (2 per
    un disegno 1:2), le righe per chi carica, il dubbio, l'altra scala."""
    fattore: float = 1.0
    righe: list = field(default_factory=list)
    dubbio: str | None = None
    alternativa: float | None = None
    come: str = "pdf"           # pdf, quote, cartiglio, libero, opzione
    pagine: dict = field(default_factory=dict)  # pagina -> fattore

    @property
    def applicata(self):
        return self.fattore != 1.0

    def detto(self, altra=False):
        """Il dubbio com'e' scritto, o per il modello nell'altra scala
        (`altra`): li' non e' costruito come dice la fine del dubbio."""
        if not self.dubbio or not altra:
            return self.dubbio
        testa = self.dubbio.rsplit("; costruito", 1)[0]
        f = self.alternativa or 1.0
        return "%s; questo modello e' nell'altra scala, %s" % (
            testa, "quella del PDF" if f == 1.0 else nome(f))

    def difetti(self, altra=False):
        from .verifica import DIFETTO
        return ([DIFETTO + "dubbio di scala: " + self.detto(altra)] if self.dubbio else [])


def _n(v, cifre=1):
    return ("%.*f" % (cifre, v)).rstrip("0").rstrip(".").replace(".", ",")


def nome(f):
    """1:2 per 2, 2:1 per 0,5, 1:2,83 per un rapporto non solito."""
    if f >= 1:
        return "1:%s" % _n(f, 2)
    return "%s:1" % _n(1.0 / f, 2)


def misure(f):
    return {2.0: "misure raddoppiate", 0.5: "misure dimezzate"}.get(
        f, "misure moltiplicate per %s" % _n(f, 2) if f > 1 else
        "misure divise per %s" % _n(1.0 / f, 2))


# --------------------------------------------------------------------------- #
# la lettura di una pagina
# --------------------------------------------------------------------------- #
def _numeri(tp, page):
    """I numeri scritti come testo: `[(valore, (x0, y0, x1, y1), asse)]` in mm
    della pagina con la y dall'alto, e il testo della pagina."""
    import pypdfium2.raw as raw

    from .quote import NUMERO, testo_per_indice
    testo = testo_per_indice(tp)
    mx0, _my0, _mx1, my1 = page.get_mediabox()
    fuori = []
    for m in NUMERO.finditer(testo):
        try:
            v = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        if v < MINIMO:
            continue
        scatole = [tp.get_charbox(i) for i in range(m.start(1), m.end(1))]
        x0 = min(b[0] for b in scatole)
        x1 = max(b[2] for b in scatole)
        y0 = min(b[1] for b in scatole)
        y1 = max(b[3] for b in scatole)
        ang = raw.FPDFText_GetCharAngle(tp.raw, m.start(1))
        girato = ang > 0 and abs(((ang * 57.2958) % 180) - 90) < 20
        fuori.append((v, ((x0 - mx0) * PT2MM, (my1 - y1) * PT2MM,
                          (x1 - mx0) * PT2MM, (my1 - y0) * PT2MM), 1 if girato else 0))
    return fuori, testo


def _disegno(segs, w, h):
    """Il riquadro del disegno principale in mm, `(x0, y0, x1, y1)`, e quelli
    degli altri disegni tecnici della tavola (miniature, copie, legenda): `(
    principale, [altri])`, o None."""
    from .dieline import _gruppi, _technical_pens
    penne = _technical_pens(segs, w, h)
    if not penne:
        return None
    # il gruppo di tratti tecnici collegati con la lunghezza maggiore: il DT,
    # non le sue miniature, la legenda o il cartiglio (`dieline._gruppi`)
    # i pezzi corti contano: un DT a tratti spezzati (la variante
    # `spezzati`, pezzi di 3 mm) perdeva il disegno grande, e vinceva la
    # miniatura del cartiglio con le sue quote vere, che dicevano 1:5
    corto = 1.0 / PT2MM
    tec = [s for s in segs if s[4] in penne and s[3] - s[2] >= corto]
    gruppi = _gruppi(tec)
    if not gruppi:
        return None
    lunghi = [sum(sg[3] - sg[2] for sg, _r in g) for g in gruppi]

    def riquadro(g):
        return tuple(v * PT2MM for v in (min(r[0] for _s, r in g), min(r[1] for _s, r in g),
                                          max(r[2] for _s, r in g), max(r[3] for _s, r in g)))
    i = max(range(len(gruppi)), key=lambda i: lunghi[i])
    principale = riquadro(gruppi[i])
    if principale[2] - principale[0] <= 0 or principale[3] - principale[1] <= 0:
        return None
    # gli altri disegni con un po' di linee: le miniature, le copie tecniche
    altri = [riquadro(g) for j, g in enumerate(gruppi)
             if j != i and lunghi[j] >= ALTRO * lunghi[i]]
    return principale, altri


def _distanza(r, x, y):
    return math.hypot(max(r[0] - x, 0, x - r[2]), max(r[1] - y, 0, y - r[3]))


def _la_quota(r, k, L):
    """Se il disegno `r` e' la quota stessa, staccata dal DT: la sua linea
    coi richiami, larga quanto lei e bassa."""
    lungo, corto = (r[2] - r[0], r[3] - r[1]) if k == "H" else (r[3] - r[1], r[2] - r[0])
    return lungo <= L + 10.0 and corto <= 15.0


def _miniatura(r, principale):
    """Un altro disegno molto piu' piccolo del principale: una miniatura,
    in un'altra scala. Le copie grandi uguali hanno le loro quote, buone."""
    def diagonale(q):
        return math.hypot(q[2] - q[0], q[3] - q[1])
    return diagonale(r) < 0.5 * diagonale(principale)


def _quote(numeri, segs, disegno):
    """Le quote misurate vicino al disegno principale, una per numero:
    `disegno` e' quello di `_disegno`. Una quota piu' vicina a un altro
    disegno della tavola che al principale e' sua (la miniatura del
    cartiglio porta le quote vere, ma e' in un'altra scala)."""
    riquadro, altri = disegno
    X0, Y0, X1, Y1 = riquadro
    lati = (X1 - X0, Y1 - Y0)
    margine = max(40.0, 0.5 * max(lati))
    per = {"H": {}, "V": {}}
    for k, c, a, b, st in segs:
        if st[0] > SOTTILE:
            continue
        c, a, b = c * PT2MM, a * PT2MM, b * PT2MM
        per[k].setdefault(int(c // 1), []).append((a, b, c))

    def vicini(k, c, d):
        for chiave in range(int((c - d) // 1), int((c + d) // 1) + 1):
            yield from per[k].get(chiave, ())

    def chiusa(k, c, e):
        o = "V" if k == "H" else "H"
        return any(abs(cc - e) <= CHIUSA and a - CHIUSA <= c <= b + CHIUSA
                   for a, b, cc in vicini(o, e, CHIUSA))

    def in_cella(k, lo, hi, t0, t1):
        # il numero chiuso fra due linee parallele, una per parte, a pochi
        # millimetri e lunghe almeno quanto lui: la cella di una tabella. Il
        # numero di una quota ha la linea da una parte sola, o lo attraversa
        sopra = sotto = False
        for a, b, c in vicini(k, (t0 + t1) / 2, (t1 - t0) / 2 + CELLA):
            if a > lo + 0.2 or b < hi - 0.2:
                continue
            if t0 - CELLA <= c < t0 - 0.1:
                sopra = True
            elif t1 + 0.1 < c <= t1 + CELLA:
                sotto = True
        return sopra and sotto

    trovate, viste = [], set()
    for v, (x0, y0, x1, y1), asse in numeri:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if not (X0 - margine <= cx <= X1 + margine and Y0 - margine <= cy <= Y1 + margine):
            continue
        k = "H" if asse == 0 else "V"
        lo, hi = (x0, x1) if asse == 0 else (y0, y1)
        t0, t1 = (y0, y1) if asse == 0 else (x0, x1)
        mezzo = (lo + hi) / 2
        if in_cella(k, lo, hi, t0, t1):
            continue
        righe = {}
        for a, b, c in vicini(k, (t0 + t1) / 2, (t1 - t0) / 2 + VICINO):
            righe.setdefault(round(c, 1), []).append((a, b))
        migliore = None
        for c, pezzi in righe.items():
            d = 0.0 if t0 <= c <= t1 else min(abs(c - t0), abs(c - t1))
            if d > VICINO:
                continue
            fila = []
            for a, b in sorted(pezzi):
                if fila:
                    buco = a - fila[-1][1]
                    # i pezzi che si toccano sono una linea; un buco solo se
                    # ci sta dentro il numero
                    if buco <= 0.5 or (buco <= BUCO and fila[-1][1] - 1 <= lo
                                       and hi <= a + 1):
                        fila[-1][1] = max(fila[-1][1], b)
                        continue
                fila.append([a, b])
            for a, b in fila:
                L = b - a
                if L < 5.0 or not a <= mezzo <= b:
                    continue
                if abs(mezzo - (a + b) / 2) > 0.2 * L + 3.0:
                    continue
                if not (chiusa(k, c, a) and chiusa(k, c, b)):
                    continue
                if migliore is None or d < migliore[1]:
                    migliore = (L, d, (k, c, round(a, 1), round(b, 1)))
        if migliore is None:
            continue
        L, _d, linea = migliore
        _k, c, a, b = linea
        mx, my = ((a + b) / 2, c) if k == "H" else (c, (a + b) / 2)
        L0 = b - a
        # il disegno a cui la quota sta accanto: il principale, o una copia
        # grande come lui (la tavola coi DT tecnici ripetuti); una miniatura
        # ha le quote vere ma un'altra scala, e non conta
        suo = min([riquadro] + [r for r in altri if not _la_quota(r, k, L0)],
                  key=lambda r: _distanza(r, mx, my))
        if suo is not riquadro and _miniatura(suo, riquadro):
            continue
        lato = (suo[2] - suo[0], suo[3] - suo[1])[asse]
        if L < PARTE * lato:
            continue
        chiave = (round(v, 1), round(L), asse)
        if chiave in viste:
            continue
        viste.add(chiave)
        trovate.append((linea, Quota(v, L, asse, L >= INTERA * lato)))
    # una linea di quota porta un numero solo: una linea con tanti numeri
    # diversi e' una tabella, un testo, la riga di una legenda
    per_linea = {}
    for linea, q in trovate:
        per_linea.setdefault(linea, set()).add(round(q.valore, 1))
    return [q for linea, q in trovate if len(per_linea[linea]) == 1]


def _cartiglio(testo):
    for m in CARTIGLIO.finditer(testo):
        try:
            a, b = (float(g.replace(",", ".")) for g in m.groups())
        except ValueError:
            continue
        if a > 0 and b > 0 and 0.1 <= b / a <= 10:
            return (" ".join(m.group(0).split()), b / a)
    return None


def leggi_pagine(pdf, pagine=PAGINE):
    """Le quote misurate e il cartiglio di ogni pagina: `[Pagina]`."""
    import pypdfium2 as pdfium

    from .tracciati import segmenti
    fuori = []
    doc = pdfium.PdfDocument(pdf)
    try:
        n = min(len(doc), pagine)
        for i in range(n):
            page = doc[i]
            tp = page.get_textpage()
            try:
                numeri, testo = _numeri(tp, page)
            finally:
                tp.close()
            p = Pagina(i, cartiglio=_cartiglio(testo))
            if numeri:
                segs, w, h = segmenti(pdf, i)
                disegno = _disegno(segs, w, h)
                if disegno is not None:
                    p.quote = _quote(numeri, segs, disegno)
            fuori.append(p)
    finally:
        doc.close()
    return fuori


# --------------------------------------------------------------------------- #
# la decisione
# --------------------------------------------------------------------------- #
def _elenco(quote, quante=3):
    q = sorted(quote, key=lambda q: -q.linea)[:quante]
    return ", ".join(str(x) for x in q)


def decidi(p):
    """`(fattore, come, dubbio, alternativa, prove)` di una pagina; `fattore`
    None se la pagina non dice niente (ne' quote ne' cartiglio)."""
    per = {}
    libere = []
    for q in p.quote:
        s = q.scala()
        if s is None:
            libere.append(q)
        else:
            per.setdefault(s, []).append(q)
    uno = per.pop(1.0, [])
    cart = p.cartiglio[1] if p.cartiglio else None
    if cart is not None and abs(cart - 1.0) <= QUASI_UNO:
        cart = 1.0
    testo_cart = ("il cartiglio scrive «%s»" % p.cartiglio[0]
                  if p.cartiglio else "")
    k, qk = None, []
    if per:
        k = max(per, key=lambda s: (len(per[s]), any(q.intera for q in per[s])))
        qk = per[k]
    # due quote, e una d'insieme o una per asse: due cifre piccole sullo
    # stesso lato si accordano piu' facilmente per caso
    forti = len(qk) >= 2 and (any(q.intera for q in qk)
                              or len({q.asse for q in qk}) == 2)
    if forti and not uno:
        if cart is not None and cart != k:
            return (k, "quote", "le quote dicono %s (%s), ma %s; costruito in scala %s"
                    % (nome(k), _elenco(qk), testo_cart, nome(k)), cart, qk)
        return (k, "quote", None, None, qk)
    if len(qk) >= 2 and uno:
        tiene, altra = (k, 1.0) if len(qk) > len(uno) else (1.0, k)
        return (tiene, "quote", "le quote si contraddicono: %s (%s) e 1:1 (%s); costruito "
                "in scala %s" % (nome(k), _elenco(qk), _elenco(uno), nome(tiene)),
                altra, qk if tiene == k else uno)
    if len(qk) == 1 and qk[0].intera and not uno:
        if cart == k:
            return (k, "cartiglio", None, None, qk)
        return (1.0, "pdf", "una quota sola dice %s (%s)%s; costruito alla scala del PDF"
                % (nome(k), qk[0], ", e %s" % testo_cart if testo_cart else
                   ", e il cartiglio non scrive la scala"), k, qk)
    if not per and len(libere) >= LIBERE:
        r = sorted(q.rapporto for q in libere)
        for i in range(len(r) - LIBERE + 1):
            grappolo = r[i:i + LIBERE]
            if grappolo[-1] / grappolo[0] - 1 <= 2 * LIBERE_REL:
                f = grappolo[len(grappolo) // 2]
                accordo = [q for q in libere if abs(q.rapporto / f - 1) <= LIBERE_REL]
                if abs(f - 1.0) <= QUASI_UNO or not any(q.intera for q in accordo):
                    break
                if uno:
                    return (1.0, "pdf", "%d quote dicono un rapporto di %s (%s), %d "
                            "dicono 1:1 (%s); costruito alla scala del PDF"
                            % (len(accordo), nome(f), _elenco(accordo), len(uno),
                               _elenco(uno)), f, uno)
                return (f, "libero", None, None, accordo)
    if cart is not None and cart != 1.0:
        if uno:
            return (1.0, "pdf", "%s, ma le quote dicono 1:1 (%s); costruito alla "
                    "scala del PDF" % (testo_cart, _elenco(uno)), cart, uno)
        return (1.0, "pdf", "%s, ma nessuna quota lo conferma; costruito alla scala "
                "del PDF" % testo_cart, cart, [])
    if uno or (cart == 1.0):
        return (1.0, "pdf", None, None, uno)
    return (None, "pdf", None, None, [])


def leggi(pdf, opzione=None):
    """La scala del PDF: `Scala`. Con `opzione` (la scala chiesta, come
    fattore: 2 per 1:2) non si legge niente."""
    if opzione:
        f = float(opzione)
        s = Scala(fattore=f, come="opzione")
        if f != 1.0:
            s.righe = ["DISEGNO IN SCALA %s, come chiesto: %s" % (nome(f), misure(f))]
        return s
    pagine = leggi_pagine(pdf)
    decise = {}
    s = Scala()
    principale = None
    for p in pagine:
        f, come, dubbio, alt, prove = decidi(p)
        if f is None:
            continue
        decise[p.numero] = f
        if principale is None or (dubbio and not principale[2]) or (
                f != 1.0 and principale[0] == 1.0 and not principale[2]):
            principale = (f, come, dubbio, alt, prove, p)
    if principale is None:
        return s
    f, come, dubbio, alt, prove, p = principale
    # le pagine che non dicono niente prendono la scala del file, se le
    # pagine che parlano sono d'accordo
    if len(set(decise.values())) == 1:
        s.pagine = {q.numero: decise.get(q.numero, f) for q in pagine}
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(pdf)
            n = len(doc)
            doc.close()
            for i in range(len(pagine), n):
                s.pagine[i] = f
        except Exception:                   # noqa: BLE001
            pass
    else:
        s.pagine = dict(decise)
    s.fattore, s.come, s.dubbio, s.alternativa = f, come, dubbio, alt
    if s.applicata:
        perche = {"quote": "le quote: %s" % _elenco(prove),
                  "cartiglio": "la quota %s, come scrive il cartiglio, «%s»"
                               % (_elenco(prove, 1), p.cartiglio[0] if p.cartiglio else ""),
                  "libero": "un rapporto non solito, forse un PDF adattato alla "
                            "pagina; le quote: %s" % _elenco(prove)}.get(come, "")
        if come == "quote" and p.cartiglio and not dubbio:
            perche += "; come scrive il cartiglio, «%s»" % p.cartiglio[0]
        s.righe.append("DISEGNO IN SCALA %s: %s (%s)" % (nome(f), misure(f), perche))
    if dubbio:
        s.righe.append("DUBBIO DI SCALA: %s. Controllare il DT" % dubbio)
    return s


# --------------------------------------------------------------------------- #
# la riscrittura
# --------------------------------------------------------------------------- #
RIQUADRI = ("/MediaBox", "/CropBox", "/BleedBox", "/TrimBox", "/ArtBox")


def riscrivi(pdf, uscita, pagine, riga=None):
    """Il PDF con ogni pagina ingrandita del suo fattore (`{pagina: f}`):
    il contenuto e i riquadri della pagina. Il documento si clona intero, cosi'
    restano i livelli (vedi `artwork.pagina_unica`)."""
    from pypdf import PdfWriter, Transformation
    from pypdf.generic import ArrayObject, FloatObject, NameObject
    w = PdfWriter(clone_from=pdf)
    for i, p in enumerate(w.pages):
        f = pagine.get(i, 1.0)
        if f == 1.0:
            continue
        mb = [float(v) for v in p.mediabox]
        # i riquadri che la pagina eredita si scrivono sulla pagina prima di
        # cambiarli: la MediaBox puo' stare nel nodo delle pagine
        presenti = {nm: [float(v) for v in getattr(p, nm[1:].lower())]
                    for nm in RIQUADRI if nm in p or nm == "/MediaBox"}
        presenti.setdefault("/MediaBox", mb)
        p.add_transformation(Transformation().scale(f, f))
        for nm, r in presenti.items():
            p[NameObject(nm)] = ArrayObject(FloatObject(v * f) for v in r)
    if riga:
        w.add_metadata({CHIAVE: riga})
    tmp = uscita + ".tmp"
    with open(tmp, "wb") as fh:
        w.write(fh)
    os.replace(tmp, uscita)
    return uscita


def chiesta(valore):
    """L'opzione `scala` della richiesta come fattore: 2, "2", "1:2" -> 2;
    "2:1" -> 0,5; vuota -> None. ValueError se non si capisce."""
    if valore in (None, "", 0):
        return None
    try:
        if isinstance(valore, str) and ":" in valore:
            a, b = (float(x.replace(",", ".")) for x in valore.split(":"))
            f = b / a
        else:
            f = float(str(valore).replace(",", "."))
    except (ValueError, ZeroDivisionError):
        raise ValueError("La scala del disegno si scrive come 1:2, 2:1 o come "
                         "il fattore (2 per un disegno in scala 1:2)") from None
    if not 0.05 <= f <= 20:
        raise ValueError("La scala del disegno %s non e' plausibile" % valore)
    return f


def righe_di(scale, nomi=()):
    """Le righe di tutti i PDF della richiesta, col nome del file se sono
    piu' d'uno."""
    fuori = []
    for k, s in enumerate(scale):
        for r in s.righe:
            if len(scale) > 1 and k < len(nomi):
                testa, _, resto = r.partition(": ")
                r = "%s (%s): %s" % (testa, nomi[k], resto)
            fuori.append(r)
    return fuori


def altra(s):
    """L'altra scala da provare come tentativo (`pack3d.tentativi`): quella
    che le quote o il cartiglio dicevano, se la scala e' in dubbio; la scala
    del PDF, se quella delle quote e' applicata; None se non ce n'e' (niente
    quote, o la scala chiesta)."""
    if s.come == "opzione":
        return None
    if s.dubbio and s.alternativa:
        return s.alternativa
    if s.applicata:
        return 1.0
    return None


def quando(scale):
    """Quando provare l'altra scala, per il giro dei tentativi: "prima" se
    una scala e' in dubbio, "ultima" se le scale sono applicate senza dubbi,
    None se nessun PDF ha un'altra scala."""
    if any(s.dubbio and altra(s) for s in scale):
        return "prima"
    if any(altra(s) for s in scale):
        return "ultima"
    return None


def righe_altra(scale, nomi=()):
    """Le righe di un modello costruito nell'altra scala: al posto di quelle
    di `righe_di`."""
    fuori = []
    for k, s in enumerate(scale):
        f = altra(s)
        chi = " (%s)" % nomi[k] if len(scale) > 1 and k < len(nomi) else ""
        if f is None:
            fuori += [r.replace(": ", "%s: " % chi, 1) if chi else r for r in s.righe]
        elif f == 1.0:
            # l'altra e' quella del PDF solo se la prima era riscritta
            fuori.append("DISEGNO ALLA SCALA DEL PDF%s, l'altra scala: la prima "
                         "lettura era in scala %s" % (chi, nome(s.fattore)))
        else:
            fuori.append("DISEGNO IN SCALA %s%s, l'altra scala: %s"
                         % (nome(f), chi, misure(f)))
        if s.dubbio:
            fuori.append("DUBBIO DI SCALA%s: %s. Controllare il DT"
                         % (chi, s.detto(altra=f is not None)))
    return fuori


def in_altra_scala(caricati, scale, cartella):
    """I PDF del tentativo nell'altra scala: per ognuno quello caricato
    riscritto nell'altra scala (o com'e', se l'altra e' quella del PDF);
    `None` al posto di quelli che non ne hanno una."""
    fuori = []
    for k, (p, s) in enumerate(zip(caricati, scale)):
        f = altra(s)
        if f is None:
            fuori.append(None)
        elif f == 1.0:
            fuori.append(p)
        else:
            fuori.append(in_scala(p, cartella, 100 + k, f)[0])
    return fuori


# la scala applicata scritta nel PDF riscritto, per la tavola della lettura
# (`pack3d.lettura`), che lo riceve da chi legge e non sa da dove viene
CHIAVE = "/Pack3dScala"


def dichiarata(pdf):
    """La riga della scala scritta nel PDF da `riscrivi`, o None."""
    try:
        from pypdf import PdfReader
        v = (PdfReader(pdf).metadata or {}).get(CHIAVE)
        return str(v) if v else None
    except Exception:                       # noqa: BLE001
        return None


def in_scala(pdf, cartella, k=0, opzione=None):
    """`(pdf da leggere, Scala)`: il PDF caricato riscritto in scala se serve,
    in `cartella`; quello di prima se la scala e' 1:1. Una lettura della
    scala che si rompe non ferma niente: la scala resta quella del PDF."""
    try:
        s = leggi(pdf, opzione)
    except Exception as e:                  # noqa: BLE001
        return pdf, Scala(righe=["scala del disegno non letta (%s): quella del PDF"
                                 % type(e).__name__])
    if not s.applicata:
        return pdf, s
    if not s.pagine:
        s.pagine = {0: s.fattore}
        try:
            from pypdf import PdfReader
            s.pagine = {i: s.fattore for i in range(len(PdfReader(pdf).pages))}
        except Exception:                   # noqa: BLE001
            pass
    nuovo = os.path.join(cartella, "scala%d.pdf" % k)
    riscrivi(pdf, nuovo, s.pagine, "Disegno in scala %s: %s" % (nome(s.fattore),
                                                               misure(s.fattore)))
    return nuovo, s
