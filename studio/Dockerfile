FROM python:3.11-slim

# Hugging Face Spaces esegue il container come utente 1000
RUN useradd -m -u 1000 app
WORKDIR /app

# Ghostscript serve a una cosa sola, e non c'e' altro modo di farla: simulare
# la SOVRASTAMPA. pdfium non la simula - verificato con un PDF costruito
# apposta, un ciano sopra un magenta con /OP true e senza: esce identico - e
# senza sovrastampa la colata Kinder perde l'ombra sulle gocce, che diventa un
# alone azzurro piatto. Vedi REGOLE.md, *La colata si rimette con l'inchiostro
# del file*.
#
# Costa una quarantina di MB di immagine e non si vede mai al lavoro: gira
# solo sui file che hanno la colata su un livello suo, e solo sulla sua banda.
# Se manca, il codice se ne accorge e usa la risorsa: non si rompe niente.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ghostscript \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .
USER app

# 7860 e' la porta attesa dagli Spaces; Render e Railway sovrascrivono PORT
#
# PACK3D_MAX_JOBS=1, e NON alzarlo. Passando a una macchina da 16 GB l'ho
# alzato a 2 - la memoria ci stava larga, 648 MB il picco peggiore - e l'ho
# provato con due flowpack insieme: il server e' morto tutto intero, a meta'
# della seconda costruzione, senza traceback. Il perche' sta nel dmesg:
#
#     traps: python3 trap int3 in libpdfium.so
#
# pdfium non e' thread-safe, e non lo e' nemmeno su documenti diversi: due
# chiamate insieme sporcano l'heap nativo e si portano via il processo - cioe'
# anche il lavoro di chi non c'entrava niente. Questo limite non si compra con
# la RAM: per farne due davvero servono due PROCESSI, non due thread.
#
# La seconda richiesta prende un 503 con invito a riprovare. Meglio respingere
# che far cadere il servizio.
ENV HOST=0.0.0.0 PORT=7860 PACK3D_MAX_JOBS=1
EXPOSE 7860
CMD ["python", "server.py"]
