FROM python:3.11-slim

# Hugging Face Spaces esegue il container come utente 1000
RUN useradd -m -u 1000 app
WORKDIR /app

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
