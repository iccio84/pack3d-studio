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
# PACK3D_MAX_JOBS=1, non 2: una costruzione misurata arriva a 400 MB di picco
# (K Brioss, foglio da 420 x 290 mm), e le istanze Free e Starter di Render
# hanno 512 MB. Due costruzioni insieme non ci stanno, il kernel uccide il
# processo a meta' e chi aspetta si vede tornare una risposta vuota. Su una
# macchina piu' grande si rialza dall'ambiente senza toccare l'immagine.
ENV HOST=0.0.0.0 PORT=7860 PACK3D_MAX_JOBS=1
EXPOSE 7860
CMD ["python", "server.py"]
