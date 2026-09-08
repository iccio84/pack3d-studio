import os
import json
import tempfile
from typing import Optional
from fastapi import FastAPI, Request, Response, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Importazione dei moduli interni della pipeline
try:
    from pack3d import flowpack, dieline, exporters
except ImportError:
    import flowpack
    import dieline
    import exporters

app = FastAPI(title="Pack3D Studio Service")

# --- GESTIONE INTERFACCIA E FILE STATICI ---
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    elif os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return JSONResponse({"status": "online", "message": "File index.html non trovato nella root."})


# --- ENDPOINT DI PING / SALUTE ---
@app.get("/api/ping")
@app.get("/ping")
async def ping():
    """Conferma la presenza e lo stato attivo del backend all'interfaccia utente."""
    return {"status": "ok", "service": "pack3d"}


# --- CORE LOGIC: CONVERSIONE PDF -> GLB ---
def process_pdf_bytes(pdf_bytes: bytes, kind: str = "cartotecnico", teeth: int = 0, gonfiore: str = "medio") -> bytes:
    kind = (kind or "cartotecnico").lower().strip()
    if kind in ["carton", "cartotecnica"]:
        kind = "cartotecnico"

    if kind == "altro":
        raise ValueError("La tipologia 'Altro' non è ancora supportata.")

    if not exporters:
        raise NotImplementedError("Modulo exporters.py non disponibile.")

    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tmp:
        tmp_glb_path = tmp.name

    try:
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

                V, UV, tris = flowpack.build_mesh(fp, serr_teeth=int(teeth or 0))
                exporters.write_glb_mesh(V, UV, tris, None, tmp_glb_path)
            finally:
                if os.path.exists(tmp_pdf_path):
                    try: os.remove(tmp_pdf_path)
                    except OSError: pass

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
                    try: os.remove(tmp_pdf_path)
                    except OSError: pass

        with open(tmp_glb_path, "rb") as fh:
            glb_data = fh.read()

        return glb_data

    finally:
        if os.path.exists(tmp_glb_path):
            try: os.remove(tmp_glb_path)
            except OSError: pass


# --- ENDPOINT PER L'INTERFACCIA ORIGINALE (/api/analyze & /api/build) ---
@app.post("/api/analyze")
async def api_analyze(request: Request):
    try:
        header_opt = request.headers.get("X-Pack3d", "{}")
        opts = json.loads(header_opt)
        kind = opts.get("kind", "cartotecnico")
        return {"meta": [f"Tipologia: {kind}"], "title": "Analisi completata"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/build")
async def api_build(request: Request):
    pdf_bytes = await request.body()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Nessun file PDF inviato.")

    try:
        header_opt = request.headers.get("X-Pack3d", "{}")
        opts = json.loads(header_opt)
    except Exception:
        opts = {}

    kind = opts.get("kind", "cartotecnico")
    teeth = opts.get("teeth", 0)
    gonfiore = opts.get("soft", "medio")

    try:
        glb_bytes = process_pdf_bytes(pdf_bytes, kind=kind, teeth=teeth, gonfiore=gonfiore)
        return Response(content=glb_bytes, media_type="model/gltf-binary")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINT STANDARD MULTIPART (/generate-3d) ---
@app.post("/generate-3d")
async def generate_3d(
    file: UploadFile = File(...),
    kind: str = Form("cartotecnico"),
    teeth: int = Form(0),
    gonfiore: str = Form("medio")
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Il file deve essere un PDF.")

    pdf_bytes = await file.read()
    try:
        glb_bytes = process_pdf_bytes(pdf_bytes, kind=kind, teeth=teeth, gonfiore=gonfiore)
        return Response(content=glb_bytes, media_type="model/gltf-binary")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- AVVIO SERVER ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
