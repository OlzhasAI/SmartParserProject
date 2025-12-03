import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import ezdxf

# Import V2 Parser
from dxf_parser_v2 import analyze_dxf_v2

app = FastAPI(title="DWG/DXF → BIM Parser (V2 Hatch-Based)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

STATE = {
    "plan_file": None,
    "section_file": None,
}

@app.post("/api/plan/upload")
async def upload_plan(file: UploadFile = File(...)):
    try:
        file_id = os.urandom(8).hex()
        filename = f"plan_{file_id}.dxf"
        save_path = os.path.join(UPLOAD_DIR, filename)

        with open(save_path, "wb") as f:
            f.write(await file.read())

        STATE["plan_file"] = save_path
        return {"status": "ok", "file_id": file_id, "path": save_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/section/upload")
async def upload_section(file: UploadFile = File(...)):
    try:
        file_id = os.urandom(8).hex()
        filename = f"section_{file_id}.dxf"
        save_path = os.path.join(UPLOAD_DIR, filename)

        with open(save_path, "wb") as f:
            f.write(await file.read())

        STATE["section_file"] = save_path
        return {"status": "ok", "file_id": file_id, "path": save_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bim/build")
async def build_bim():
    try:
        plan_path = STATE["plan_file"]

        if plan_path is None:
            raise HTTPException(status_code=400, detail="DXF План не загружен. Загрузите файл Плана (Шаг 1).")
        
        if not Path(plan_path).exists():
             raise HTTPException(status_code=500, detail=f"Файл плана не найден на сервере по пути: {plan_path}")

        # --- ЗАГРУЗКА DXF ---
        try:
            doc = ezdxf.readfile(plan_path)
        except Exception as e:
            raise ValueError(f"Ошибка чтения DXF файла: {e}")

        # --- АНАЛИЗ ГЕОМЕТРИИ (V2 HATCH-BASED) ---
        # Возвращает структуру { "scene": { "walls": [...], ... } }
        bim_json = analyze_dxf_v2(doc)

        return JSONResponse(content=bim_json)

    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/")
def root():
    return {"status": "backend is running (V2)", "state": STATE}
