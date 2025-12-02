# backend/dxf_geometry.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

import ezdxf

# Импорты модулей анализа
from dxf_walls import analyze_walls
from dxf_rooms import analyze_rooms
from dxf_sections import extract_levels_from_dxf
from dxf_openings import analyze_openings


# -----------------------------------------------------------
# Служебные функции
# -----------------------------------------------------------

def _collect_layers(doc: ezdxf.EzDxfDocument) -> List[Dict[str, str]]:
    return [{"name": layer.dxf.name} for layer in doc.layers]


def _collect_entity_counts(doc: ezdxf.EzDxfDocument) -> Dict[str, int]:
    msp = doc.modelspace()
    counts: Dict[str, int] = {}
    for e in msp:
        etype = e.dxftype()
        counts[etype] = counts.get(etype, 0) + 1
    return counts


def _collect_examples(doc: ezdxf.EzDxfDocument) -> Dict[str, Any]:
    msp = doc.modelspace()

    line_examples = []
    for e in msp.query("LINE"):
        line_examples.append(
            {
                "layer": e.dxf.layer,
                "start": [float(e.dxf.start.x), float(e.dxf.start.y)],
                "end": [float(e.dxf.end.x), float(e.dxf.end.y)]
            }
        )
        if len(line_examples) >= 5:
            break

    poly_examples = []
    for e in msp.query("LWPOLYLINE"):
        try:
            pts = [[float(x), float(y)] for x, y, *_ in e.get_points("xy")]
            poly_examples.append({"layer": e.dxf.layer, "points": pts})
        except:
            pass
        if len(poly_examples) >= 5:
            break

    insert_examples = []
    for e in msp.query("INSERT"):
        insert_examples.append(
            {
                "layer": e.dxf.layer,
                "block_name": e.dxf.name,
                "insert_point": [float(e.dxf.insert.x), float(e.dxf.insert.y)]
            }
        )
        if len(insert_examples) >= 5:
            break

    return {
        "lines": line_examples,
        "polylines": poly_examples,
        "inserts": insert_examples,
    }


# -----------------------------------------------------------
# Основная функция анализа
# -----------------------------------------------------------

def analyze_dxf_geometry(file_path_plan: str,
                         file_path_section: str | None = None) -> Dict[str, Any]:
    """
    Анализ плана + опционально анализ разреза.
    """

    # 1. ЗАГРУЗКА ФАЙЛА (Вот это самое важное место!)
    plan_path = Path(file_path_plan)
    if not plan_path.exists():
        raise FileNotFoundError(f"DXF файл не найден: {file_path_plan}")

    try:
        # ВОТ ЭТОЙ СТРОКИ НЕ ХВАТАЛО:
        doc = ezdxf.readfile(str(plan_path))
    except Exception as e:
        raise ValueError(f"Ошибка чтения DXF файла: {e}")

    # 2. СБОР МЕТАДАННЫХ
    source_info = {
        "is_dxf": True,
        "layers_count": len(doc.layers),
        "layers": _collect_layers(doc),
        "entity_counts": _collect_entity_counts(doc),
        "examples": _collect_examples(doc)
    }

    # 3. АНАЛИЗ ГЕОМЕТРИИ (Стены, Окна, Помещения)
    
    # Сначала анализируем стены (переменная doc теперь существует!)
    walls_detection = analyze_walls(doc)
    
    # Берем список найденных стен, чтобы передать его в анализ окон
    walls_list = walls_detection.get("walls", [])
    
    # Анализируем проемы (окна/двери)
    openings_detection = analyze_openings(doc, walls_list)
    
    # Анализируем помещения
    rooms_detection = analyze_rooms(doc)

    # 4. АНАЛИЗ РАЗРЕЗА (Если файл был загружен)
    levels_detection = []
    if file_path_section:
        sec_path = Path(file_path_section)
        if sec_path.exists():
            try:
                levels_detection = extract_levels_from_dxf(str(sec_path))
            except Exception as e:
                levels_detection = {"error": str(e)}
        else:
            levels_detection = {"error": "Файл разреза не найден"}

    # 5. СБОРКА РЕЗУЛЬТАТА
    geometry_analysis = {
        "walls_detection": walls_detection,
        "rooms_detection": rooms_detection,
        "levels_detection": levels_detection,
        "openings_detection": openings_detection, # Добавляем проемы в ответ
    }

    return {
        "source_info": source_info,
        "geometry_analysis": geometry_analysis,
    }