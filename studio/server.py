import os
import tempfile
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

# Importazione dinamica o standard dei moduli interni della pipeline
try:
    from pack3d import flowpack, dieline, exporters
except ImportError:
    import flowpack
    import dieline
    import exporters

app = FastAPI(title="Pack3D Service")

# --- GESTIONE INTERFACCIA E FILE STATICI ---
# Monta la cartella static se esiste per servire JS, CSS, Asset
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    """
    Ritorna l'interfaccia utente (index.html).
    Se index.html non si trova nella root, prova a cercarlo dentro la cartella static.
    """
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    elif os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    else:
        return {
            "status": "online",
            "message": "Pack3D API Backend attivo. Metti un file index.html nella root per caricare l'interfaccia grafica."
        }


# --- LOGICA DI CONVERSIONE PDF -> GLB ---
def process_pdf_to_glb(pdf_bytes: bytes, kind: str = "cartotecnico", teeth: int = 0, gonfiore: str = "medio") -> bytes:
    """
    Invocazione della pipeline deterministica per la generazione e lettura del file GLB binario.
    """
    kind = kind.lower().strip()
    
    if kind == "altro":
        raise ValueError("La tipologia 'Altro' non e' ancora supportata.")

    if not exporters:
        raise NotImplementedError("Modulo exporters.py non caricato correttamente.")

    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tmp:
        tmp_glb_path = tmp.name

    try:
        # 1. CASO FLOWPACK (mesh triangolare)
        if kind == "flowpack":
            if not flowpack:
                raise NotImplementedError("Modulo flowpack.py non disponibile.")
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                tmp_pdf.write(pdf_bytes)
                tmp_pdf_path = tmp_pdf.name

            try:
                if hasattr(flowpack, "analyze_auto"):
                    try:
                        fp = flowpack.analyze_auto(tmp_pdf_path)
                    except Exception:
                        fp = flowpack.analyze(tmp_pdf_path)
                elif hasattr(flowpack, "analyze"):
                    fp = flowpack.analyze(tmp_pdf_path)
                else:
                    raise NotImplementedError("Funzione di analisi non trovata in flowpack.py")

                V, UV, tris = flowpack.build_mesh(fp, serr_teeth=teeth)
                exporters.write_glb_mesh(V, UV, tris, None, tmp_glb_path)
            finally:
                if os.path.exists(tmp_pdf_path):
                    try:
                        os.remove(tmp_pdf_path)
                    except OSError:
                        pass

        # 2. CASO CARTOTECNICO / ASTUCCI (facce / pannelli)
        else:
            if not dieline:
                raise NotImplementedError("Modulo dieline.py non disponibile.")

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                tmp_pdf.write(pdf_bytes)
                tmp_pdf_path = tmp_pdf.name

            try:
                if hasattr(dieline, "analyze"):
                    dieline_obj = dieline.analyze(tmp_pdf_path)
                elif hasattr(dieline, "analyze_auto"):
                    dieline_obj = dieline.analyze_auto(tmp_pdf_path)
                else:
                    raise NotImplementedError("Funzione 'analyze' non trovata in dieline.py")

                faces = getattr(dieline_obj, "panels", dieline_obj)
                exporters.write_glb(faces, tmp_glb_path)
            finally:
                if os.path.exists(tmp_pdf_path):
                    try:
                        os.remove(tmp_pdf_path)
                    except OSError:
                        pass

        with open(tmp_glb_path, "rb") as fh:
            glb_data = fh.read()

        return glb_data

    finally:
        if os.path.exists(tmp_glb_path):
            try:
                os.remove(tmp_glb_path)
            except OSError:
                pass


# --- ENDPOINT API ---
@app.post("/generate-3d")
async def generate_3d(
    file: UploadFile = File(...),
    kind: str = Form("cartotecnico"),
    teeth: int = Form(0),
    gonfiore: str = Form("medio")
):
    """
    Endpoint per convertire un file PDF di fustella/artwork in un modello 3D GLB.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Il file inviato deve essere un PDF.")

    try:
        pdf_bytes = await file.read()
        glb_bytes = process_pdf_to_glb(
            pdf_bytes=pdf_bytes,
            kind=kind,
            teeth=teeth,
            gonfiore=gonfiore
        )
        return Response(content=glb_bytes, media_type="model/gltf-binary")

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except NotImplementedError as nie:
        raise HTTPException(status_code=501, detail=str(nie))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'elaborazione del 3D: {str(e)}")


# --- AVVIO SERVER ---
if __name__ == "__main__":
    import uvicorn
    # Legge dinamicamente la porta fornita da Render ($PORT) o usa la 8000 in locale
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
