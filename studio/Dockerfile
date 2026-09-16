FROM python:3.11-slim

# Hugging Face Spaces esegue il container come utente 1000
RUN useradd -m -u 1000 app
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .
USER app

# 7860 e' la porta attesa dagli Spaces; Render e Railway sovrascrivono PORT
ENV HOST=0.0.0.0 PORT=7860 PACK3D_MAX_JOBS=2
EXPOSE 7860
CMD ["python", "server.py"]
