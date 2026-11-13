"""
L'espositore da terra (FSDU): il montaggio dei pezzi della fustella.

Il PDF ha una pagina sola coi pezzi stesi in scala 1:1 (`pop.fustella`). Qui
si riconosce ogni pezzo e si monta: dove va, e come si piega ogni suo
pannello. Le misure vengono dai pezzi stessi - le pieghe, le feritoie, le
linguette - e si tengono fra loro (regole/pop.md, *L'espositore*):

- **il corpo** e' in tre fogli: due fianchi e la schiena. Il fianco e' un
  pannello esterno con la grafica (la profondita' D) che si ripiega sul
  bordo davanti in una parete interna, con le feritoie dei ripiani. La
  schiena e' larga quanto l'interno (Wi), e le sue alette coprono il resto
  del fianco: parete interna + aletta = D;
- **i ripiani** sono a doppio strato, piegati sul davanti; le linguette
  entrano nelle feritoie dei fianchi e del divisorio, le alette dietro in
  quelle della schiena. La loro altezza e' quella della piega della
  feritoia; la larghezza fra le pieghe delle linguette e' la colonna;
- **il divisorio** e' doppio, col dorso davanti e le alette incollate
  alla schiena, alla distanza della colonna di sinistra;
- **la testata** sta sopra i fianchi: il pannello davanti largo Wi, le
  orecchie lungo i fianchi, alte quanto la piega delle loro linguette;
- **il frontalino** chiude il davanti in basso; **il fondello** e
  **il riempitivo** stanno dentro.

Il pallet (chep), la guaina di trasporto e il riempimento coi prodotti non
ci sono: il pallet e il riempimento verranno dopo, la guaina non e' del
montato.
"""
from __future__ import annotations

import numpy as np

from . import fustella as F

PX_MM = 1.0              # pixel per mm della griglia e della texture
SPESSORE = 6.0           # mm: cartone onda EB, quattro strati fanno 584 - 559


# ---------------------------------------------------------------------------
# I pezzi: chi e' chi

def _lunghe(p, asse, quota=0.6):
    """Le pieghe dritte lungo l'`asse` lunghe almeno `quota` del pezzo."""
    lato = p.altezza if asse == "V" else p.larghezza
    return [r for r in p.pieghe_dritte() if r[0] == asse and r[3] - r[2] >= quota * lato]


def _doppia(righe, distanza=25.0):
    """Le coppie di pieghe parallele vicine: [(a, b)] con a < b."""
    v = sorted(r[1] for r in righe)
    return [(a, b) for a, b in zip(v, v[1:]) if b - a <= distanza]


def inchiostro(pdf, pezzi, px_mm=0.25):
    """{indice: frazione di pixel non bianchi} per ogni pezzo, sulla pagina
    resa a bassa risoluzione: un pezzo senza stampa (la guaina di trasporto)
    non e' del montato."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        pg = doc[0]
        im = np.asarray(pg.render(scale=px_mm / (72.0 / 25.4)).to_pil().convert("L"))
    finally:
        doc.close()
    fuori = {}
    for i, p in enumerate(pezzi):
        x0, y0, x1, y1 = (int(v * px_mm) for v in p.riquadro)
        a = im[y0:y1 + 1, x0:x1 + 1]
        fuori[i] = float((a < 235).mean()) if a.size else 0.0
    return fuori


def riconosci(pezzi, inchiostri=None):
    """{ruolo: Pezzo} per l'espositore. I ruoli: fianco_sx, schiena,
    fianco_dx (il corpo, i tre pezzi piu' alti), divisorio, riempitivo,
    testata, ripiano_sup, ripiano_inf, frontalino, fondello. Un pezzo senza
    stampa (meno del 20% d'inchiostro: la guaina di trasporto) e uno senza
    pieghe (il pezzo per il pallet) non sono del montato."""
    inchiostri = inchiostri or {}
    stampati = [p for i, p in enumerate(pezzi)
                if p.pieghe and inchiostri.get(i, 1.0) >= 0.2]
    corpo_h = max(p.altezza for p in stampati if p.larghezza < 1000)
    corpo = sorted([p for p in stampati if p.altezza >= 0.9 * corpo_h and p.larghezza < 1000],
                   key=lambda p: p.riquadro[0])
    if len(corpo) != 3:
        raise ValueError("espositore: il corpo deve essere in tre fogli, due fianchi e la "
                         "schiena; ne ho trovati %d" % len(corpo))
    ruoli = {"fianco_sx": corpo[0], "schiena": corpo[1], "fianco_dx": corpo[2]}
    resto = [p for p in stampati if p not in corpo]
    for p in resto:
        lunghe_v = _lunghe(p, "V")
        diagonali = [pl for pl in p.pieghe
                     if abs(pl[0][0] - pl[-1][0]) > 5 and abs(pl[0][1] - pl[-1][1]) > 5]
        if p.altezza >= 0.6 * corpo_h:
            # il divisorio e' piegato a meta' (il dorso), il riempitivo no
            meta = [c for c in _doppia(lunghe_v) if 0.3 < (c[0] / p.larghezza) < 0.7]
            ruoli["divisorio" if meta else "riempitivo"] = p
        elif len(diagonali) >= 4 and p.larghezza > 2 * p.altezza:
            ruoli["testata"] = p
        elif _doppia(lunghe_v, 10.0):
            ruoli.setdefault("ripiani", []).append(p)
        elif any(r[0] == "V" for r in p.pieghe_dritte()) and p.pieghe_dritte():
            ruoli["frontalino"] = p
        else:
            ruoli["fondello"] = p
    ripiani = sorted(ruoli.pop("ripiani", []), key=lambda p: p.altezza)
    if len(ripiani) < 2:
        raise ValueError("espositore: servono il ripiano superiore e quelli inferiori")
    ruoli["ripiano_sup"], ruoli["ripiano_inf"] = ripiani[-1], ripiani[0]
    return ruoli


# ---------------------------------------------------------------------------
# Le misure, dai pezzi

def misure(ruoli, t=SPESSORE):
    """Le misure del montato, in mm, lette dalle pieghe e dalle feritoie."""
    m = {"t": t}
    s = ruoli["schiena"]
    v = sorted(r[1] for r in _lunghe(s, "V"))
    m["sch_x"] = (v[0], v[-1])
    m["Wi"] = v[-1] - v[0]
    # il fondo: la piega orizzontale LUNGA piu' in basso (le linguette in
    # fondo hanno pieghe corte, piu' giu')
    m["sch_fondo"] = max(r[1] for r in s.pieghe_dritte()
                         if r[0] == "H" and r[3] - r[2] > 0.4 * m["Wi"])
    for lato in ("sx", "dx"):
        f = ruoli["fianco_" + lato]
        a, b = _doppia(_lunghe(f, "V"), 15.0)[0]
        m["f%s_piega" % lato] = (a, b)
        orizz = [r for r in f.pieghe_dritte() if r[0] == "H"]
        esterno = a if lato == "sx" else f.larghezza - b
        m["f%s_fondo" % lato] = max(r[1] for r in orizz if r[3] - r[2] > 0.4 * esterno)
        alto = [r for r in orizz if r[1] < 0.1 * f.altezza]
        m["f%s_cima" % lato] = (min(r[1] for r in alto), max(r[1] for r in alto))
        # le feritoie dei ripiani: le pieghe orizzontali sulla parete interna
        dentro = (lambda r: r[2] > b) if lato == "sx" else (lambda r: r[3] < a)
        m["f%s_feritoie" % lato] = sorted(r[1] for r in orizz
                                         if dentro(r) and 0.1 * f.altezza < r[1] < 0.9 * f.altezza
                                         and 100 < r[3] - r[2] < 200)
    a, b = m["fsx_piega"]
    m["D"] = a                                  # il pannello esterno: dal retro alla piega
    m["H"] = m["fsx_fondo"] - m["fsx_cima"][1]
    # i ripiani: profondita' fra la piega davanti e quella dell'aletta dietro,
    # larghezza fra le pieghe delle linguette
    for nome in ("ripiano_sup", "ripiano_inf"):
        r = ruoli[nome]
        vv = sorted(x for x in (q[1] for q in _lunghe(r, "V", 0.7)))
        hh = sorted(q[1] for q in r.pieghe_dritte(minimo=10) if q[0] == "H")
        m[nome] = {"pieghe_v": vv, "linguette": (hh[0], hh[-1]), "largo": hh[-1] - hh[0]}
    d = ruoli["divisorio"]
    vv = sorted(q[1] for q in _lunghe(d, "V"))
    dorso = [c for c in _doppia(_lunghe(d, "V")) if 0.3 < c[0] / d.larghezza < 0.7][0]
    m["div_dorso"] = dorso
    m["div_v"] = vv
    m["div_feritoie"] = sorted(q[1] for q in d.pieghe_dritte() if q[0] == "H")
    m["div_H"] = d.altezza
    m["colonna_sx"] = m["ripiano_inf"]["largo"]
    te = ruoli["testata"]
    tv = sorted(q[1] for q in te.pieghe_dritte() if q[0] == "V")
    m["testata_v"] = (tv[0], tv[1], tv[-2], tv[-1])
    m["testata_piede"] = max(q[1] for q in te.pieghe_dritte() if q[0] == "H")
    return m


# ---------------------------------------------------------------------------
# Il montaggio: per ogni pannello, dove va il suo punto (x, y del foglio, mm
# locali del pezzo) e da che parte e' il cartone non stampato

class Montaggio:
    """La maglia di tutti i pezzi, sulla griglia della texture."""

    def __init__(self, griglia, t=SPESSORE):
        self.G = griglia
        self.t = t
        self.V, self.UV, self.T = [], [], []
        self.parti = {}

    def pannello(self, pezzo, masc, scarto, punto, dentro, nome):
        """Stende un pannello: `punto(lx, ly)` porta un punto del foglio, in
        mm locali del pezzo, sulla faccia stampata; `dentro` e' la direzione
        del cartone. Usa la maglia dei vassoi su un ritaglio, e riporta le UV
        sulla griglia intera."""
        from ..vassoio import Maglia
        G = self.G
        h, w = masc.shape
        X0, Y0 = scarto
        mg = Maglia(w, h, spessore=self.t)

        def p(X, Y):
            x, y = G.a_mm(X0 + X, Y0 + Y)
            lx, ly = pezzo.locale(x, y)
            return tuple(float(v) for v in punto(lx, ly))

        mg.pezzo(masc, "righe", p, dentro)
        V, UV, T = mg.array()
        if not len(T):
            return
        stampa = UV[:, 1] <= mg.q + 1e-9
        u = (UV[:, 0] * w + X0) / G.W
        v = ((UV[:, 1] / mg.q) * h + Y0) / G.H * self.q
        UV = np.where(stampa[:, None], np.stack([u, v], 1),
                      np.where((np.abs(UV[:, 1] - mg.vI) < 1e-9)[:, None],
                               [[0.5, self.vI]], [[0.5, self.vT]]))
        self.V.append(V)
        self.UV.append(UV)
        self.T.append(T)
        self.parti.setdefault(nome, []).append(len(self.T) - 1)

    def texture(self, steso):
        """La texture: lo steso della griglia con le due strisce in fondo
        (l'interno e il taglio), come i vassoi (`vassoio.con_coda`)."""
        from ..vassoio import CODA, con_coda
        tex = con_coda(steso)
        ht = float(self.G.H + CODA)
        self.q = self.G.H / ht
        self.vI = (ht - CODA * 0.75) / ht
        self.vT = (ht - CODA * 0.25) / ht
        return tex

    def array(self):
        """(V, UV, T, parti): gli indici sui vertici di tutti, e una parte
        per pezzo, coi suoi triangoli di fila (`exporters.write_glb_mesh`)."""
        V, UV, Tg = [], [], []
        base = 0
        for v, uv, t in zip(self.V, self.UV, self.T):
            V.append(v)
            UV.append(uv)
            Tg.append(t + base)
            base += len(v)
        T, parti, n = [], [], 0
        for nome, blocchi in self.parti.items():
            tt = np.concatenate([Tg[b] for b in blocchi])
            parti.append((nome, n, n + len(tt)))
            n += len(tt)
            T.append(tt)
        return (np.concatenate(V), np.concatenate(UV), np.concatenate(T).astype(np.uint32),
                parti)


def _dove(pannello_riq, pezzo, G):
    """Il riquadro di un pannello in mm locali del pezzo: (x0, y0, x1, y1)."""
    (masc, (X0, Y0)) = pannello_riq
    h, w = masc.shape
    a = pezzo.locale(*G.a_mm(X0, Y0))
    b = pezzo.locale(*G.a_mm(X0 + w, Y0 + h))
    return a[0], a[1], b[0], b[1]


def monta(pdf, uscita, t=SPESSORE, px_mm=PX_MM):
    """Costruisce l'espositore montato in `uscita` (GLB). Torna gli avvisi."""
    from .. import exporters
    tagli, pieghe = F.tratti(pdf)
    pezzi = F.pezzi(tagli, pieghe)
    ruoli = riconosci(pezzi, inchiostro(pdf, pezzi))
    m = misure(ruoli, t)
    usati = [p for k, p in ruoli.items()]
    zona = (min(p.riquadro[0] for p in usati) - 5, min(p.riquadro[1] for p in usati) - 5,
            max(p.riquadro[2] for p in usati) + 5, max(p.riquadro[3] for p in usati) + 5)
    G = F.Griglia(zona, px_mm)
    mo = Montaggio(G, t)
    tex = mo.texture(_steso(pdf, G))

    Wi, D, H = m["Wi"], m["D"], m["H"]
    zf = t + (m["ripiano_inf"]["pieghe_v"][-1] - m["ripiano_inf"]["pieghe_v"][1])   # davanti dei ripiani
    avvisi = []

    def stendi(ruolo, regola):
        p = ruoli[ruolo]
        for pan in G.pannelli(p):
            masc, scarto = pan
            if masc.sum() < 20:
                continue
            r = _dove(pan, p, G)
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            fatto = regola(cx, cy, r)
            if fatto is None:
                continue
            punto, dentro = fatto
            mo.pannello(p, masc, scarto, punto, dentro, ruolo)

    # --- i fianchi
    for lato in ("sx", "dx"):
        a, b = m["f%s_piega" % lato]
        fondo = m["f%s_fondo" % lato]
        c0, c1 = m["f%s_cima" % lato]
        sx = lato == "sx"
        x_est = -2 * t if sx else Wi + 2 * t        # faccia stampata del pannello esterno
        x_int = 0.0 if sx else Wi                   # faccia stampata della parete interna
        verso = 1.0 if sx else -1.0                 # da fuori verso l'interno

        def z_est(lx, sx=sx, a=a, b=b):
            return min(lx, D) if sx else min(D, D - (lx - b))

        def z_int(lx, sx=sx, a=a, b=b):
            return D - (lx - b) if sx else D - (a - lx)

        feritoie = m["f%s_feritoie" % lato]

        def regola(cx, cy, r, sx=sx, a=a, b=b, fondo=fondo, c0=c0, c1=c1,
                   x_est=x_est, x_int=x_int, verso=verso, feritoie=feritoie):
            esterno = cx < a if sx else cx > b
            interno = cx > b if sx else cx < a
            if cy > fondo:                                           # aletta del fondo
                return (lambda lx, ly: (x_est + verso * (ly - fondo), 0.0, z_est(lx)),
                        (0, 1, 0))
            if cy < c0:                                              # linguetta in cima, ripiegata dentro
                return (lambda lx, ly: (x_int, fondo - c1 - (c0 - ly), z_est(lx)),
                        (-verso, 0, 0))
            if cy < c1 + 1 and r[3] < c1 + 2:                        # la piega della cima
                return (lambda lx, ly: (x_est + verso * (c1 - ly) / (c1 - c0) * 2 * t,
                                        fondo - c1, z_est(lx)), (0, -1, 0))
            if esterno:
                return (lambda lx, ly: (x_est, fondo - ly, z_est(lx)), (verso, 0, 0))
            if not interno:                                          # la piega davanti
                return (lambda lx, ly: (x_est + verso * abs(lx - (a if sx else b)) / (b - a) * 2 * t,
                                        fondo - ly, D), (0, 0, -1))
            for yc in feritoie:                                      # la linguetta di una feritoia
                if yc - 1 <= r[1] <= yc + 3 and r[3] - r[1] < 80:
                    Yc = fondo - yc
                    return (lambda lx, ly, yc=yc, Yc=Yc: (x_int + verso * (ly - yc), Yc, z_int(lx)),
                            (0, -1, 0))
            return (lambda lx, ly: (x_int, fondo - ly, z_int(lx)), (-verso, 0, 0))

        stendi("fianco_" + lato, regola)

    # --- la schiena
    s0, s1 = m["sch_x"]
    sf = m["sch_fondo"]

    # La schiena e' stampata verso l'interno: dietro i ripiani si vede il
    # rosso (il render). Le alette, piegate in avanti, mostrano la stampa
    # nell'interno anche loro, accanto alla parete interna del fianco; il
    # fondo, piegato in avanti, la mostra in su.
    def regola_schiena(cx, cy, r):
        if cy > sf:
            return (lambda lx, ly: (lx - s0, 2 * t, ly - sf), (0, -1, 0))
        if cx < s0:
            return (lambda lx, ly: (0.0, sf - ly, s0 - lx), (-1, 0, 0))
        if cx > s1:
            return (lambda lx, ly: (Wi, sf - ly, lx - s1), (1, 0, 0))
        return (lambda lx, ly: (lx - s0, sf - ly, t), (0, 0, -1))

    stendi("schiena", regola_schiena)

    # --- il divisorio: a destra della colonna di sinistra
    xd = m["colonna_sx"]
    d0, d1 = m["div_dorso"]
    dv = m["div_v"]
    dH = m["div_H"]
    zd = t + (d0 - dv[1])                       # il dorso, davanti
    sp = 2 * t                                  # due strati

    def regola_div(cx, cy, r):
        for yc in m["div_feritoie"]:
            if yc - 1 <= r[1] <= yc + 3 and r[3] - r[1] < 80 and cx < d0:
                return (lambda lx, ly, yc=yc: (xd - (ly - yc), dH - yc, zd - (d0 - lx)), (0, -1, 0))
        if cx < dv[1]:                                               # aletta sinistra, sulla schiena
            return (lambda lx, ly: (xd - (dv[1] - lx), dH - ly, 2 * t), (0, 0, -1))
        if cx < d0:
            return (lambda lx, ly: (xd, dH - ly, zd - (d0 - lx)), (1, 0, 0))
        if cx < d1:                                                  # il dorso
            return (lambda lx, ly: (xd + (lx - d0) / (d1 - d0) * sp, dH - ly, zd), (0, 0, -1))
        if cx < dv[-2]:
            return (lambda lx, ly: (xd + sp, dH - ly, zd - (lx - d1)), (-1, 0, 0))
        return (lambda lx, ly: (xd + sp + (lx - dv[-1]), dH - ly, 2 * t), (0, 0, -1))

    stendi("divisorio", regola_div)

    # --- i ripiani
    def regola_ripiano(nome, Yc, x0, largo):
        rv = m[nome]["pieghe_v"]
        l0, l1 = m[nome]["linguette"]
        if nome == "ripiano_sup":       # aletta | sopra | piega | sotto
            al, p0, p1 = rv[0], rv[1], rv[2]
            z_sopra = lambda lx: zf - (p0 - lx)
            z_sotto = lambda lx: zf - (lx - p1)
            sopra = lambda cx: al < cx < p0
            sotto = lambda cx: cx > p1
            aletta = lambda cx: cx < al
            z_al = lambda lx: t
            y_al = lambda lx: Yc + 2 * t - (al - lx)
        else:                           # sotto | piega | sopra | aletta
            p0, p1, al = rv[0], rv[1], rv[2]
            z_sopra = lambda lx: zf - (lx - p1)
            z_sotto = lambda lx: zf - (p0 - lx)
            sopra = lambda cx: p1 < cx < al
            sotto = lambda cx: cx < p0
            aletta = lambda cx: cx > al
            z_al = lambda lx: t
            y_al = lambda lx: Yc + 2 * t - (lx - al)

        def regola(cx, cy, r):
            if cy < l0:                                              # linguette a sinistra
                zz = z_sopra if sopra(cx) else z_sotto
                return (lambda lx, ly: (x0, Yc + 2 * t - (l0 - ly), zz(lx)), (1, 0, 0))
            if cy > l1:
                zz = z_sopra if sopra(cx) else z_sotto
                return (lambda lx, ly: (x0 + largo, Yc + 2 * t - (ly - l1), zz(lx)), (-1, 0, 0))
            if aletta(cx):
                return (lambda lx, ly: (x0 + ly - l0, y_al(lx), z_al(lx)), (0, 0, 1))
            if sopra(cx):
                return (lambda lx, ly: (x0 + ly - l0, Yc + 2 * t, z_sopra(lx)), (0, -1, 0))
            if sotto(cx):
                return (lambda lx, ly: (x0 + ly - l0, Yc, z_sotto(lx)), (0, 1, 0))
            return (lambda lx, ly: (x0 + ly - l0, Yc + abs(lx - p0) / max(p1 - p0, 1) * 2 * t, zf),
                    (0, 0, -1))
        return regola

    ff = m["fsx_fondo"]
    alto = ff - m["fsx_feritoie"][0]
    stendi("ripiano_sup", regola_ripiano("ripiano_sup", alto, 0.0, Wi))
    livelli = [ff - y for y in m["fsx_feritoie"][1:]] + [3 * t]
    for i, Yc in enumerate(livelli):
        nome = "ripiano_inf"
        regola = regola_ripiano(nome, Yc, 0.0, m["colonna_sx"])
        p = ruoli[nome]
        for pan in G.pannelli(p):
            masc, scarto = pan
            if masc.sum() < 20:
                continue
            r = _dove(pan, p, G)
            punto, dentro = regola((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, r)
            mo.pannello(p, masc, scarto, punto, dentro, "ripiano_inf_%d" % (i + 1))
    if len(livelli) == 3 and livelli[-1] == 3 * t:
        avvisi.append("ripiani inferiori: due nelle feritoie della colonna di sinistra "
                      "(%.0f e %.0f mm), il terzo sul fondo della colonna: da verificare"
                      % (livelli[0], livelli[1]))

    # --- la testata, sopra i fianchi
    te = ruoli["testata"]
    a0, a1, b0, b1 = m["testata_v"]
    tp = m["testata_piede"]
    zt = zf

    def regola_testata(cx, cy, r):
        y = lambda ly: H + (tp - ly)
        if cx < a0:
            return (lambda lx, ly: (-t, y(ly), zt - (a0 - lx)), (1, 0, 0))
        if cx > b1:
            return (lambda lx, ly: (Wi + t, y(ly), zt - (lx - b1)), (-1, 0, 0))
        if cx < a1:
            return (lambda lx, ly: (-t + (lx - a0) / (a1 - a0) * t, y(ly), zt), (0, 0, -1))
        if cx > b0:
            return (lambda lx, ly: (Wi + (lx - b0) / (b1 - b0) * t, y(ly), zt), (0, 0, -1))
        return (lambda lx, ly: ((lx - a1) / (b0 - a1) * Wi, y(ly), zt), (0, 0, -1))

    stendi("testata", regola_testata)

    # --- il frontalino, davanti in basso fra i fianchi
    fr = ruoli["frontalino"]
    fv = sorted(q[1] for q in fr.pieghe_dritte() if q[0] == "V")
    fh = max(q[1] for q in fr.pieghe_dritte() if q[0] == "H" and q[3] - q[2] > 0.5 * fr.larghezza)
    f0, f1 = fv[0], fv[-1]
    largo_f = f1 - f0
    xf = (Wi - largo_f) / 2

    # Il frontalino sta sul davanti dei ripiani e della testata (zf), sul
    # bordo del pallet: dietro c'e' il terzo ripiano inferiore, che sul fondo
    # copre tutta la profondita' fino a li'. Le ali si ripiegano dentro, il
    # fondo sotto.
    def regola_front(cx, cy, r):
        if cy > fh:
            return (lambda lx, ly: (xf + lx - f0, -t, zf - (ly - fh)), (0, 1, 0))
        if cx < f0:
            return (lambda lx, ly: (xf, fh - ly, zf - (f0 - lx)), (1, 0, 0))
        if cx > f1:
            return (lambda lx, ly: (xf + largo_f, fh - ly, zf - (lx - f1)), (-1, 0, 0))
        return (lambda lx, ly: (xf + lx - f0, fh - ly, zf), (0, 0, -1))

    stendi("frontalino", regola_front)

    # --- il fondello, sul fondo
    fo = ruoli["fondello"]
    xo = (Wi - fo.larghezza) / 2
    stendi("fondello", lambda cx, cy, r: (lambda lx, ly: (xo + lx, 3 * t, t + ly), (0, -1, 0)))

    # --- il riempitivo: nella colonna di destra, contro la schiena
    ri = ruoli["riempitivo"]
    rv = sorted(q[1] for q in ri.pieghe_dritte() if q[0] == "V")
    r0, r1 = rv[0], rv[-1]
    xr = xd + sp + ((Wi - xd - sp) - (r1 - r0)) / 2
    rH = ri.altezza

    def regola_riemp(cx, cy, r):
        if cx < r0:
            return (lambda lx, ly: (xr, rH - ly, t + (lx)), (1, 0, 0))
        if cx > r1:
            return (lambda lx, ly: (xr + (r1 - r0), rH - ly, t + (ri.larghezza - lx)), (-1, 0, 0))
        return (lambda lx, ly: (xr + lx - r0, rH - ly, t + r0), (0, 0, -1))

    stendi("riempitivo", regola_riemp)

    V, UV, T, parti = mo.array()
    exporters.write_glb_mesh(V, UV, T, tex, uscita, tex_max=4096, parti=parti)
    avvisi.insert(0, "espositore: corpo %.0f x %.0f mm, alto %.0f (con la testata %.0f); "
                     "ripiano superiore a %.0f mm, colonna di sinistra %.0f mm"
                  % (Wi + 4 * t, D, H, H + tp, alto, m["colonna_sx"]))
    return avvisi, m


def _steso(pdf, G):
    """La pagina resa sulla griglia: lo steso di tutti i pezzi."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        pg = doc[0]
        W, Hh = pg.get_size()
        PT = 72.0 / 25.4
        x0, y0, x1, y1 = G.zona
        sc = G.px / PT
        im = pg.render(scale=sc, crop=(x0 * PT, Hh - y1 * PT, W - x1 * PT, y0 * PT)).to_pil()
        return im.convert("RGB").resize((G.W, G.H))
    finally:
        doc.close()
