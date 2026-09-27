"""
Le verifiche della costruzione, nell'ordine in cui si fanno a mano.

1. **Prima della mappatura, le UV contro il disegno tecnico.** Il modello si
   costruisce dal DT, e le sue UV sono il DT steso: dove la pinna finisce, dove
   il prodotto comincia, dove il giro piega. Se una di queste non cade sulla
   sua linea del disegno, la grafica andra' nel posto sbagliato comunque la si
   mappi - quindi si controlla prima, sul livello del DT, e non dopo sulla
   texture.

2. **Dopo la mappatura, il fronte sul fronte.** Spento il livello del DT e
   acceso quello della grafica, il pannello fronte dell'AW deve stare
   esattamente sulla faccia fronte del modello: centrato, con la normale che
   guarda avanti, e non specchiato. E la texture in quel punto deve essere la
   grafica dell'AW in quel punto: e' la prova che rotazioni e trasposizioni
   fra pagina, steso e texture si compongono giuste.

3. **Dopo, il film sulle testate.** Sul flowpack pinne e spalle non sono un
   piano: la grafica ci deve cadere come ci cade il film, che non si allunga.
   Si misura quanto un millimetro di film diventa lungo sul modello, lungo il
   passo e lungo il giro, triangolo per triangolo.

Nessuna delle tre cambia il modello. Dicono se e' giusto, e quando non lo e'
lo gridano negli avvisi: un modello plausibile e sbagliato e' il difetto
peggiore che questo progetto possa avere, e l'unica difesa e' dirlo.

Una regola di mano per la seconda: vista da fuori, con la normale verso chi
guarda, la texture ha la u che va a destra e la v che va in GIU' - glTF conta
le v dall'alto. Quindi `du x dv` punta DENTRO: dove punta fuori, la grafica e'
specchiata.
"""
from __future__ import annotations

import numpy as np

from .dieline import PT2MM

# quanto possono distare una linea del modello e quella del DT, in mm
TOL_MM = 0.6
# quanto puo' scostarsi dal centro della faccia il centro del fronte, in mm
TOL_CENTRO = 1.5
# quanto puo' pendere la normale al centro del fronte, in gradi
TOL_GRADI = 15.0
# scarto medio di colore fra texture e AW oltre il quale non sono la stessa cosa
TOL_COLORE = 24.0
# Quanto puo' stirarsi la grafica di una faccia d'astuccio. Sotto il 2% non
# si dice niente; fino al 5% si dice, perche' c'e' una ragione di mestiere -
# sul Nutella Donut cielo e fondo del DT sono falde da 36,9 mm su una faccia da
# 38,1, e una falda di chiusura e' spesso un filo piu' corta - e oltre si grida.
STIRO_DICE = 0.02
STIRO_GRIDA = 0.05
# lato della finestra su cui si media il colore di una sonda, in mm. A cinque
# pixel un gradiente con mezzo pixel di sfasamento - quello fra il centro di
# un pixel della pagina e quello della texture ruotata - dava 33 di scarto su
# KP T1 Mandarino in HD, a mappatura giusta; su due millimetri scende sotto
# 3, e il giro sbagliato resta a 189.
SONDA_MM = 2.0


# --------------------------------------------------------------------------- #
# 1. le UV contro il DT
# --------------------------------------------------------------------------- #
def uvw_flowpack(fp0, fp, rastremo, scatola, spalla=None):
    """Le testate del modello contro le linee del DT. `(ok, riga)`.

    Il modello, da ogni taglio verso l'interno, ha due confini: dove comincia
    la pinna (`fp.end_fin`) e dove comincia il prodotto (`fp.end_fin +
    rastremo`). Il DT ha le sue linee, raccolte nell'analisi.

    `spalla` e' quanto e' lunga davvero la discesa verso la saldatura, se il
    calo del tubo l'ha voluta piu' lunga della gola: allora comincia dentro
    il prodotto, e la riga lo dice. Non e' uno scarto dal DT - saldatura e
    fine del prodotto restano sulle loro linee, la spalla ci passa sopra.

    - a pinna, la prima linea del DT e' la saldatura e deve essere il confine
      della pinna; la seconda, se la gola e' stata letta, l'inizio del
      prodotto;
    - con una scatola dentro la saldatura non e' disegnata: la prima linea e'
      la piega della scatola, e deve essere l'inizio del prodotto - la pinna
      sta oltre, dove la mette la gola.

    Lungo il passo le UV non si muovono mai ai confini - `L/2 + end_fin` non
    cambia, e sulla spalla il film si ridistribuisce solo fra la saldatura e
    la sezione piena, che restano ferme - quindi queste due quote sono tutto
    quello che puo' sbagliare.
    """
    from .flowpack import TESTATA_MAX, _strutture
    if not fp0.linee_passo:
        return False, ("UVW contro il DT: il disegno non segna le testate, "
                       "niente con cui confrontarle")
    passo = fp0.step_mm
    lim = TESTATA_MAX * passo
    modello = [fp.end_fin, fp.end_fin + rastremo]
    righe, peggio, ok = [], 0.0, True
    for nome, dist in (("sinistra", list(fp0.linee_passo)),
                       ("destra", [passo - c for c in fp0.linee_passo])):
        st = _strutture([d for d in dist if 0.3 < d <= lim])
        if not st:
            continue
        if scatola:
            attese = [(st[0][0], modello[1])]
        else:
            attese = [(st[0][0], modello[0])]
            if not st[0][1] and fp0.gola and len(st) > 1:
                attese.append((st[1][0], modello[1]))
        for dt, mod in attese:
            d = abs(dt - mod)
            peggio = max(peggio, d)
            if d > TOL_MM:
                ok = False
                righe.append("%s: il DT segna %.1f mm, il modello %.1f"
                             % (nome, dt, mod))
    if not ok and any("rientri diversi" in w for w in fp0.warnings):
        righe.append("il DT non e' speculare sulle testate: una saldatura e' "
                     "disegnata corta o manca, e il modello ha preso il "
                     "rientro piu' stretto. Controllare quel lato sul DT")
    if ok:
        riga = ("UVW sul DT: pinna da %.1f mm, prodotto da %.1f, entro %.1f mm "
                "dalle linee del disegno" % (modello[0], modello[1], peggio))
        if spalla is not None and spalla > rastremo + TOL_MM:
            riga += ("; la spalla comincia a %.1f mm dal taglio, dentro il "
                     "prodotto" % (fp.end_fin + spalla))
        return True, riga
    return False, "UVW NON CORRISPONDE AL DT - " + "; ".join(righe)


# --------------------------------------------------------------------------- #
# 2. il fronte sul fronte
# --------------------------------------------------------------------------- #
def _centro_fronte(fp):
    """Dove sta il centro del pannello fronte sul giro, in mm dal bordo del
    nastro (il bordo dello steso da cui partono le v)."""
    y0 = fp.sheet[1]
    inizio = (fp.girth_span[0] - y0) * PT2MM
    if fp.pillow:
        return inizio + fp.back_a + fp.W / 2.0
    return inizio + fp.back_a + fp.T + fp.W / 2.0


def _campiona(im, x, y, r):
    """Il colore medio del quadrato di lato 2r + 1 attorno al pixel (x, y).

    Si ritaglia prima di convertire: la texture HD di un foglio grande sono
    venti megapixel, e farne un array per leggerne qualche centinaio sarebbe
    stupido."""
    w, h = im.size
    x, y = int(round(x)), int(round(y))
    x0, x1 = max(0, x - r), min(w, x + r + 1)
    y0, y1 = max(0, y - r), min(h, y + r + 1)
    if x1 <= x0 or y1 <= y0:
        return None
    a = np.asarray(im.crop((x0, y0, x1, y1)).convert("RGB"), dtype=np.float32)
    return a.reshape(-1, 3).mean(0)


def fronte_flowpack(V, UV, nv, fp, texture, foglio, scala):
    """Il pannello fronte dell'AW sulla faccia fronte del modello. `(ok, riga)`.

    `V` e `UV` sono quelli del tubo, a griglia di `nv + 1` punti per anello;
    `texture` e' la texture come va nel GLB, `foglio` lo steso della grafica
    nel verso della PAGINA, reso a `scala` px per punto a partire dall'angolo
    alto-sinistro del riquadro dello steso.

    Tre prove sullo stesso punto, il centro del fronte:

    - dove cade: al centro della faccia fronte, cioe' x e y a zero e la
      normale verso +z, che e' davanti per come il tubo e' costruito;
    - come cade: non specchiato, vedi la regola di mano in testa al modulo;
    - cosa c'e': la texture in quel punto e la grafica dell'AW in quel punto,
      piu' quattro punti attorno, devono essere lo stesso colore. Un giro di
      troppo fra pagina e texture qui salta fuori, perche' la grafica non e'
      mai uguale ruotata di 180 gradi.
    """
    web = fp.web_mm
    passo = fp.step_mm
    s_web = _centro_fronte(fp)
    griglia = V.reshape(-1, nv + 1, 3)
    uvg = UV.reshape(-1, nv + 1, 2)
    # u del tubo: 0 e 1 sono i due tagli, e il centro del passo e' 0,5 in
    # qualunque verso. v: dal bordo del nastro.
    iu = int(np.argmin(np.abs(uvg[:, 0, 0] - 0.5)))
    iv = int(np.argmin(np.abs(uvg[iu, :, 1] - s_web / web)))
    p = griglia[iu, iv]
    # derivate sulla griglia: lungo il passo e lungo il giro
    a, b = max(iu - 1, 0), min(iu + 1, griglia.shape[0] - 1)
    c, d = max(iv - 1, 0), min(iv + 1, griglia.shape[1] - 1)
    dpu = (griglia[b, iv] - griglia[a, iv]) / max(uvg[b, iv, 0] - uvg[a, iv, 0], 1e-9)
    dpv = (griglia[iu, d] - griglia[iu, c]) / max(uvg[iu, d, 1] - uvg[iu, c, 1], 1e-9)
    n = np.cross(dpu, dpv)
    n = n / (np.linalg.norm(n) or 1.0)
    # la normale USCENTE: via dall'asse del tubo, che e' l'asse x
    if float(np.dot(n, (0.0, p[1], p[2]))) < 0:
        n = -n
    gradi = float(np.degrees(np.arccos(np.clip(n[2], -1.0, 1.0))))
    specchiato = float(np.dot(np.cross(dpu, dpv), n)) > 0
    fuori = []
    if abs(p[0]) > TOL_CENTRO or abs(p[1]) > TOL_CENTRO:
        fuori.append("il centro del fronte cade a %.1f, %.1f mm dal centro "
                     "della faccia" % (p[0], p[1]))
    if gradi > TOL_GRADI:
        fuori.append("la normale li' pende di %.0f gradi dal davanti" % gradi)
    if specchiato:
        fuori.append("la grafica e' SPECCHIATA")

    # cosa c'e': texture contro AW, al centro e a un terzo del fronte
    scarti = []
    if texture is not None and foglio is not None:
        tw, th = texture.size
        r = max(2, int(round(SONDA_MM / 2.0 / PT2MM * scala)))
        for du, dv in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            s_p = passo / 2.0 + du * passo / 6.0
            s_g = s_web + dv * fp.W / 3.0
            u = (1.0 - s_p / passo) if fp.ruotato else s_p / passo
            t = _campiona(texture, u * tw, (s_g / web) * th, r)
            # lo stesso punto sulla pagina: nel verso del solutore il passo
            # corre sulla x, e se lo steso e' ruotato la pagina e' trasposta
            px, py = (s_g, s_p) if fp.ruotato else (s_p, s_g)
            f = _campiona(foglio, px / PT2MM * scala, py / PT2MM * scala, r)
            if t is not None and f is not None:
                scarti.append(float(np.abs(t - f).mean()))
    if scarti and max(scarti) > TOL_COLORE:
        fuori.append("la texture sul fronte non e' la grafica dell'AW in quel "
                     "punto (scarto di colore %.0f)" % max(scarti))
    if fuori:
        return False, "FRONTE NON SUL FRONTE - " + "; ".join(fuori)
    return True, ("fronte sul fronte: il centro del pannello fronte dell'AW "
                  "cade a %.1f mm dal centro della faccia, normale a %.0f "
                  "gradi dal davanti, non specchiato%s"
                  % (float(np.hypot(p[0], p[1])), gradi,
                     ", e la texture li' e' la grafica dell'AW (scarto %.0f)"
                     % max(scarti) if scarti else ""))


def facce_astuccio(faces, panels):
    """Ogni faccia contro il suo pannello, e il fronte davanti. `(ok, righe)`.

    Per un astuccio le UV sono i quattro angoli del ritaglio, quindi il
    confronto col DT e' sulle proporzioni: la faccia sul solido e il pannello
    sulla fustella devono avere gli stessi lati - se non li hanno, la grafica
    viene stirata. Poi le due prove di mano: nessuna faccia specchiata, e la
    faccia `front` con la normale verso +z.
    """
    righe, ok = [], True
    for f in faces:
        nome = f["name"]
        if nome not in panels:
            continue
        q = [np.array(v, float) for v in f["quad"]]
        du, dv = q[1] - q[0], q[3] - q[0]
        # Il FUORI non si prende dall'ordine del quad: se il quad e' girato,
        # si gira con lui, e una faccia specchiata risulterebbe dritta. Il
        # solido e' centrato nell'origine, quindi fuori e' dal centro verso la
        # faccia.
        centro = sum(q) / 4.0
        n = np.cross(du, dv)
        n = n / (np.linalg.norm(n) or 1.0)
        if float(np.dot(n, centro)) < 0:
            n = -n
        # du e dv sono gia' i lati: con le v che scendono, du x dv deve
        # puntare dentro
        if float(np.dot(np.cross(du, dv), n)) > 0:
            ok = False
            righe.append("FACCIA SPECCHIATA: %s" % nome)
        p = panels[nome]
        lati_f = sorted((float(np.linalg.norm(du)), float(np.linalg.norm(dv))))
        lati_p = sorted((p.w_mm, p.h_mm))
        rap_f = lati_f[0] / max(lati_f[1], 1e-9)
        rap_p = lati_p[0] / max(lati_p[1], 1e-9)
        stiro = abs(rap_f - rap_p) / max(rap_p, 1e-9)
        if stiro > STIRO_GRIDA:
            ok = False
            righe.append("UVW NON CORRISPONDE AL DT - %s: la faccia e' %.1f x "
                         "%.1f mm e il pannello %.1f x %.1f, la grafica si "
                         "stira del %.0f%%" % (nome, lati_f[0], lati_f[1],
                                               lati_p[0], lati_p[1],
                                               100 * stiro))
        elif stiro > STIRO_DICE:
            righe.append("%s: il pannello del DT e' %.1f x %.1f mm e la faccia "
                         "%.1f x %.1f, la sua grafica si stira del %.0f%%"
                         % (nome, lati_p[0], lati_p[1], lati_f[0], lati_f[1],
                            100 * stiro))
        if nome == "front" and n[2] < 0.97:
            ok = False
            righe.append("FRONTE NON SUL FRONTE: la faccia 'front' guarda "
                         "verso %.2f, %.2f, %.2f" % tuple(n))
    if ok:
        righe.insert(0, "UVW sul DT e fronte sul fronte: le facce hanno i lati "
                        "dei loro pannelli, nessuna specchiata, il fronte "
                        "guarda davanti")
    return ok, righe


# --------------------------------------------------------------------------- #
# 3. il film sulle testate
# --------------------------------------------------------------------------- #
# Oltre quanto si grida, sul 95% dei triangoli di pinne e spalle. Lungo il
# giro il film sulla pinna non ha motivo di stirarsi: e' il tubo appiattito.
# Lungo il passo un po' si', perche' la spalla scende e il film non si
# allunga: 1,2 a pinne aperte, 1,67 sul Brioss, dove la scatola tiene la
# sezione fino alla faccia e la gola e' quella che e' - il film vero li' fa
# le orecchie, che una superficie liscia non sa fare.
STIRO_GIRO = 1.25
STIRO_PASSO = 1.8
# sotto quanto il giro si chiude, a pinne aperte: e' il fianco che spariva sul
# bordo della pinna, 0,06 sul Paradiso prima della correzione
CHIUSO_GIRO = 0.6


def testate_flowpack(V, UV, T, fp, spalla, dente, aperte):
    """Quanto la grafica si stira su pinne e spalle. `(ok, riga)`.

    Per ogni triangolo lo jacobiano fra il film - u per il passo, v per il
    nastro, in mm - e la superficie, in mm: le sue due colonne dicono quanto
    diventa lungo un millimetro di film lungo il passo e lungo il giro. Uno e
    uno e' il film com'e'. Si guardano le testate fino a dove la spalla
    comincia, meno i denti, che il film lo tagliano davvero.

    `aperte`: pinne aperte a meta' perimetro. Con le pinne piu' strette il
    fianco si ripiega a soffietto sul bordo, e li' il giro si chiude apposta.
    """
    passo = fp.L + 2.0 * fp.end_fin
    nastro = (fp.sheet[3] - fp.sheet[1]) * PT2MM
    F = np.stack([UV[:, 0] * passo, UV[:, 1] * nastro], 1)
    P0, P1, P2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    F0, F1, F2 = F[T[:, 0]], F[T[:, 1]], F[T[:, 2]]
    dP = np.stack([P1 - P0, P2 - P0], 2)
    dF = np.stack([F1 - F0, F2 - F0], 2)
    det = dF[:, 0, 0] * dF[:, 1, 1] - dF[:, 0, 1] * dF[:, 1, 0]
    area = 0.5 * np.linalg.norm(np.cross(P1 - P0, P2 - P0), axis=1)
    uc = (F0[:, 0] + F1[:, 0] + F2[:, 0]) / 3.0
    d = np.minimum(uc, passo - uc)
    testa = ((np.abs(det) > 1e-9) & (area > 1e-6) & (d > dente + 0.5)
             & (d < fp.end_fin + spalla))
    if testa.sum() < 20:
        return True, "testate: troppo poche per misurarle"
    inv = np.zeros((int(testa.sum()), 2, 2))
    dt, dFt = det[testa], dF[testa]
    inv[:, 0, 0] = dFt[:, 1, 1] / dt
    inv[:, 1, 1] = dFt[:, 0, 0] / dt
    inv[:, 0, 1] = -dFt[:, 0, 1] / dt
    inv[:, 1, 0] = -dFt[:, 1, 0] / dt
    J = dP[testa] @ inv
    lungo = float(np.percentile(np.linalg.norm(J[:, :, 0], axis=1), 95))
    giro = np.linalg.norm(J[:, :, 1], axis=1)
    g_alto, g_basso = float(np.percentile(giro, 95)), float(np.percentile(giro, 5))
    riga = ("pinne e spalle: il film si stira fino a %.2f lungo il passo e "
            "%.2f lungo il giro, su 95 triangoli su cento"
            % (lungo, g_alto))
    guai = []
    if lungo > STIRO_PASSO:
        guai.append("%.2f lungo il passo, la spalla e' troppo ripida per il "
                    "film che ha" % lungo)
    if g_alto > STIRO_GIRO:
        guai.append("%.2f lungo il giro, la grafica si allarga con la pinna"
                    % g_alto)
    if aperte and g_basso < CHIUSO_GIRO:
        guai.append("il giro si chiude a %.2f, i fianchi spariscono sul bordo "
                    "della pinna" % g_basso)
    if guai:
        return False, "GRAFICA STIRATA SULLE TESTATE - " + "; ".join(guai)
    return True, riga
