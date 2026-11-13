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

La grafica e' quella del PDF senza il disegno tecnico
(`fustella.resa_senza_dt`); i contorni seguono le curve del PDF, lo spessore
prende il colore della stampa, e due parti non stanno mai nello stesso posto
(`Montaggio.risolvi`, `intersezioni`): regole/pop.md, *Come si costruisce*.
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
    """La maglia di tutti i pezzi, sulla griglia della texture.

    `pannello` mette da parte i pannelli, `array` li stende: prima toglie le
    compenetrazioni fra parti diverse (`risolvi`), poi fa la maglia di
    ognuno (`_maglia`)."""

    def __init__(self, griglia, t=SPESSORE):
        self.G = griglia
        self.t = t
        self.V, self.UV, self.T = [], [], []
        self.parti = {}
        self.grezzi = []
        self.pannelli = []
        self.intagli = []
        self._cache = {}

    def pannello(self, pezzo, masc, scarto, punto, dentro, nome):
        """Un pannello: `punto(lx, ly)` porta un punto del foglio, in mm
        locali del pezzo, sulla faccia stampata; `dentro` e' la direzione
        del cartone. `punto` e' affine: ogni pannello e' piatto."""
        from scipy import ndimage
        G = self.G
        d = np.asarray(dentro, float)
        d = d / np.linalg.norm(d)
        X0, Y0 = scarto
        o = np.array(G.a_mm(X0, Y0), float)
        # La mappa affine si misura nel punto piu' interno del pannello: il
        # ritaglio sborda di un paio di pixel oltre le pieghe, e le regole
        # sono a tratti (min, abs) - misurata sull'angolo del ritaglio, un
        # fianco intero finiva schiacciato su una linea.
        dist = ndimage.distance_transform_edt(np.pad(masc, 1))[1:-1, 1:-1]
        ic, jc = np.unravel_index(int(np.argmax(dist)), dist.shape)
        c = np.array(G.a_mm(X0 + jc + 0.5, Y0 + ic + 0.5), float)
        h = float(np.clip(dist[ic, jc] / G.px * 0.5, 0.25, 1.0))

        def f(xy):
            return np.array(punto(*pezzo.locale(*xy)), float)
        Pc = f(c)
        A = np.stack([f(c + (h, 0.0)) - Pc, f(c + (0.0, h)) - Pc], 1) / h
        P0 = Pc - A @ (c - o)
        # piatto davvero: i punti lontani dalle pieghe stanno sulla mappa
        dentro_m = ndimage.binary_erosion(masc, iterations=2)
        ii, jj = np.nonzero(dentro_m)
        if len(ii):
            k = max(1, len(ii) // 100)
            xy = np.stack(G.a_mm(X0 + jj[::k] + 0.5, Y0 + ii[::k] + 0.5), 1)
            P = np.array([f(q) for q in xy])
            scarto_max = float(np.abs(P0 + (xy - o) @ A.T - P).max())
            if scarto_max > 0.5:
                raise ValueError("%s: il pannello non e' piatto (scarto %.1f mm, %s)"
                                 % (nome, scarto_max, _dove((masc, scarto), pezzo, G)))
        self.grezzi.append(dict(nome=nome, pezzo=pezzo, masc=np.asarray(masc, bool).copy(),
                                scarto=scarto, o=o, P0=P0, A=A, d=d,
                                via=np.zeros(masc.shape, bool)))

    # --- le compenetrazioni

    @staticmethod
    def _in3d(p, xy):
        """I punti `xy` (mm della pagina) del pannello `p` sulla sua faccia
        stampata."""
        return p["P0"] + (xy - p["o"]) @ p["A"].T

    def _dentro(self, p, X, margine):
        """Quali punti 3D `X` stanno dentro lo spessore e il contorno del
        pannello `p` (a piu' di `margine` mm dalle facce)."""
        G, t = self.G, self.t
        Q = X - p["P0"]
        s = Q @ p["d"]
        sel = (s > margine) & (s < t - margine)
        out = np.zeros(len(X), bool)
        if not sel.any():
            return out
        uv, *_ = np.linalg.lstsq(p["A"], (Q[sel] - np.outer(s[sel], p["d"])).T, rcond=None)
        xy = p["o"] + uv.T
        Xp, Yp = G.a_pixel(xy[:, 0], xy[:, 1])
        j = np.floor(Xp - p["scarto"][0]).astype(int)
        i = np.floor(Yp - p["scarto"][1]).astype(int)
        h, w = p["masc"].shape
        ok = (i >= 0) & (i < h) & (j >= 0) & (j < w)
        dent = np.zeros(len(xy), bool)
        dent[ok] = p["masc"][i[ok], j[ok]]
        out[np.nonzero(sel)[0]] = dent
        return out

    def _ingombro(self, p):
        G, t = self.G, self.t
        h, w = p["masc"].shape
        X0, Y0 = p["scarto"]
        ang = np.array([G.a_mm(X0 + a, Y0 + b) for a in (0, w) for b in (0, h)])
        P = self._in3d(p, ang)
        P = np.concatenate([P, P + p["d"] * t])
        return P.min(0), P.max(0)

    def risolvi(self, prima, margine=0.4):
        """Dove un pannello entra nello spessore di un pannello di un'altra
        parte, chi viene dopo nell'ordine `prima(p)` (piu' basso cede) perde
        quei pixel: un intaglio, come la feritoia che il cartone avrebbe.
        Senza, nel modello due cartoni stanno nello stesso posto."""
        from scipy import ndimage
        G, t = self.G, self.t
        rango = {id(p): prima(p) for p in self.grezzi}
        ingombri = {id(p): self._ingombro(p) for p in self.grezzi}
        ordine = sorted(self.grezzi, key=lambda p: rango[id(p)])
        for k, b in enumerate(ordine):              # b cede a chi viene prima
            lob, hib = ingombri[id(b)]
            for a in ordine[:k]:
                if a["nome"] == b["nome"]:
                    continue
                loa, hia = ingombri[id(a)]
                if np.any(hia < lob - 0.1) or np.any(hib < loa - 0.1):
                    continue
                ii, jj = np.nonzero(b["masc"] & ~b["via"])
                if not len(ii):
                    break
                X0, Y0 = b["scarto"]
                xy = np.stack(G.a_mm(X0 + jj + 0.5, Y0 + ii + 0.5), 1)
                P = self._in3d(b, xy)
                vicini = np.all((P > loa - t) & (P < hia + t), 1)
                if not vicini.any():
                    continue
                colpiti = np.zeros(len(P), bool)
                for f in (0.12, 0.5, 0.88):
                    X = P[vicini] + b["d"] * (t * f)
                    colpiti[np.nonzero(vicini)[0]] |= self._dentro(a, X, margine)
                if colpiti.sum() < 3:
                    continue
                via = np.zeros_like(b["via"])
                via[ii[colpiti], jj[colpiti]] = True
                via = ndimage.binary_dilation(via, iterations=1) & b["masc"]
                b["via"] |= via
                self.intagli.append((b["nome"], a["nome"], int(via.sum())))
        for p in self.grezzi:
            p["masc"] = p["masc"] & ~p["via"]

    # --- la maglia

    def _maglia(self, p):
        """La maglia di un pannello. Il contorno non e' quello dei pixel della
        maschera, a gradini: e' quello del PDF. Il bordo della maschera si
        aggancia ai tagli e alle pieghe del pezzo (le curve di Bezier
        campionate fitte, `fustella.PASSO_CURVA`), e i punti in fila si
        tolgono (`fustella.semplifica`); lungo un intaglio (`risolvi`) il
        bordo resta dov'e'. Poi la faccia stampata, quella interna, e lo
        spessore lungo i tagli: sulle pieghe no, li' il cartone continua nel
        pannello accanto. Lo spessore prende il colore della grafica a
        qualche millimetro dal bordo, non quello del cartone grezzo."""
        from scipy import ndimage
        from scipy.spatial import cKDTree
        from ..ballotin import triangola
        G, t = self.G, self.t
        pezzo, masc, nome, d = p["pezzo"], p["masc"], p["nome"], p["d"]
        if masc.sum() < 20:
            return
        X0, Y0 = p["scarto"]
        albero, pieghe = self._linee(pezzo)
        intaglio = ndimage.binary_dilation(p["via"], iterations=1)
        h, w = masc.shape
        anelli = []
        for an in F.contorni(masc):
            if abs(_area(an)) < 2.0:
                continue
            mm = np.stack(G.a_mm(X0 + an[:, 0], Y0 + an[:, 1]), 1)
            # un angolo di pixel che tocca un intaglio non si aggancia
            fermo = np.zeros(len(an), bool)
            for di in (-1, 0):
                for dj in (-1, 0):
                    i = np.clip(an[:, 1].astype(int) + di, 0, h - 1)
                    j = np.clip(an[:, 0].astype(int) + dj, 0, w - 1)
                    fermo |= intaglio[i, j]
            agg = F.aggancia(mm, None, toll=2.5, albero=albero)
            mm = np.where(fermo[:, None], mm, agg)
            mm = F.semplifica(_senza_doppi(mm), 0.05)
            if len(mm) >= 3 and abs(_area(mm)) > 1.0:
                anelli.append(mm)
        if not anelli:
            return
        pts, tri = triangola(anelli, bordo=1e9, griglia=1e9)
        if not len(tri):
            return

        def a3d(xy):
            return self._in3d(p, xy)

        def uv(xy):
            X, Y = G.a_pixel(xy[:, 0], xy[:, 1])
            return np.stack([X / G.W, Y / G.H * self.q], 1)

        # le due facce
        P = a3d(pts)
        n = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
        tri = np.where(((n @ d) > 0)[:, None], tri[:, ::-1], tri)    # la stampa guarda fuori
        Vs = [P, P + d * t]
        UVs = [uv(pts), np.tile([[0.5, self.vI]], (len(pts), 1))]
        Ts = [tri, tri[:, ::-1] + len(pts)]
        base = 2 * len(pts)
        # lo spessore: il colore e' quello della grafica a 3 mm dal bordo
        stretta = ndimage.binary_erosion(masc, iterations=3)
        if not stretta.any():
            stretta = masc
        anello = stretta & ~ndimage.binary_erosion(stretta)
        ii, jj = np.nonzero(anello)
        vicino = cKDTree(np.stack([jj + 0.5, ii + 0.5], 1))
        for an in anelli:
            a, b = an, np.roll(an, -1, axis=0)
            su_piega = (_distanza(a, pieghe) < 0.15) & (_distanza(b, pieghe) < 0.15) \
                & (_distanza((a + b) / 2, pieghe) < 0.15)
            lungo = np.hypot(*(b - a).T) > 1e-6
            k = np.nonzero(~su_piega & lungo)[0]
            if not len(k):
                continue
            A, B = a3d(a[k]), a3d(b[k])
            # verso fuori: lontano dal cartone. Gli anelli di `contorni` hanno
            # il cartone a destra (y in giu': a destra di (dx, dy) c'e'
            # (-dy, dx)), e agganciarli e semplificarli non cambia il verso
            e = (b[k] - a[k]) / np.hypot(*(b[k] - a[k]).T)[:, None]
            m = (a[k] + b[k]) / 2
            dirf = a3d(m + np.stack([e[:, 1], -e[:, 0]], 1) * 0.5) - a3d(m)
            Xa, Ya = G.a_pixel(a[k, 0], a[k, 1])
            Xb, Yb = G.a_pixel(b[k, 0], b[k, 1])
            _, ia = vicino.query(np.stack([Xa - X0, Ya - Y0], 1))
            _, ib = vicino.query(np.stack([Xb - X0, Yb - Y0], 1))
            ua = uv(np.stack(G.a_mm(X0 + jj[ia] + 0.5, Y0 + ii[ia] + 0.5), 1))
            ub = uv(np.stack(G.a_mm(X0 + jj[ib] + 0.5, Y0 + ii[ib] + 0.5), 1))
            q = len(k)
            V4 = np.concatenate([A, B, B + d * t, A + d * t])
            U4 = np.concatenate([ua, ub, ub, ua])
            i0 = base + np.arange(q)
            quad = np.stack([i0, i0 + q, i0 + 2 * q, i0 + 3 * q], 1)
            T2 = np.concatenate([quad[:, [0, 1, 2]], quad[:, [0, 2, 3]]])
            nn = np.cross(V4[T2[:, 1] - base] - V4[T2[:, 0] - base],
                          V4[T2[:, 2] - base] - V4[T2[:, 0] - base])
            dd = np.concatenate([dirf, dirf])
            T2 = np.where(((nn * dd).sum(1) < 0)[:, None], T2[:, ::-1], T2)
            Vs.append(V4)
            UVs.append(U4)
            Ts.append(T2)
            base += 4 * q
        self.V.append(np.concatenate(Vs))
        self.UV.append(np.concatenate(UVs))
        self.T.append(np.concatenate(Ts))
        self.parti.setdefault(nome, []).append(len(self.T) - 1)
        self.pannelli.append(p)

    def _linee(self, pezzo):
        """(albero dei tagli e delle pieghe campionati fitti, pieghe come
        segmenti) del pezzo, in mm della pagina: dove si agganciano i
        contorni, e dove non va lo spessore."""
        from scipy.spatial import cKDTree
        k = id(pezzo)
        if k not in self._cache:
            pieghe = [np.asarray(pl, float) for pl in getattr(pezzo, "linee_piega", [])]
            albero = cKDTree(F._campiona(list(pezzo.tagli) + pieghe, 0.25))
            seg = np.array([[pl[0][0], pl[0][1], pl[-1][0], pl[-1][1]] for pl in pieghe]) \
                if pieghe else np.zeros((0, 4))
            self._cache[k] = (albero, seg)
        return self._cache[k]

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

    def array(self, prima=None):
        """(V, UV, T, parti): gli indici sui vertici di tutti, e una parte
        per pezzo, coi suoi triangoli di fila (`exporters.write_glb_mesh`).
        Prima toglie le compenetrazioni (`risolvi`, nell'ordine `prima`)."""
        if not self.pannelli:
            if prima is not None:
                self.risolvi(prima)
            for p in self.grezzi:
                self._maglia(p)
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


def intersezioni(mo, passo=3.0, margine=0.6, dettaglio=False):
    """[(parte, parte, punti, (min, max))]: le coppie di parti diverse che si
    compenetrano ancora nella maglia fatta. Il piano di mezzo di ogni pannello
    si campiona ogni `passo` mm; un punto che cade DENTRO lo spessore di un
    pannello di un'altra parte (a piu' di `margine` mm dalle sue facce) e
    dentro il suo contorno e' una compenetrazione. Due pannelli che si
    toccano faccia a faccia non lo sono."""
    G, t = mo.G, mo.t
    info = []
    for p in mo.pannelli:
        X0, Y0 = p["scarto"]
        k = max(1, int(round(passo * G.px)))
        ii, jj = np.nonzero(p["masc"][::k, ::k])
        if not len(ii):
            continue
        xy = np.stack(G.a_mm(X0 + jj * k + 0.5, Y0 + ii * k + 0.5), 1)
        M = mo._in3d(p, xy) + p["d"] * (t / 2)
        r = _dove((p["masc"], p["scarto"]), p["pezzo"], G)
        lo, hi = mo._ingombro(p)
        info.append(dict(p=p, M=M, lo=lo - 1, hi=hi + 1,
                         chi="%s@%.0f,%.0f" % (p["nome"], (r[0] + r[2]) / 2, (r[1] + r[3]) / 2)))
    trovate = {}
    for a in info:
        for b in info:
            if a["p"]["nome"] == b["p"]["nome"]:
                continue
            if np.any(a["hi"] < b["lo"]) or np.any(b["hi"] < a["lo"]):
                continue
            dentro = mo._dentro(b["p"], a["M"], margine)
            if dentro.sum() < 2:
                continue
            pts = a["M"][dentro]
            chiave = tuple(sorted((a["chi"], b["chi"]))) if dettaglio else \
                tuple(sorted((a["p"]["nome"], b["p"]["nome"])))
            v = trovate.get(chiave)
            if v is None:
                trovate[chiave] = [len(pts), pts.min(0), pts.max(0)]
            else:
                v[0] += len(pts)
                v[1] = np.minimum(v[1], pts.min(0))
                v[2] = np.maximum(v[2], pts.max(0))
    return sorted(((k[0], k[1], v[0], (v[1], v[2])) for k, v in trovate.items()),
                  key=lambda r: -r[2])


def _senza_doppi(a, tol=1e-6):
    tenere = np.ones(len(a), bool)
    tenere[1:] = np.hypot(*np.diff(a, axis=0).T) > tol
    return a[tenere]


def _area(an):
    x, y = an[:, 0], an[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _distanza(p, seg):
    """La distanza di ogni punto `p` (Nx2) dal segmento piu' vicino di `seg`
    (Mx4: x0, y0, x1, y1)."""
    p = np.atleast_2d(p)
    if not len(seg):
        return np.full(len(p), np.inf)
    a, b = seg[None, :, :2], seg[None, :, 2:]
    ab = b - a
    L2 = np.maximum((ab ** 2).sum(-1), 1e-12)
    u = np.clip(((p[:, None] - a) * ab).sum(-1) / L2, 0, 1)
    c = a + ab * u[..., None]
    return np.hypot(*(p[:, None] - c).transpose(2, 0, 1)).min(1)


# Chi cede dove due parti si compenetrano: prima il corpo, poi il divisorio,
# i ripiani, la testata, il riempitivo, il frontalino e il fondello. I
# pannelli stesi sul pavimento (le alette del fondo, il fondello) cedono a
# tutto: l'intaglio sta sotto, e non si vede.
ORDINE = ("fianco_sx", "fianco_dx", "schiena", "divisorio", "ripiano_sup", "ripiano_inf",
          "testata", "riempitivo", "frontalino", "fondello")


def _ordine(t):
    def prima(p):
        nome = p["nome"]
        k = next((i for i, n in enumerate(ORDINE) if nome.startswith(n)), len(ORDINE))
        pavimento = abs(p["d"][1]) > 0.99 and p["P0"][1] <= 3 * t + 0.5
        return (1 if pavimento else 0, k)
    return prima


def _intagli(intagli):
    """[(parte, contro, mm2)]: gli intagli sommati per coppia di parti."""
    somma = {}
    for parte, contro, px in intagli:
        somma[(parte, contro)] = somma.get((parte, contro), 0) + px
    return [(a, b, n) for (a, b), n in sorted(somma.items(), key=lambda kv: -kv[1])]


def _solo(masc, scarto, pezzo, G, tieni):
    """La maschera coi soli pixel dove `tieni(lx, ly)` (mm locali del pezzo)."""
    ii, jj = np.nonzero(masc)
    X0, Y0 = scarto
    x, y = G.a_mm(X0 + jj + 0.5, Y0 + ii + 0.5)
    lx, ly = x - pezzo.riquadro[0], y - pezzo.riquadro[1]
    ok = np.array([bool(tieni(a, b)) for a, b in zip(lx, ly)])
    out = np.zeros_like(masc)
    out[ii[ok], jj[ok]] = True
    return out


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
    segni = []
    tagli, pieghe = F.tratti(pdf, segni)
    pezzi = F.pezzi(tagli, pieghe)
    ruoli = riconosci(pezzi, inchiostro(pdf, pezzi))
    m = misure(ruoli, t)
    usati = [p for k, p in ruoli.items()]
    zona = (min(p.riquadro[0] for p in usati) - 5, min(p.riquadro[1] for p in usati) - 5,
            max(p.riquadro[2] for p in usati) + 5, max(p.riquadro[3] for p in usati) + 5)
    G = F.Griglia(zona, px_mm)
    mo = Montaggio(G, t)
    # la grafica senza il disegno tecnico (i triangoli di orientamento
    # compresi): gli oggetti del DT si tolgono dal PDF prima della resa
    tex = mo.texture(F.resa_senza_dt(pdf, G, tagli, tagli + pieghe + segni))

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
            punto, dentro = fatto[:2]
            if len(fatto) > 2:                  # solo una parte del pannello
                masc = _solo(masc, scarto, p, G, fatto[2])
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

        def regola(cx, cy, r, sx=sx, a=a, b=b, fondo=fondo, c0=c0, c1=c1,
                   x_est=x_est, x_int=x_int, verso=verso):
            esterno = cx < a if sx else cx > b
            interno = cx > b if sx else cx < a
            # L'aletta del fondo e' sotto il pannello esterno. Il pannello
            # che la lettura trova sotto la piega va piu' in la': e' il bordo
            # della parete interna, qualche mm piu' lunga, e resta con lei
            # (piegato con l'aletta usciva davanti al fianco).
            if cy > fondo:
                return (lambda lx, ly: (x_est + verso * (ly - fondo), 0.0, z_est(lx)),
                        (0, 1, 0), (lambda lx, ly: lx <= a) if sx else (lambda lx, ly: lx >= b))
            # La linguetta in cima si ripiega dentro, contro la parete
            # interna: e' piu' corta del fianco proprio per starci sopra. Va
            # uno spessore piu' in la' della parete, che li' sale fino in cima
            # sul davanti; la piega della cima copre tutti e tre gli strati.
            if cy < c0:
                return (lambda lx, ly: (x_int + verso * t, fondo - c1 - (c0 - ly), z_est(lx)),
                        (-verso, 0, 0))
            if cy < c1 + 1 and r[3] < c1 + 2:                        # la piega della cima
                return (lambda lx, ly: (x_est + verso * (c1 - ly) / (c1 - c0) * 3 * t,
                                        fondo - c1, z_est(lx)), (0, -1, 0))
            if esterno:
                return (lambda lx, ly: (x_est, fondo - ly, z_est(lx)), (verso, 0, 0))
            if not interno:                                          # la piega davanti
                return (lambda lx, ly: (x_est + verso * abs(lx - (a if sx else b)) / (b - a) * 2 * t,
                                        fondo - ly, D), (0, 0, -1))
            # le feritoie dei ripiani restano nella parete: la linguetta del
            # ripiano ci passa davanti (ripiegata fuori, il cartone della
            # feritoia attraversava il ripiano)
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

    # Le feritoie dei ripiani restano nella parete, come nei fianchi. Dietro,
    # le pieghe fra la parete e l'aletta (doppia a sinistra, tripla a
    # destra) stanno con l'aletta, sulla schiena: con la parete andavano
    # dentro la schiena.
    def regola_div(cx, cy, r):
        if cx < dv[1]:                                               # aletta sinistra, sulla schiena
            return (lambda lx, ly: (xd - (dv[1] - lx), dH - ly, 2 * t), (0, 0, -1))
        if cx < d0:
            return (lambda lx, ly: (xd, dH - ly, zd - (d0 - lx)), (1, 0, 0))
        if cx < d1:                                                  # il dorso
            return (lambda lx, ly: (xd + (lx - d0) / (d1 - d0) * sp, dH - ly, zd), (0, 0, -1))
        if cx < dv[-3]:
            return (lambda lx, ly: (xd + sp, dH - ly, zd - (lx - d1)), (-1, 0, 0))
        return (lambda lx, ly: (xd + sp + (lx - dv[-1]), dH - ly, 2 * t), (0, 0, -1))

    stendi("divisorio", regola_div)

    # --- i ripiani
    # Davanti a zf, dietro l'aletta contro la schiena: a `zb` (la schiena,
    # o le alette del divisorio per i ripiani della colonna di sinistra). Lo
    # strato sopra va da zf all'aletta, quello sotto da zf al davanti
    # dell'aletta che gli scende accanto: il foglio steso e' qualche mm piu'
    # lungo dello spazio fra i due (lo spessore del modello non e' quello
    # vero del cartone), e lo strato si accorcia di quel tanto invece di
    # entrare nella schiena.
    def regola_ripiano(nome, Yc, x0, largo, zb):
        nome = "ripiano_inf" if nome.startswith("ripiano_inf") else nome
        rv = m[nome]["pieghe_v"]
        l0, l1 = m[nome]["linguette"]
        W = ruoli[nome].larghezza
        if nome == "ripiano_sup":       # aletta | sopra | piega | sotto
            al, p0, p1 = rv[0], rv[1], rv[2]
            ks, kb = (zf - zb) / (p0 - al), (zf - zb - t) / (W - p1)
            z_sopra = lambda lx: zf - (p0 - lx) * ks
            z_sotto = lambda lx: zf - (lx - p1) * kb
            sopra = lambda cx: al < cx < p0
            aletta = lambda cx: cx < al
            y_al = lambda lx: Yc + 2 * t - (al - lx)
        else:                           # sotto | piega | sopra | aletta
            p0, p1, al = rv[0], rv[1], rv[2]
            ks, kb = (zf - zb) / (al - p1), (zf - zb - t) / p0
            z_sopra = lambda lx: zf - (lx - p1) * ks
            z_sotto = lambda lx: zf - (p0 - lx) * kb
            sopra = lambda cx: p1 < cx < al
            aletta = lambda cx: cx > al
            y_al = lambda lx: Yc + 2 * t - (lx - al)
        sotto = lambda cx: (cx > p1) if nome == "ripiano_sup" else (cx < p0)

        def regola(cx, cy, r):
            if cy < l0:                                              # linguette a sinistra
                zz = z_sopra if sopra(cx) else z_sotto
                return (lambda lx, ly: (x0, Yc + 2 * t - (l0 - ly), zz(lx)), (1, 0, 0))
            if cy > l1:
                zz = z_sopra if sopra(cx) else z_sotto
                return (lambda lx, ly: (x0 + largo, Yc + 2 * t - (ly - l1), zz(lx)), (-1, 0, 0))
            if aletta(cx):
                return (lambda lx, ly: (x0 + ly - l0, y_al(lx), zb), (0, 0, 1))
            if sopra(cx):
                return (lambda lx, ly: (x0 + ly - l0, Yc + 2 * t, z_sopra(lx)), (0, -1, 0))
            if sotto(cx):
                return (lambda lx, ly: (x0 + ly - l0, Yc, z_sotto(lx)), (0, 1, 0))
            return (lambda lx, ly: (x0 + ly - l0, Yc + abs(lx - p0) / max(p1 - p0, 1) * 2 * t, zf),
                    (0, 0, -1))
        return regola

    ff = m["fsx_fondo"]
    alto = ff - m["fsx_feritoie"][0]
    stendi("ripiano_sup", regola_ripiano("ripiano_sup", alto, 0.0, Wi, t))
    # I ripiani inferiori sono quanti le feritoie della colonna di sinistra
    # sotto quella del ripiano superiore. Il fondo della colonna e' il
    # fondello (largo quanto l'interno, con la feritoia del divisorio): un
    # ripiano anche li' attraversava il frontalino.
    livelli = [ff - y for y in m["fsx_feritoie"][1:]]
    for i, Yc in enumerate(livelli):
        nome = "ripiano_inf_%d" % (i + 1)
        regola = regola_ripiano(nome, Yc, 0.0, m["colonna_sx"], 2 * t)
        p = ruoli["ripiano_inf"]
        for pan in G.pannelli(p):
            masc, scarto = pan
            if masc.sum() < 20:
                continue
            r = _dove(pan, p, G)
            punto, dentro = regola((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, r)
            mo.pannello(p, masc, scarto, punto, dentro, nome)

    # --- la testata, sopra i fianchi
    a0, a1, b0, b1 = m["testata_v"]
    tp = m["testata_piede"]
    zt = zf

    # Sotto la piega del piede ci sono i piedi: entrano nella feritoia in
    # cima al fianco, dentro la doppia parete, e montati non si vedono. Nel
    # modello la doppia parete e' piena, e stavano dentro il fianco: non si
    # stendono.
    def regola_testata(cx, cy, r):
        if cy > tp:
            return None
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
            return (lambda lx, ly: (xf + lx - f0, 0.0, zf - (ly - fh)), (0, 1, 0))
        if cx < f0:
            return (lambda lx, ly: (xf, fh - ly, zf - (f0 - lx)), (1, 0, 0))
        if cx > f1:
            return (lambda lx, ly: (xf + largo_f, fh - ly, zf - (lx - f1)), (-1, 0, 0))
        return (lambda lx, ly: (xf + lx - f0, fh - ly, zf), (0, 0, -1))

    stendi("frontalino", regola_front)

    # --- il fondello, sul fondo
    # Il fondello e' il pavimento: sopra le alette del fondo dei fianchi e
    # della schiena, davanti alle alette del divisorio, con la sua feritoia
    # sul divisorio (quanto lo lascia l'interno). L'aletta davanti si ripiega
    # sotto.
    fo = ruoli["fondello"]
    corte = [q for q in fo.pieghe_dritte() if q[0] == "H" and q[3] - q[2] < 0.2 * fo.larghezza]
    lunghe = [q[1] for q in fo.pieghe_dritte() if q[0] == "H" and q[3] - q[2] >= 0.6 * fo.larghezza]
    c_fer = (corte[0][2] + corte[0][3]) / 2 if corte else fo.larghezza / 2
    xo = min(max(xd + sp / 2 - c_fer, 0.0), Wi - fo.larghezza)
    fp = max(lunghe) if lunghe else fo.altezza

    def regola_fondello(cx, cy, r):
        if cy > fp:
            return (lambda lx, ly: (xo + lx, t, 2 * t + fp - (ly - fp)), (0, 1, 0))
        return (lambda lx, ly: (xo + lx, 3 * t, 2 * t + ly), (0, -1, 0))

    stendi("fondello", regola_fondello)

    # --- il riempitivo: nella colonna di destra, contro la schiena
    ri = ruoli["riempitivo"]
    rv = sorted(q[1] for q in ri.pieghe_dritte() if q[0] == "V")
    r0, r1 = rv[0], rv[-1]
    xr = xd + sp + ((Wi - xd - sp) - (r1 - r0)) / 2
    rH = ri.altezza

    # Sta sul fondello, e dietro tocca l'aletta destra del divisorio
    def regola_riemp(cx, cy, r):
        y = lambda ly: 3 * t + rH - ly
        if cx < r0:
            return (lambda lx, ly: (xr, y(ly), 2 * t + lx), (1, 0, 0))
        if cx > r1:
            return (lambda lx, ly: (xr + (r1 - r0), y(ly), 2 * t + (ri.larghezza - lx)), (-1, 0, 0))
        return (lambda lx, ly: (xr + lx - r0, y(ly), 2 * t + r0), (0, 0, -1))

    stendi("riempitivo", regola_riemp)

    V, UV, T, parti = mo.array(_ordine(t))
    for parte, contro, px in _intagli(mo.intagli):
        avvisi.append("%s: intagliato dove entrava in %s (%.0f mm2)" % (parte, contro, px / G.px ** 2))
    exporters.write_glb_mesh(V, UV, T, tex, uscita, tex_max=4096, parti=parti)
    avvisi.insert(0, "espositore: corpo %.0f x %.0f mm, alto %.0f (con la testata %.0f); "
                     "ripiano superiore a %.0f mm, colonna di sinistra %.0f mm"
                  % (Wi + 4 * t, D, H, H + tp, alto, m["colonna_sx"]))
    return avvisi, m
