import os
from pathlib import Path  # <--- ДОБАВЛЕНО: Необходимый импорт
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dxf_geometry import analyze_dxf_geometry

app = FastAPI(title="DWG/DXF → BIM Parser")

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
        section_path = STATE["section_file"]

        if plan_path is None:
            raise HTTPException(status_code=400, detail="DXF План не загружен. Загрузите файл Плана (Шаг 1).")
        
        if not Path(plan_path).exists():
             raise HTTPException(status_code=500, detail=f"Файл плана не найден на сервере по пути: {plan_path}")

        # --- АНАЛИЗ ГЕОМЕТРИИ ---
        full_analysis = analyze_dxf_geometry(plan_path, file_path_section=section_path)

        # <--- ИСПРАВЛЕНИЕ: Извлекаем данные из geometry_analysis
        geo = full_analysis.get("geometry_analysis", {})
        walls_data = geo.get("walls_detection", {})
        rooms_data = geo.get("rooms_detection", {})
        levels_data = geo.get("levels_detection", [])
        openings_data = geo.get("openings_detection", [])

        bim_json = {
            "source_info": full_analysis.get("source_info", {}),
            "plan": {
                "walls": walls_data.get("walls", []),
                "rooms": rooms_data.get("rooms", []),
                "openings": openings_data,
                "stats": {
                    "walls_count": walls_data.get("total_walls", 0),
                    "rooms_count": len(rooms_data.get("rooms", [])),
                    "openings_count": len(openings_data)
                }
            },
            "section": {
                "levels": levels_data if isinstance(levels_data, list) else [] 
            }
        }

        return JSONResponse(content=bim_json)

    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    
# Добавить в main.py для поддержки viewer.js
@app.get("/api/plan/last")
def get_last_plan():
    if not STATE["plan_file"] or not os.path.exists(STATE["plan_file"]):
        return {"error": "No plan uploaded"}
    # Внимание: здесь нужно вернуть JSON-структуру DXF, а не просто файл.
    # viewer.js ожидает JSON от парсера. 
    # В текущей архитектуре viewer.js несовместим с текущим main.py, 
    # так как main.py возвращает BIM-анализ, а не сырой DXF.
    return {"error": "Endpoint not implemented specifically for raw viewer"}

@app.get("/")
def root():
    return {"status": "backend is running", "state": STATE}