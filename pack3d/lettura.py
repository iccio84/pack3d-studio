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
    "cielo": ((40, 170, 90, 70), (20, 130, 60)),
    "plancia": ((0, 160, 170, 60), (0, 120, 130)),
    "falda": ((170, 60, 200, 55), (140, 40, 170)),
}


def _mm(x):
    return ("%.1f" % x).replace(".", ",")


def _jpeg(im):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82)
    return b.getvalue()


def _tavola(pdf, gradi, parti, riquadro, legenda, lato=LATO):
    """La tavola della lettura, in JPEG: la pagina di lavoro `pdf` sbiadita,
    sopra le `parti` lette e il `riquadro` nero del disegno usato, ritagliata
    attorno a lui e riportata al verso del PDF se il foglio di lavoro e'
    girato di `gradi` in senso orario; a destra la `legenda`.

    `parti`: `[(colore, (x0, y0, x1, y1) in punti della pagina, etichetta o
    None, sempre)]` - l'etichetta si scrive sulla parte dove ci sta, o
    comunque se `sempre`. `legenda`: `[(testo, colore o None)]`."""
    from PIL import Image, ImageDraw

    from .steso import INDIETRO, gira
    from .vista import _carattere, pagina
    im, (w_mm, _h_mm) = pagina(pdf, lato, misure=True)
    k = im.width / (w_mm / PT2MM)            # pixel per punto

    def px(r):
        return [v * k for v in r]

    # la pagina sbiadita, perche' sopra una grafica piena le parti si vedano
    im = Image.blend(im, Image.new("RGB", im.size, "white"), SBIADITA)
    sopra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sopra)
    for colore, r, _e, sempre in parti:
        fondo, bordo = COLORI[colore]
        d.rectangle(px(r), fill=fondo, outline=bordo + (255,), width=5 if sempre else 3)
    # il riquadro del disegno usato: la grafica si prende da li'
    d.rectangle(px(riquadro), outline=(0, 0, 0, 255), width=4)
    im = Image.alpha_composite(im.convert("RGBA"), sopra).convert("RGB")
    # solo il disegno usato e un margine attorno: nella colonna accanto al
    # modello la pagina intera, quasi tutta vuota, lo faceva piccolo
    a, b, c, e = px(riquadro)
    m = MARGINE * max(c - a, e - b)
    taglio = (max(0, int(a - m)), max(0, int(b - m)),
              min(im.width, int(c + m)), min(im.height, int(e + m)))
    im = im.crop(taglio)
    W, H = im.size
    op = INDIETRO.get(int(gradi) % 360)
    im = gira(im, op)

    def girato(r):
        """Un rettangolo in pixel della pagina, nel ritaglio girato al
        verso del PDF: le scritte si mettono dopo il giro, se no si leggono
        capovolte."""
        x0, y0, x1, y1 = r[0] - taglio[0], r[1] - taglio[1], r[2] - taglio[0], r[3] - taglio[1]
        if op == Image.ROTATE_180:
            x0, y0, x1, y1 = W - x1, H - y1, W - x0, H - y0
        elif op == Image.ROTATE_90:             # antiorario
            x0, y0, x1, y1 = y0, W - x1, y1, W - x0
        elif op == Image.ROTATE_270:            # orario
            x0, y0, x1, y1 = H - y1, x0, H - y0, x1
        return [x0, y0, x1, y1]

    # il nome sulla parte, dove ci sta: quelle `sempre` comunque, in alto
    d = ImageDraw.Draw(im)
    f = _carattere(20)
    for colore, r, etichetta, sempre in parti:
        if not etichetta:
            continue
        r = girato(px(r))
        lw, lh = d.textbbox((0, 0), etichetta, font=f)[2:]
        if r[2] - r[0] >= lw + 24 and r[3] - r[1] >= lh + 8:
            x, y = r[0] + 12, (r[1] + r[3] - lh) / 2 - 3
        elif sempre:
            x, y = max(r[0], (r[0] + r[2] - lw) / 2), r[1] + 12
        else:
            continue
        d.rectangle((x - 4, y - 2, x + lw + 4, y + lh + 6), fill=COLORI[colore][1])
        d.text((x, y), etichetta, fill="white", font=f)

    alto = max(im.height, 40 + 34 * len(legenda))
    tela = Image.new("RGB", (im.width + LEGENDA, alto), "white")
    tela.paste(im, (0, 0))
    d = ImageDraw.Draw(tela)
    f = _carattere(22)
    y = 20
    for testo, colore in legenda:
        x = im.width + 20
        if colore:
            fondo, bordo = COLORI[colore]
            d.rectangle((x, y + 3, x + 22, y + 25), fill=fondo[:3], outline=bordo)
            x += 32
        d.text((x, y), testo, fill="black", font=f)
        y += 34
    return _jpeg(tela)


def flowpack(pdf, fp, gradi=0, lato=LATO):
    """La lettura di un flowpack: lo steso e, sopra, le fasce lette - lungo
    il giro retro, fianco, fronte, fianco, retro (a sovrapposizione o a tubo
    piatto senza fianchi), lungo il passo le pinne di testa e la gola.

    `fp` e' il Flowpack com'e' uscito dal DT, nel telaio del solutore: x
    lungo il passo, y lungo il giro; con `fp.ruotato` x e y della pagina sono
    scambiate (`flowpack.foglio_in_pagina`)."""
    x0, y0, x1, y1 = fp.sheet

    def in_pagina(a, b, c, d):
        """Un rettangolo (x0, y0, x1, y1) del solutore nella pagina."""
        return (b, a, d, c) if fp.ruotato else (a, b, c, d)

    # le fasce lungo il giro, dal bordo del perimetro utile
    g = fp.girth_span[0]
    if fp.tubo_piatto:
        giro = [("retro", fp.back_a), ("fronte", fp.W), ("retro", fp.back_b)]
    else:
        giro = [("retro", fp.back_a), ("fianco", fp.T), ("fronte", fp.W),
                ("fianco", fp.T), ("retro", fp.back_b)]
    parti = []
    for nome, mm in giro:
        if mm > 0:
            parti.append((nome, in_pagina(x0, g, x1, g + mm / PT2MM),
                          "%s %s" % (nome.upper() if nome == "fronte" else nome, _mm(mm)),
                          nome == "fronte"))
        g += mm / PT2MM
    # lungo il passo: le pinne di testa e la gola, ai due tagli
    pinna, gola = fp.end_fin / PT2MM, fp.gola / PT2MM
    for a, b in ((x0, x0 + pinna), (x1 - pinna, x1)):
        parti.append(("pinna", in_pagina(a, y0, b, y1), None, False))
    if gola > 0:
        for a, b in ((x0 + pinna, x0 + pinna + gola), (x1 - pinna - gola, x1 - pinna)):
            parti.append(("gola", in_pagina(a, y0, b, y1), None, False))

    legenda = [("Flowpack letto cosi'", None), ("", None),
               ("fronte  %s mm" % _mm(fp.W), "fronte")]
    if not fp.tubo_piatto:
        legenda += [("fianchi  %s mm" % _mm(fp.T), "fianco")]
    legenda += [("retro  %s + %s mm" % (_mm(fp.back_a), _mm(fp.back_b)), "retro"),
                ("pinne di testa  %s mm" % _mm(fp.end_fin), "pinna")]
    if fp.gola > 0:
        legenda += [("gola  %s mm" % _mm(fp.gola), "gola")]
    legenda += [("", None),
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
    return _tavola(pdf, gradi, parti, in_pagina(x0, y0, x1, y1), legenda, lato)


# i pannelli dell'astuccio: il nome per chi guarda, e il colore
PANNELLI = {"front": ("FRONTE", "fronte"), "back": ("retro", "retro"),
            "back_top": ("retro", "retro"), "back_bottom": ("retro", "retro"),
            "left": ("fianco", "fianco"), "right": ("fianco", "fianco"),
            "top": ("cielo", "cielo"), "bottom": ("fondo", "cielo")}


def astuccio(pdf, d, gradi=0, lato=LATO):
    """La lettura di un astuccio: la fustella usata e, sopra, i pannelli
    letti - fronte, retro (le sue due meta' su un astuccio aperto), fianchi,
    cielo e fondo, e le falde - col nome e le misure.

    E' qui che si vede l'astuccio costruito sulla miniatura del cartiglio
    invece che sul foglio (caso 61cfcd4c87): il riquadro nero sta su un
    disegno di pochi centimetri in un angolo. `d` e' la Dieline nella pagina
    di lavoro, in punti con la y dall'alto."""
    parti = []
    for nome, p in d.panels.items():
        nostro, colore = PANNELLI.get(nome, (nome, "falda"))
        etichetta = "%s %s x %s" % (nostro, _mm(p.w_mm), _mm(p.h_mm))
        parti.append((colore, (p.x0, p.y0, p.x1, p.y1), etichetta, nome == "front"))
    L, W, H = d.dims_mm
    legenda = [("Astuccio letto cosi'", None), ("", None),
               ("%s x %s x %s mm" % (_mm(L), _mm(W), _mm(H)), None),
               ("chiuso" if d.chiuso else "aperto, con la finestra", None), ("", None),
               ("fronte", "fronte"), ("retro", "retro"), ("fianchi", "fianco"),
               ("cielo e fondo", "cielo"), ("falde e alette", "falda"), ("", None),
               ("Il riquadro nero e' la fustella", None),
               ("usata: la grafica si prende", None),
               ("da li'.", None), ("", None),
               ("Se il riquadro non sta sul DT", None),
               ("vero (per esempio sulla", None),
               ("miniatura), o il fronte non e'", None),
               ("il pannello arancione, il PDF", None),
               ("e' stato letto male: segnalalo.", None)]
    return _tavola(pdf, gradi, parti, d.bbox, legenda, lato)


def _unione(riquadri):
    xs0, ys0, xs1, ys1 = zip(*riquadri)
    return (min(xs0), min(ys0), max(xs1), max(ys1))


def vassoio(pdf, v, gradi=0, lato=LATO):
    """La lettura di un vassoio espositore: il fondo e le quattro pareti,
    con la testata che va davanti - la piu' bassa (`vassoio.testata_davanti`)
    - in arancione. `v` e' il Vassoio nella pagina di lavoro."""
    from .vassoio import testata_davanti
    davanti = testata_davanti(v)
    parti = []
    for nome, r in v.riquadri.items():
        if nome == "fondo":
            parti.append(("cielo", r, "fondo %s x %s" % (_mm(v.fondo_w), _mm(v.fondo_h)), False))
        elif nome in v.pareti:
            fronte = nome == davanti
            parti.append(("fronte" if fronte else "fianco", r,
                          "%s %s" % ("DAVANTI" if fronte else nome, _mm(v.pareti[nome])),
                          fronte))
    legenda = [("Vassoio letto cosi'", None), ("", None),
               ("fondo  %s x %s mm" % (_mm(v.fondo_w), _mm(v.fondo_h)), "cielo"),
               ("davanti: la testata %s, %s mm" % (davanti, _mm(v.pareti[davanti])), "fronte"),
               ("le altre pareti", "fianco")]
    legenda += [("   %s  %s mm" % (n, _mm(h)), None) for n, h in v.pareti.items() if n != davanti]
    legenda += [("", None),
                ("Il riquadro nero e' la fustella", None),
                ("usata: la grafica si prende", None),
                ("da li'.", None), ("", None),
                ("Se davanti non c'e' la parete", None),
                ("arancione, o il fondo non e' il", None),
                ("riquadro verde, il PDF e' stato", None),
                ("letto male: segnalalo.", None)]
    return _tavola(pdf, gradi, parti, _unione(v.riquadri.values()), legenda, lato)


def plancia(pdf, p, gradi=0, lato=LATO):
    """La lettura di un display con plancia (`pack3d.plancia`, e la plancia
    ricavata nel coperchio di `pack3d.sportello`): il fondo, le pareti fino ai
    loro bordi - la parete con la finestra davanti, in arancione - il
    coperchio che diventa la plancia, e la finestra."""
    x0, y0, x1, y1 = p.fondo
    b = p.bordi
    f0, f1 = p.fianchi
    pareti = {"nord": (x0, b["nord"], x1, y0), "sud": (x0, y1, x1, b["sud"]),
              "ovest": (b["ovest"], f0, x0, f1), "est": (x1, f0, b["est"], f1)}
    parti = [("cielo", p.fondo, "fondo %s x %s" % (_mm((x1 - x0) * PT2MM),
                                                     _mm((y1 - y0) * PT2MM)), False)]
    for nome, r in pareti.items():
        alto = abs((r[3] - r[1]) if nome in ("nord", "sud") else (r[2] - r[0])) * PT2MM
        fronte = nome == p.fronte
        r = (min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3]))
        parti.append(("fronte" if fronte else "fianco", r,
                      "%s %s" % ("DAVANTI" if fronte else nome, _mm(alto)), fronte))
    if p.coperchio:
        parti.append(("plancia", p.coperchio, "plancia", True))
    if getattr(p, "finestra", None):
        parti.append(("falda", p.finestra, "finestra", False))
    legenda = [("Display con plancia letto cosi'", None), ("", None),
               ("fondo", "cielo"), ("davanti: la parete %s" % p.fronte, "fronte"),
               ("le altre pareti", "fianco"),
               ("il coperchio, che fa la plancia", "plancia"),
               ("la finestra", "falda"), ("", None),
               ("Il riquadro nero e' la fustella", None),
               ("usata: la grafica si prende", None),
               ("da li'.", None), ("", None),
               ("Se davanti non c'e' la parete", None),
               ("arancione, o la plancia non e'", None),
               ("il coperchio, il PDF e' stato", None),
               ("letto male: segnalalo.", None)]
    return _tavola(pdf, gradi, parti, _unione([r for _c, r, _e, _s in parti]), legenda, lato)
