# Risorse

Grafica di riferimento che non viene dall'artwork.

## colata_kinder.png

La colata di latte Kinder **come deve venire**, fornita dall'utente.
2000 x 488 px, RGB. E' in uso: vedi in REGOLE.md *La colata si sostituisce solo
se sta su un livello suo*.

### Cos'e', misurato

E' un **master**: lo stesso disegno che sta negli artwork Kinder, ma non il
ritaglio di un pack. Sovrapponendolo all'onda di un artwork, portato al suo
passo, le due combaciano cresta per cresta, goccia e bollicina satellite
comprese.

Il passo pero' **cambia da pack a pack**, quindi la risorsa non ha una scala
sua: la scala si ricava file per file dal rapporto fra i due periodi.

    Kinder Pingui T6 BOX   onda da 20,08 mm nell'artwork
    KP T1 Mandarino        onda da 17,13 mm nell'artwork
    risorsa                onda da 80,0 px

### Cosa cambia rispetto al nostro reso

Il disegno e' identico, il RESO no:

- nella risorsa la cresta bianca ha **un'ombra azzurra sottile, solo sotto**;
- nel nostro reso l'azzurro e' un **alone spesso e sfumato sopra e sotto**, e
  la cresta bianca ne esce slavata.

E' la sovrastampa: l'ombra e' una lastra di ciano che sovrastampa il rosso, e
pdfium la rende come un azzurro normale e opaco. Vedi in REGOLE.md
*La grafica va in quadricromia, non in RGB*.

### Il limite che ha: la risoluzione

Portata al passo dell'artwork la risorsa sta attorno ai **110 dpi** (109 sul
KP T1 Mandarino), mentre la texture si costruisce a 200 dpi in qualita' web e a
300 in qualita' alta. Viene quindi ingrandita di circa 1,8 volte.

Su questo disegno si puo' fare, e non e' una scusa: la colata e' fatta di campi
pieni e di bordi morbidi, senza dettaglio fine, e un ingrandimento LANCZOS di
1,8 su una cosa cosi' non si vede - mentre l'alone che toglie si vedeva eccome.
Ma resta un limite: **una risorsa alla risoluzione di stampa sarebbe meglio**,
e su un pack piu' grande, dove l'ingrandimento crescerebbe, servirebbe.
