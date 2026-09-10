# PDF di riferimento

Qui vanno gli artwork gia' risolti, quelli che compaiono nelle tabelle di
`REGOLE.md`. Servono al corpus di regressione: ogni regola della pipeline e'
stata pagata con un errore su uno di questi file, e senza una prova che li
rimisuri ogni modifica ai solutori puo' rompere un caso che funzionava.

**I PDF non stanno nel repository.** Sono artwork di clienti: vanno copiati a
mano in questa cartella, che e' ignorata da git. Le prove che li richiedono si
salteranno da sole quando il file non c'e' (`unittest.SkipTest`), cosi' la
suite resta verde su una copia pulita.

## File attesi

| nome atteso | famiglia | quote da verificare |
|---|---|---|
| `kms_t10.pdf` | astuccio | quote L/H/P, verso di fasciatura, verso delle normali |
| `milch_schnitte_t1.pdf` | flowpack | nastro 144,0 / fronte 43,0 / fianco 15,0 / falda 14,0 |
| `fulfil.pdf` | flowpack | nastro 141,0 / fronte 36,0 / fianco 19,5 / falda 15,0 |
| `kinder_bueno_dark.pdf` | flowpack | nastro 415,0 / fronte 150,5 / fianco 41,0 / falda 16,0 |
| `nutella_pot_sleeve.pdf` | coppa | residuo 0,000 mm dal DT in miniatura, fondo 72,0-72,32 mm |

I nomi contano: sono quelli che le prove cercano. Se il file che hai si chiama
diversamente, rinominalo invece di cambiare la prova.

## Cosa deve verificare il corpus

Le quote della tabella sono il minimo. Le tre verifiche che hanno gia' fatto
danno un modello sbagliato in passato, e che quindi vanno nel corpus:

1. **Le coerenze fisiche del flowpack** — perimetro + 2 falde = nastro,
   retro = fronte, corpo + 2 pinne di testa = passo. Sono le stesse tre che
   `_flowpack_from_ai_json` usa per rifiutare una geometria non misurata.
2. **Il verso delle normali** — non l'attributo NORMAL, l'avvolgimento dei
   triangoli: e' quello che i viewer usano per il culling, ed e' il motivo per
   cui gli astucci sono stati consegnati due volte con le facce all'interno.
3. **La tipologia non si indovina** — su Kinder Bueno Dark il solutore astuccio
   restituisce 275,0 x 101,9 x 31,0 invece di 150,5 x 41,0. Numeri plausibili e
   sbagliati: la prova deve fissare che con `kind="flowpack"` esca la seconda
   coppia.
