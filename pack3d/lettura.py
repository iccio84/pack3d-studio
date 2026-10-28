"""
La lettura del PDF, da mettere accanto al modello.

Gli errori dei casi arrivati in coda quasi mai erano misure sbagliate di un
decimo: erano letture sbagliate di COSA e' cosa. Il flowpack montato girato
di 90 gradi, con la pinna longitudinale presa per le testate; l'astuccio
costruito sulla miniatura del cartiglio invece che sul foglio; la famiglia
sbagliata. Chi ha il PDF li vede in un attimo, se gli si fa vedere come lo si
e' letto: la pagina col disegno usato e sopra i pannelli, col loro nome e le
misure. La pagina la mette accanto al modello, senza un clic in piu', e da
li' chi l'ha caricato segnala «letto male» (`server`, `/api/segnala`).

Le quote scritte sul file confermano il disegno in un caso su 43 del parco:
chiedere conferma di ogni misura che non confermano vorrebbe dire chiederla
quasi sempre, su disegni letti giusti. Si fa vedere, e si chiede solo a chi
vede che non torna.

Usa pdfium (`vista.pagina`): va chiamata dentro il posto di costruzione.
"""
from __future__ import annotations

import io

from .dieline import PT2MM

# accanto al GLB costruito, col suo nome piu' questo: il server la va a
# prendere li' (`server.lettura_accanto`)
ACCANTO = ".lettura.jpg"
LATO = 1400            # px, il lato lungo della pagina resa
LEGENDA = 400          # px, la colonna a destra coi nomi e le misure
SBIADITA = 0.45        # quanto bianco sulla pagina, perche' le fasce si vedano
MARGINE = 0.25         # attorno allo steso, in frazione del suo lato lungo: il resto della pagina e' vuoto
# i colori dei pannelli: (riempimento RGBA, bordo RGB)
COLORI = {
    "fronte": ((255, 140, 0, 95), (230, 110, 0)),
    "fianco": ((40, 120, 255, 70), (30, 90, 220)),
    "retro": ((120, 120, 120, 55), (90, 90, 90)),
    "pinna": ((170, 60, 200, 80), (140, 40, 170)),
    "gola": ((170, 60, 200, 40), (140, 40, 170)),
}


def _mm(x):
    return ("%.1f" % x).replace(".", ",")


def _jpeg(im):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82)
    return b.getvalue()


def flowpack(pdf, fp, gradi=0, lato=LATO):
    """La lettura di un flowpack, in JPEG: la pagina di lavoro `pdf` col
    riquadro dello steso e, sopra, le fasce lette - lungo il giro retro,
    fianco, fronte, fianco, retro (a sovrapposizione o a tubo piatto senza
    fianchi), lungo il passo le pinne di testa e la gola - riportata al verso
    del PDF se il foglio di lavoro e' girato di `gradi` in senso orario.

    `fp` e' il Flowpack com'e' uscito dal DT, nel telaio del solutore: x
    lungo il passo, y lungo il giro; con `fp.ruotato` x e y della pagina sono
    scambiate (`flowpack.foglio_in_pagina`)."""
    from PIL import Image, ImageDraw

    from .steso import INDIETRO, gira
    from .vista import _carattere, pagina
    im, (w_mm, h_mm) = pagina(pdf, lato, misure=True)
    k = im.width / (w_mm / PT2MM)            # pixel per punto
    x0, y0, x1, y1 = fp.sheet

    def in_pagina(a, b, c, d):
        """Un rettangolo (x0, y0, x1, y1) del solutore in pixel della pagina."""
        r = (b, a, d, c) if fp.ruotato else (a, b, c, d)
        return [v * k for v in r]

    # le fasce lungo il giro, dal bordo del perimetro utile
    g = fp.girth_span[0]
    if fp.tubo_piatto:
        giro = [("retro", fp.back_a), ("fronte", fp.W), ("retro", fp.back_b)]
    else:
        giro = [("retro", fp.back_a), ("fianco", fp.T), ("fronte", fp.W),
                ("fianco", fp.T), ("retro", fp.back_b)]
    fasce = []
    for nome, mm in giro:
        if mm > 0:
            fasce.append((nome, in_pagina(x0, g, x1, g + mm / PT2MM), mm))
        g += mm / PT2MM
    # lungo il passo: le pinne di testa e la gola, ai due tagli
    pinna, gola = fp.end_fin / PT2MM, fp.gola / PT2MM
    for a, b in ((x0, x0 + pinna), (x1 - pinna, x1)):
        fasce.append(("pinna", in_pagina(a, y0, b, y1), fp.end_fin))
    if gola > 0:
        for a, b in ((x0 + pinna, x0 + pinna + gola), (x1 - pinna - gola, x1 - pinna)):
            fasce.append(("gola", in_pagina(a, y0, b, y1), fp.gola))

    # la pagina sbiadita, perche' sopra una grafica piena le fasce si vedano
    im = Image.blend(im, Image.new("RGB", im.size, "white"), SBIADITA)
    sopra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sopra)
    for nome, r, _mm_ in fasce:
        fondo, bordo = COLORI[nome]
        d.rectangle(r, fill=fondo, outline=bordo + (255,), width=5 if nome == "fronte" else 3)
    # il riquadro dello steso, che e' quello da cui si ritaglia la grafica
    d.rectangle(in_pagina(x0, y0, x1, y1), outline=(0, 0, 0, 255), width=4)
    im = Image.alpha_composite(im.convert("RGBA"), sopra)
    # il nome sulla fascia, dove ci sta: il fronte sempre
    d = ImageDraw.Draw(im)
    f = _carattere(20)
    for nome, r, mm in fasce:
        if nome not in ("fronte", "fianco", "retro"):
            continue
        testo = "%s %s" % (nome.upper() if nome == "fronte" else nome, _mm(mm))
        lw, lh = d.textbbox((0, 0), testo, font=f)[2:]
        # attraverso la fascia ci deve stare: alta quanto la scritta se la
        # fascia corre in orizzontale, larga quanto lei se corre in verticale
        traverso = (r[2] - r[0]) if fp.ruotato else (r[3] - r[1])
        if traverso < (lw + 8 if fp.ruotato else lh + 6) and nome != "fronte":
            continue
        x, y = r[0] + 12, (r[1] + r[3] - lh) / 2 - 3
        if fp.ruotato:
            x, y = (r[0] + r[2] - lw) / 2, r[1] + 12
        d.rectangle((x - 4, y - 2, x + lw + 4, y + lh + 6), fill=COLORI[nome][1] + (255,))
        d.text((x, y), testo, fill="white", font=f)
    # solo lo steso e un margine attorno: nella colonna accanto al modello la
    # pagina intera, quasi tutta vuota, lo faceva piccolo
    a, b, c, e = in_pagina(x0, y0, x1, y1)
    m = MARGINE * max(c - a, e - b)
    im = im.convert("RGB").crop((max(0, int(a - m)), max(0, int(b - m)),
                                 min(im.width, int(c + m)), min(im.height, int(e + m))))
    im = gira(im, INDIETRO.get(int(gradi) % 360))

    # la legenda: cosa e' cosa, con le misure lette
    righe = [("Flowpack letto cosi'", None), ("", None)]
    righe += [("fronte  %s mm" % _mm(fp.W), "fronte")]
    if not fp.tubo_piatto:
        righe += [("fianchi  %s mm" % _mm(fp.T), "fianco")]
    righe += [("retro  %s + %s mm" % (_mm(fp.back_a), _mm(fp.back_b)), "retro"),
              ("pinne di testa  %s mm" % _mm(fp.end_fin), "pinna")]
    if fp.gola > 0:
        righe += [("gola  %s mm" % _mm(fp.gola), "gola")]
    righe += [("", None),
              ("corpo  %s mm" % _mm(fp.L), None),
              ("passo  %s mm" % _mm(fp.step_mm), None),
              ("giro del film  %s mm" % _mm(fp.web_mm), None),
              ("", None),
              ("Il riquadro nero e' lo steso:", None),
              ("la grafica si prende da li'.", None),
              ("", None),
              ("Se il fronte non e' la fascia", None),
              ("arancione, o le pinne non sono", None),
              ("alle due testate, il PDF e'", None),
              ("stato letto male: segnalalo.", None)]
    alto = max(im.height, 40 + 34 * len(righe))
    tela = Image.new("RGB", (im.width + LEGENDA, alto), "white")
    tela.paste(im, (0, 0))
    d = ImageDraw.Draw(tela)
    f = _carattere(22)
    y = 20
    for testo, nome in righe:
        x = im.width + 20
        if nome:
            fondo, bordo = COLORI[nome]
            d.rectangle((x, y + 3, x + 22, y + 25), fill=fondo[:3], outline=bordo)
            x += 32
        d.text((x, y), testo, fill="black", font=f)
        y += 34
    return _jpeg(tela)
