# Risorse

Grafica di riferimento che non viene dall'artwork.

## colata_kinder.png

La colata di latte Kinder **come deve venire**, fornita dall'utente.
2000 x 488 px, RGB.

### Cos'e', misurato

E' **lo stesso disegno** che sta nell'artwork del Kinder Pingui T6 BOX, non un
disegno diverso: sovrapponendo le due onde alla stessa scala combaciano cresta
per cresta, goccia compresa, con la sua bollicina satellite. La misura e' il
periodo dell'onda, preso dallo spettro della curva rosso/bianco:

    artwork    periodo 20,08 mm
    risorsa    periodo 80,0 px

cioe' la risorsa e' disegnata a **3,98 px/mm**, e i suoi 2000 x 488 px coprono
**502 x 122 mm** alla scala dell'artwork. Sono circa **101 dpi**.

### Cosa cambia rispetto al nostro reso

Il disegno e' identico, il RESO no:

- nella risorsa la cresta bianca ha **un'ombra azzurra sottile, solo sotto**;
- nel nostro reso l'azzurro e' un **alone spesso e sfumato sopra e sotto**, e
  la cresta bianca ne esce slavata.

E' la sovrastampa: l'ombra e' una lastra di ciano che sovrastampa il rosso, e
pdfium la rende come un azzurro normale e opaco. Vedi in REGOLE.md
*La grafica va in quadricromia, non in RGB*.

### Perche' non e' ancora in uso

Per sostituirla servono due cose che questo file non ha:

1. **dove va.** Un PNG porta i pixel, non la posizione. Nell'artwork del
   Pingui la colata non e' un oggetto solo che si possa scambiare: il campo
   delle gocce e' una immagine RGB (259,8 x 219,0 mm, riquadro noto) e la
   fascia dell'onda e' vettoriale, e niente nel file dice "questa e' la
   colata". Serve la colata su un **livello suo**: vedi in REGOLE.md
   *La colata si sostituisce solo se sta su un livello suo*;
2. **la risoluzione.** A 101 dpi sta sotto ai 200 dpi con cui si costruisce la
   texture in qualita' web e ai 300 della qualita' alta. Incollarla cosi'
   peggiorerebbe quella fascia invece di migliorarla.

Finche' mancano, sta qui come **riferimento visivo** di cosa si deve ottenere.
