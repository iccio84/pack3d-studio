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
