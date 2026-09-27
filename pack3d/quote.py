"""
Le quote scritte sul file: il riscontro delle misure prese dal disegno.

Il pack si misura dal disegno tecnico, e il disegno tecnico si puo' leggere
male: una linea che manca, tre guide scambiate per tre pieghe, una fascia
bianca della grafica presa per il margine della pinna. Chi ha preparato il
file pero' le misure le ha anche SCRITTE, di solito nella miniatura del DT in
un angolo della tavola, come catene di quote lungo i due assi:

    Colazione, lungo il passo:   20 | 37,5 | 215 | 37,5 | 20      = 330
    Colazione, lungo il nastro:  20 | 5 | 66,5 | 7 | 57 | ... | 20 = 460

Quando ci sono come testo, sono il riscontro piu' forte che esista: un numero
che il progettista ha scritto, non uno che abbiamo dedotto. Qui non si usano
mai per costruire - la costruzione resta sul disegno - ma per dire se il
disegno e' stato letto giusto.

Una quota sola non conferma niente: un "20" lo scrive anche la tabella
nutrizionale. Conta la CATENA: numeri allineati sullo stesso asse, in fila,
che sommano alla misura totale. Che una catena intera torni con le nostre
misure per caso non succede.

Sul K Tronky le quote sono vettorializzate e non si leggono: lo si dice, e le
misure restano quelle del disegno, da controllare a occhio sulla miniatura.
"""
from __future__ import annotations

import re

from .dieline import PT2MM

# un numero da quota: 20, 37.5, 37,5 - non 1.234 ne' un pezzo di codice
NUMERO = re.compile(r"(?<![\w.,])(\d{1,4}(?:[.,]\d{1,2})?)(?![\w.,])")
# quanto possono stare storti due numeri della stessa catena, in mm
ALLINEATI = 2.0
# quanto puo' sbagliare una somma per dirsi uguale, in mm
SCARTO = 0.6


def numeri(pdf, page_no=0):
    """I numeri scritti come testo: `[(valore, lungo, traverso, asse)]`.

    `asse` e' 0 per il testo orizzontale e 1 per quello girato di 90 o 270
    gradi; `lungo` e' la posizione lungo la direzione di lettura, `traverso`
    quella perpendicolare, in mm. Una catena di quote sta su un traverso solo.
    """
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    fuori = []
    doc = pdfium.PdfDocument(pdf)
    try:
        page = doc[page_no]
        tp = page.get_textpage()
        testo = tp.get_text_range()
        mx0, _my0, _mx1, my1 = page.get_mediabox()
        for m in NUMERO.finditer(testo):
            try:
                v = float(m.group(1).replace(",", "."))
            except ValueError:
                continue
            i = m.start()
            sx, _giu, _dx, su = tp.get_charbox(i)
            ang = raw.FPDFText_GetCharAngle(tp.raw, i)
            x = (sx - mx0) * PT2MM
            y = (my1 - su) * PT2MM
            girato = ang > 0 and abs(((ang * 57.2958) % 180) - 90) < 20
            fuori.append((v, y, x, 1) if girato else (v, x, y, 0))
        tp.close()
    finally:
        doc.close()
    return fuori


def catene(nums, totale):
    """Le catene di quote che sommano a `totale`: `[[v1, v2, ...]]`.

    Si raggruppano i numeri per asse e per traverso, si mettono in fila lungo
    la lettura, si tolgono quelli che valgono gia' il totale - la quota
    d'insieme sta di solito in mezzo alla catena, sulla stessa riga - e si
    cercano le finestre consecutive che sommano al totale.
    """
    gruppi = []
    for v, lungo, trav, asse in sorted(nums, key=lambda n: (n[3], n[2])):
        for g in gruppi:
            if g["asse"] == asse and abs(g["trav"] - trav) <= ALLINEATI:
                g["n"].append((lungo, v))
                break
        else:
            gruppi.append(dict(asse=asse, trav=trav, n=[(lungo, v)]))
    fuori = []
    for g in gruppi:
        fila = [v for _l, v in sorted(g["n"])
                if abs(v - totale) > SCARTO]
        for i in range(len(fila)):
            s = 0.0
            for j in range(i, len(fila)):
                s += fila[j]
                if abs(s - totale) <= SCARTO and j > i:
                    fuori.append(fila[i:j + 1])
                    break
                if s > totale + SCARTO:
                    break
    return fuori


def riscontro_testate(pdf, passo, pinna, gola, page_no=0):
    """Le testate del flowpack contro le quote scritte. Una riga, o None.

    La catena attesa lungo il passo e' `pinna | gola | corpo | gola | pinna`,
    o `pinna | corpo | pinna` senza gola. Se il file ne scrive una che somma
    al passo, si dice se torna; se ne scrive una diversa, lo si GRIDA, perche'
    vuol dire che il disegno e' stato letto male.
    """
    try:
        nums = numeri(pdf, page_no)
    except Exception:
        return None
    if not nums:
        return ("quote del file non leggibili come testo (vettorializzate?): "
                "passo e testate solo dal disegno, da controllare sulla "
                "miniatura")
    corpo = passo - 2.0 * (pinna + gola)
    attesa = ([pinna, gola, corpo, gola, pinna] if gola
              else [pinna, corpo, pinna])
    # Lungo il passo il pack e' simmetrico, e la sua catena anche. Con una
    # quarantina di numeri sul foglio una fila che somma al passo si trova
    # anche per caso - su Colazione 7 | 135 | 7 | 57 | 7 | 71,5 | 40 | 5, che
    # sono pezzi del nastro - ma una fila simmetrica per caso no.
    trovate = [c for c in catene(nums, passo)
               if len(c) >= 3 and all(abs(a - b) <= SCARTO
                                      for a, b in zip(c, reversed(c)))]
    if not trovate:
        return ("nessuna catena di quote che torni col passo di %.1f mm: "
                "testate solo dal disegno, da controllare sulla miniatura"
                % passo)
    for c in trovate:
        if len(c) == len(attesa) and all(abs(a - b) <= SCARTO
                                         for a, b in zip(c, attesa)):
            return ("testate confermate dalle quote del file: %s = %s"
                    % (" | ".join("%g" % v for v in c), "%g" % passo))
    c = trovate[0]
    return ("QUOTE DEL FILE DIVERSE DALLE TESTATE LETTE: il file scrive %s = "
            "%g, dal disegno esce %s. Controllare il DT"
            % (" | ".join("%g" % v for v in c), passo,
               " | ".join("%.1f" % v for v in attesa)))


# --------------------------------------------------------------------------- #
# astucci e vassoi: stessa regola, altre catene
# --------------------------------------------------------------------------- #
# "70 x 40 x 150" nel cartiglio: la terna delle dimensioni, come la scrive chi
# prepara la tavola. Vale per l'astuccio montato e per il vassoio.
TERNA = re.compile(r"(?<![\w.,])(\d{1,4}(?:[.,]\d{1,2})?)\s*[xX×*]\s*"
                   r"(\d{1,4}(?:[.,]\d{1,2})?)\s*[xX×*]\s*"
                   r"(\d{1,4}(?:[.,]\d{1,2})?)(?![\w.,])")
# Interne o esterne: fra le due c'e' lo spessore del cartoncino, un millimetro
# o poco piu' per parte. Una terna del cartiglio entro questo torna.
CARTIGLIO = 1.5
# Oltre questo scarto relativo una terna scritta non parla di questo pack: e'
# un altro numero del foglio, e non si grida.
ESTRANEA = 0.2


def terne(pdf, page_no=0):
    """Le terne `a x b x c` scritte come testo, ordinate: `[(a, b, c)]`."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        tp = doc[page_no].get_textpage()
        testo = tp.get_text_range()
        tp.close()
    finally:
        doc.close()
    fuori = []
    for m in TERNA.finditer(testo):
        try:
            fuori.append(tuple(sorted(float(g.replace(",", "."))
                                      for g in m.groups())))
        except ValueError:
            continue
    return fuori


def _riscontro(pdf, cosa, attese, dimensioni, page_no=0):
    """Le misure lette dal DT contro le quote scritte. Una riga, o None.

    `attese` sono le catene che il DT fa aspettare, `[(nome, [mm, ...])]`;
    `dimensioni` la terna del pack montato. Si cerca prima la terna nel
    cartiglio, poi le catene lungo gli assi, e si grida solo quando il file
    parla DI QUESTO pack e dice un'altra cosa: una catena lunga uguale, con la
    stessa somma, e almeno meta' dei pezzi uguali ai nostri - un numero preso
    a caso dal foglio non ci arriva - oppure una terna che ci somiglia entro
    il 20% ma non torna.
    """
    try:
        nums = numeri(pdf, page_no)
        scritte = terne(pdf, page_no)
    except Exception:
        return None
    if not nums:
        return ("quote del file non leggibili come testo (vettorializzate?): "
                "%s solo dal disegno, da controllare sulla miniatura" % cosa)
    confermate, diverse = [], []
    nostra = tuple(sorted(dimensioni))
    for t in scritte:
        scarti = [abs(a - b) for a, b in zip(t, nostra)]
        if max(scarti) <= CARTIGLIO:
            confermate.append("cartiglio %s" % " x ".join("%g" % v for v in t))
        elif all(s <= ESTRANEA * max(b, 1.0) for s, b in zip(scarti, nostra)):
            diverse.append("il cartiglio scrive %s, dal disegno esce %s"
                           % (" x ".join("%g" % v for v in t),
                              " x ".join("%.1f" % v for v in nostra)))
    for nome, attesa in attese:
        if len(attesa) < 2:
            continue
        totale = sum(attesa)
        for c in catene(nums, totale):
            if len(c) != len(attesa):
                continue
            for verso in (attesa, list(reversed(attesa))):
                uguali = sum(abs(a - b) <= SCARTO for a, b in zip(c, verso))
                if uguali == len(c):
                    confermate.append("%s %s = %g" % (
                        nome, " | ".join("%g" % v for v in c), totale))
                    break
                if uguali * 2 >= len(c):
                    diverse.append("%s: il file scrive %s, dal disegno esce %s"
                                   % (nome, " | ".join("%g" % v for v in c),
                                      " | ".join("%.1f" % v for v in verso)))
                    break
    if diverse:
        return ("QUOTE DEL FILE DIVERSE DAL DISEGNO: %s. Controllare il DT"
                % "; ".join(dict.fromkeys(diverse)))
    if confermate:
        return ("%s confermati dalle quote del file: %s"
                % (cosa[0].upper() + cosa[1:], "; ".join(dict.fromkeys(confermate))))
    return ("nessuna quota del file che torni con %s: misure solo dal "
            "disegno, da controllare sulla miniatura" % cosa)


def riscontro_astuccio(pdf, d, page_no=0):
    """Pannelli e alette dell'astuccio contro le quote scritte.

    Le catene attese sono la fila del fronte - i pannelli che gli stanno
    accanto, da sinistra a destra - e la sua colonna, con le alette sopra e
    sotto: sono le due righe di quote che un DT d'astuccio porta quasi
    sempre, e il cartiglio aggiunge la terna L x P x H.
    """
    P = d.panels or {}
    f = P.get("front")
    if f is None:
        return None

    def sovrapposti(a0, a1, b0, b1):
        return min(a1, b1) - max(a0, b0) > 0.5 * min(a1 - a0, b1 - b0)

    riga = sorted((p for p in P.values() if sovrapposti(p.y0, p.y1, f.y0, f.y1)),
                  key=lambda p: p.x0)
    colonna = sorted((p for p in P.values() if sovrapposti(p.x0, p.x1, f.x0, f.x1)),
                     key=lambda p: p.y0)
    attese = [("in larghezza", [round(p.w_mm, 1) for p in riga]),
              ("in altezza", [round(p.h_mm, 1) for p in colonna])]
    return _riscontro(pdf, "pannelli e alette", attese, d.dims_mm, page_no)


def riscontro_vassoio(pdf, v, d, page_no=0):
    """Fondo e pareti del vassoio contro le quote scritte.

    Le catene attese sono le cinque colonne e le tre fasce della griglia -
    parete, cordonatura, fondo, cordonatura, parete - e la terna e' quella del
    vassoio montato.
    """
    xs = sorted({round(t, 2) for t in d.xs})
    ys = sorted({round(t, 2) for t in d.ys})
    attese = [("in larghezza", [round((b - a) * PT2MM, 1) for a, b in zip(xs, xs[1:])]),
              ("in altezza", [round((b - a) * PT2MM, 1) for a, b in zip(ys, ys[1:])])]
    return _riscontro(pdf, "fondo e pareti", attese, v.dims_mm, page_no)


# --------------------------------------------------------------------------- #
# la miniatura vettoriale: quando le quote non sono testo
# --------------------------------------------------------------------------- #
# Una tavola porta spesso il disegno tecnico piu' volte: le copie per i
# tecnicismi di stampa - supporto trasparente, alluminio, battuta di bianco,
# aree coperte - e la miniatura del cartiglio. Sono lo STESSO disegno in
# scala, e quando le quote sono vettorializzate, come sul Kinder Cards T2, sono
# l'unico riscontro che il codice sappia leggere: "forma e proporzioni dalla
# miniatura, scala dal disegno grande".
#
# Una copia si riconosce dal contorno: due orizzontali e due verticali che
# chiudono un rettangolo con le proporzioni del DT letto, fra l'8 e il 92%
# della sua taglia, fuori da lui. Dentro ci devono essere le sue linee.
#
# Solo per confermare, mai per gridare. Di rettangoli con le proporzioni giuste
# una tavola ne ha anche altri: sul Kinder Country sono le cornici delle lastre
# di separazione, sul Paradiso i riquadri della legenda, e dentro non c'e' il
# disegno. Una copia che non torna non dice che il DT e' stato letto male: puo'
# non essere una copia. E le radici delle pinne non si chiedono, perche' non
# tutte le miniature le disegnano - sul Milch-Schnitte e sul Paradiso no.
MINIATURA_SCALA = (0.08, 0.92)
# mm alla scala del DT grande, ma mai sotto 0,6 punti sulla copia
MINIATURA_TOL_MM = 0.8
MINIATURA_TOL_PT = 0.6
# un tratto piu' corto di questa frazione del lato e' una scritta, non una linea
MINIATURA_LUNGA = 0.25
MINIATURA_SPESSO = 1.2


def _catena(v):
    return " | ".join(("%.1f" % x).rstrip("0").rstrip(".").replace(".", ",")
                      for x in v)


def riscontro_miniature(pdf, fp, page_no=0):
    """Pieghe e testate lette sul DT contro le sue copie in scala. Una riga o None.

    `fp` e' il Flowpack com'e' uscito dall'analisi, con `sheet` e `ruotato`:
    il nastro corre in x se lo steso e' ruotato, in y se no. E' un riscontro:
    qualunque cosa vada storta qui, il modello si costruisce lo stesso.
    """
    if not getattr(fp, "sheet", None):
        return None
    try:
        return _riscontro_miniature(pdf, fp, page_no)
    except Exception:
        return None


def _riscontro_miniature(pdf, fp, page_no):
    from .tracciati import segmenti
    segs, _w, _h = segmenti(pdf, page_no)
    sx0, sy0, sx1, sy1 = fp.sheet
    PX0, PY0, PX1, PY1 = (sy0, sx0, sy1, sx1) if fp.ruotato else fp.sheet
    W, H = PX1 - PX0, PY1 - PY0
    if W <= 0 or H <= 0:
        return None
    # le linee attese, in mm dall'inizio: lungo il nastro le quattro pieghe
    # del corpo (a sovrapposizione solo i due bordi), lungo il passo le
    # testate del DT e i due tagli
    passo = [0.0] + [float(v) for v in fp.linee_passo] + [float(fp.step_mm)]
    bordi = [0.0, float(fp.web_mm)]
    if fp.pillow:
        pieghe = bordi
    else:
        a = float(fp.side_fin) + float(fp.back_a)
        pieghe = bordi + [a, a + fp.T, a + fp.T + fp.W, a + 2 * fp.T + fp.W]
    Hs = [(c, a, b, st) for k, c, a, b, st in segs if k == "H"
          and st[0] <= MINIATURA_SPESSO]
    Vs = [(c, a, b, st) for k, c, a, b, st in segs if k == "V"
          and st[0] <= MINIATURA_SPESSO]

    def lato(lista, c, a, b, tol):
        """Un tratto in `c` che copre da a a b."""
        return any(abs(cc - c) <= tol and a0 <= a + tol and b0 >= b - tol
                   for cc, a0, b0, _st in lista)

    copie = []
    for y, a, b, _st in Hs:
        s = (b - a) / W
        if not (MINIATURA_SCALA[0] <= s <= MINIATURA_SCALA[1]):
            continue
        tol = max(0.5, 0.01 * (b - a))
        for y0, y1 in ((y, y + s * H), (y - s * H, y)):
            r = (a, y0, b, y1)
            if not (r[2] < PX0 or r[0] > PX1 or r[3] < PY0 or r[1] > PY1):
                continue
            if any(max(abs(p - q) for p, q in zip(r, c[0])) < 1.0 for c in copie):
                continue
            if (lato(Vs, a, y0, y1, tol) and lato(Vs, b, y0, y1, tol)
                    and lato(Hs, y1 if y0 == y else y0, a, b, tol)):
                copie.append((r, s))

    tornano = []
    for (x0, y0, x1, y1), s in copie:
        tol = max(MINIATURA_TOL_PT, MINIATURA_TOL_MM / PT2MM * s)
        # nastro in x -> pieghe verticali e testate orizzontali, e viceversa
        assi = (((Vs, x0, y0, y1, pieghe), (Hs, y0, x0, x1, passo))
                if fp.ruotato else
                ((Hs, y0, x0, x1, pieghe), (Vs, x0, y0, y1, passo)))
        ok = True
        for lista, o, t0, t1, posizioni in assi:
            lungo = MINIATURA_LUNGA * (t1 - t0)
            for mm in posizioni:
                p = o + mm / PT2MM * s
                if not any(abs(c - p) <= tol and b - a >= lungo
                           and a >= t0 - tol and b <= t1 + tol
                           for c, a, b, _st in lista):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            tornano.append(s)
    if not tornano:
        return None
    if fp.pillow:
        nastro = "nastro %s" % _catena([fp.web_mm])
    else:
        nastro = "nastro %s" % _catena([fp.side_fin, fp.back_a, fp.T, fp.W,
                                        fp.T, fp.back_b, fp.side_fin])
    scale = sorted({round(1.0 / s, 1) for s in tornano})
    return ("miniatura: le pieghe e le testate lette sul DT (%s, passo %s) "
            "tornano su %d %s del disegno in scala %s"
            % (nastro, _catena([b - a for a, b in zip(passo, passo[1:])]),
               len(tornano), "copia" if len(tornano) == 1 else "copie",
               ", ".join(("1:%.1f" % v).replace(".", ",") for v in scale)))
