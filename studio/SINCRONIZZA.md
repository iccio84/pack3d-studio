# Tenere allineati la chat e il repository

## Il problema, detto com'e'

La chat non vede GitHub. Ragiona sulla copia del progetto che le hai dato tu, e
quella copia invecchia dal momento esatto in cui qualcuno tocca il repository.

Quando le chiedi un aggiornamento, la chat ti restituisce un progetto intero:
i file che ha cambiato **piu' tutti gli altri come se li ricordava**. Quel
pacchetto non e' un aggiornamento, e' un ritorno indietro travestito — e non se
ne accorge nessuno, perche' i file che riporta indietro sono proprio quelli di
cui non si sta parlando.

Il sintomo l'abbiamo gia' visto quattro volte di fila: lo stesso `PACK3D_MODEL`
in `agent.py` riscritto a mano a ogni giro, perche' ogni zip riportava il model
id vecchio.

## La direzione giusta

**Il repository e' la verita'. La chat si alimenta da li', non viceversa.**

```
          prima (rompeva)            adesso
       chat --zip--> GitHub      GitHub --istantanea--> chat
                                 chat --file singoli--> GitHub
```

Prima di ogni sessione di lavoro con la chat, una riga:

```bash
python istantanea.py
```

Scrive `istantanea_pack3d.md`: tutto il progetto in un file solo, ~55 mila
token, con in testa il commit da cui e' stata presa. Caricalo nella conoscenza
del progetto della chat **al posto** di quello precedente — non accanto, o si
ritrova due versioni e sceglie la sbagliata.

Se il progetto della chat offre il collegamento diretto a un repository GitHub,
usa quello e l'istantanea non serve piu': e' la stessa idea senza il passaggio a
mano. L'istantanea resta utile per una singola conversazione, o per mandare solo
i due file che contano:

```bash
python istantanea.py pack3d/flowpack.py server.py
```

## Cosa chiedere alla chat, e cosa no

| chiedi | non chiedere |
|---|---|
| i **file che cambiano**, interi, con il percorso in testa | uno zip del progetto |
| "cosa c'e' che non va e quale regola aggiungere" | "rigenera il progetto" |
| un `diff` quando la modifica e' piccola | un file "aggiornato" senza dire da quale versione parte |

L'istantanea porta gia' questa richiesta scritta in testa, quindi la chat la
legge da sola. Se nonostante tutto arriva uno zip: non applicarlo mai per
sostituzione. Confronta file per file e prendi solo quelli che c'entrano con il
caso di cui stavate parlando.

## Il punto di giunzione: `REGOLE.md`

Non e' documentazione. `agent.py` lo legge e lo infila nel system prompt
dell'agente a ogni analisi:

```python
regole = open(p, encoding="utf-8").read()
...
system=ISTRUZIONI + "\n\n# Regole del progetto\n\n" + regole
```

Quindi lo stesso file e' contemporaneamente il briefing che dai alla chat **e**
il cervello dell'agente dentro l'app. Una regola che resta indietro non e' una
riga di manuale sbagliata: e' l'agente che continua a misurare come prima.

Era successo. `REGOLE.md` diceva ancora *"le pinne di testa si misurano dal
margine non stampato"*, che su un artwork al vivo da' `end_fin = 0` — l'errore
che aveva prodotto il 21% di triangoli degeneri sul Bueno T2. Il codice era gia'
stato corretto; la regola no, e l'agente leggeva quella.

**Quindi: ogni modifica al comportamento tocca anche `REGOLE.md`, nello stesso
commit.** Se non c'e' niente da scrivere li', probabilmente non hai cambiato il
comportamento.

## Un caso studio nuovo

Un artwork che esce male non e' un motivo per rigenerare il progetto. Produce al
massimo quattro cose, e ognuna ha il suo posto:

| cosa hai imparato | dove va |
|---|---|
| una regola di lettura del disegno | `REGOLE.md` |
| qualcosa che l'analista deve fare diversamente | `ISTRUZIONI` in `agent.py` |
| un conto che il codice sbagliava | `pack3d/flowpack.py`, `server.py` |
| un impaginato che i solutori non coprono | registro `CASI` in `server.py` |

Un ramo, un commit, un caso. Se il caso nuovo ti costringe a riscrivere mezzo
`flowpack.py`, fermati: quasi sempre significa che stai generalizzando da un
campione solo.

## La domanda da farsi prima di unire

**I casi di prima escono ancora giusti?**

Oggi non lo controlla nessuno in automatico, e si e' visto: le pinne larghe il
doppio sono venute fuori solo perche' e' arrivato uno screenshot. Finche' non
c'e' una verifica automatica, questa e' la lista da ripassare a mano.

| caso | cosa tiene fermo |
|---|---|
| Milch-Schnitte T1 | l'impaginato di riferimento, nastro 144 = 43 + 15 x 2 + 14 x 2 |
| FULFIL | il caso calibrato a mano in `CASI`, riferimento del gonfio |
| Kinder Bueno T2 | pinne ricavate dalle saldature su grafica al vivo; sezione 41 x 20 e non 50 x 11 a pari perimetro |
| Kinder Pingui T1 | steso ruotato di 90 gradi; cucitura non centrata (16 + 18); fasce grinza 8 \| 10 \| 113 \| 10 \| 8 |

Il controllo minimo su ognuno: perimetro + 2 falde = nastro, e un'occhiata al
render. Le due cose insieme prendono quasi tutto.

## Quello che resta appeso

- La verifica automatica dei quattro casi qui sopra non esiste. E' il pezzo che
  renderebbe sicuro tutto il resto di questo documento.
- Il canale `quote.larghezza` / `quote.spessore` dall'agente alla costruzione
  non e' mai stato percorso con una chiave API vera.
- La texture ha rettangoli bianchi che tagliano la grafica: da capire se li
  produce `clean_artwork` o `strip_separations`.
