# Regole: Pouch

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Pouch

La busta stand-up col soffietto sul fondo - il doypack - si fa da un nastro
solo, come il flowpack, ma si monta in un altro modo, e la fustella dice
tutto. Attraverso il nastro, da un bordo all'altro: il lembo della saldatura
longitudinale, il primo pannello, la piega in cima alla busta con la
saldatura alta divisa sui due lati, il secondo pannello lungo quanto il
primo, e la striscia del soffietto, che chiude sul lembo. Lungo il nastro il
passo e' la larghezza della busta, e ai due capi ci sono le saldature
laterali. Tutte le saldature sono piatte: niente zigrinatura. Il codice sta in
`pack3d/pouch.py`.

### Si legge dalla piega

La piega e' la linea che ha ai due lati due fasce uguali - la saldatura
alta, una per pannello - e i due pannelli, dalla piega al fondo, sono lunghi
uguali. Quello che avanza e' il soffietto, piu' corto di un pannello: il suo
corpo, fra le due fasce di saldatura, e' la profondita' della base a busta
piena. Passo, nastro e saldature laterali li legge il lettore del flowpack:
sono le sue testate. La struttura si prova dai due bordi dello steso, perche'
il soffietto puo' stare in alto o in basso sulla tavola. Nessuna misura
cucita: sul primo pouch il nastro e' 466 = 195 + 195 + 76, con la saldatura
alta 8 + 8 attorno alla piega e il soffietto 8 + 60 + 8.

### Il fronte lo dice la grafica, il verso lo dice la piega

Fronte e retro escono dallo stesso nastro piegato in cima. Il fronte e' il
pannello con piu' grafica: sul primo pouch dieci volte quella del retro, che
e' fondo, una fascia e lo spazio per la data. Se i due si somigliano troppo,
il cartellino lo dice. Il verso invece non si legge dal testo: la cima della
busta e' la piega, un punto ha la stessa x sul fronte e sul retro, e la mappa
conserva il verso del foglio. Cosi' la grafica non si specchia comunque stia
lo steso sulla tavola: girato di 90, 180 e 270 gradi, il primo pouch da' lo
stesso modello.

### La forma della busta piena

Il film non si allunga, quindi ogni sezione fra le saldature laterali e'
lunga quanto il pannello, e dove la busta si gonfia si stringe: sul fondo,
aperta dal soffietto fino alla sua profondita', la larghezza fra le
saldature passa da 175 a 160 mm. La mezza profondita' scende dal fondo alla
saldatura alta, la sezione si chiude sulle saldature laterali fra una
parabola e un'ellisse, e la base e' il corpo del soffietto aperto, una lente
fra fronte e retro con la stampa del soffietto. Nelle saldature fronte e
retro restano a uno spessore di film, perche' non si sovrappongano.

### Cosa manca

La zip e il taglio laser per aprire non si modellano: stanno sotto la
saldatura alta, e da fuori si vedono appena. Gli angoli del fondo, dove il
soffietto si salda dentro le laterali, sono a punta invece che smussati.
