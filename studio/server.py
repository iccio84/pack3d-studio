import os
import tempfile
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response

# Importazione dinamica o standard dei moduli interni
try:
    from pack3d import flowpack, dieline, exporters
except ImportError:
    import flowpack
    import dieline
    import exporters

app = FastAPI(title="Pack3D Service")


def process_pdf_to_glb(pdf_bytes: bytes, kind: str = "cartotecnico", teeth: int = 0, gonfiore: str = "medio") -> bytes:
    """
    Invocazione della pipeline deterministica per la generazione e lettura del file GLB binario.
    """
    kind = kind.lower().strip()
    
    # Regola REGOLE.md
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
                # Esegue l'analisi per ricavare l'oggetto Flowpack
                if hasattr(flowpack, "analyze_auto"):
                    try:
                        fp = flowpack.analyze_auto(tmp_pdf_path)
                    except Exception:
                        fp = flowpack.analyze(tmp_pdf_path)
                elif hasattr(flowpack, "analyze"):
                    fp = flowpack.analyze(tmp_pdf_path)
                else:
                    raise NotImplementedError("Funzione di analisi non trovata in flowpack.py")

                # Costruisce la mesh (V, UV, tris)
                V, UV, tris = flowpack.build_mesh(fp, serr_teeth=teeth)
                
                # Export del file GLB
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
                # Esegue l'analisi della fustella tramite la funzione analyze() di dieline.py
                if hasattr(dieline, "analyze"):
                    dieline_obj = dieline.analyze(tmp_pdf_path)
                elif hasattr(dieline, "analyze_auto"):
                    dieline_obj = dieline.analyze_auto(tmp_pdf_path)
                else:
                    raise NotImplementedError("Funzione 'analyze' non trovata in dieline.py")

                # Estrae le facce/pannelli strutturati pronti per exporters.write_glb
                faces = getattr(dieline_obj, "panels", dieline_obj)

                # Scrive il file GLB basato sui pannelli ricavati
                exporters.write_glb(faces, tmp_glb_path)
            finally:
                if os.path.exists(tmp_pdf_path):
                    try:
                        os.remove(tmp_pdf_path)
                    except OSError:
                        pass

        # Legge il file GLB appena generato e lo restituisce in byte
        with open(tmp_glb_path, "rb") as fh:
            glb_data = fh.read()

        return glb_data

    finally:
        if os.path.exists(tmp_glb_path):
            try:
                os.remove(tmp_glb_path)
            except OSError:
                pass


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
