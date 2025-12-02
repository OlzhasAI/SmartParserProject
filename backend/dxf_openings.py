# backend/dxf_openings.py

from __future__ import annotations
from typing import List, Dict, Any
import math
import ezdxf

from wall_graph import vector_distance_point_to_segment

# Ключевые слова для поиска блоков
LAYER_KEYWORDS = {
    "WINDOW": ["WINDOW", "ВИТРАЖ", "ОКНО", "WIN"],
    "DOOR": ["ДВЕРЬ", "DOOR", "ДВ"]
}

# КРИТИЧЕСКАЯ ПЕРЕМЕННАЯ: 1000 единиц (1 метр в мм)
MAX_DISTANCE_TOLERANCE = 1000.0 
# ---------------------------------

def analyze_openings(doc: ezdxf.EzDxfDocument, walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ищет блоки (INSERT) по имени блока ИЛИ по имени слоя, и привязывает их к ближайшей стене.
    """
    msp = doc.modelspace()
    openings = []
    
    # --- ДЕБАГ: НАЧАЛО РАБОТЫ ---
    all_inserts = list(msp.query('INSERT'))
    print("-" * 50)
    print(f"DEBUG: Начинаем поиск проемов. Найдено {len(all_inserts)} INSERT-объектов.")
    print(f"DEBUG: Стен для привязки: {len(walls)}.")
    print(f"DEBUG: Допуск на привязку (мм): {MAX_DISTANCE_TOLERANCE}")
    
    for insert in all_inserts:
        name = insert.dxf.name.upper()
        layer = insert.dxf.layer.upper()
        
        opening_type = None
        
        # 1. ОПРЕДЕЛЕНИЕ ТИПА (ПРИОРИТЕТ СЛОЯ - самый надежный способ для АР)
        if "АР_ОКНА И ВИТРАЖИ" in layer or "АР_ОКНА" in layer or "ОКНА" in layer or "ВИТРАЖИ" in layer:
            opening_type = "window"
        elif "АР_ДВЕРЬ" in layer or "ДВЕРЬ" in layer:
            opening_type = "door"
            
        # 2. Проверка по имени БЛОКА (если слой не помог)
        if not opening_type:
            if any(k in name for k in LAYER_KEYWORDS["WINDOW"]):
                opening_type = "window"
            elif any(k in name for k in LAYER_KEYWORDS["DOOR"]):
                opening_type = "door"
            
        if not opening_type:
            # Блок пропущен, потому что не похож на проем
            continue
            
        # 3. ИЗВЛЕЧЕНИЕ ПАРАМЕТРОВ (если блок прошел фильтр)
        x = float(insert.dxf.insert.x)
        y = float(insert.dxf.insert.y)
        rotation = float(insert.dxf.rotation)
        
        scale_x = abs(insert.dxf.xscale)
        width = scale_x 
        
        if width > 50: 
            width /= 1000.0
        elif width < 0.2:
            width = 0.9 if opening_type == "door" else 1.2
            
        # 4. ПРИВЯЗКА К СТЕНЕ (Host Wall)
        host_wall_id = None
        min_dist = float('inf')
        
        p_insert = (x, y)
        
        for wall in walls:
            w_start = wall['start']
            w_end = wall['end']
            
            dist = vector_distance_point_to_segment(p_insert, w_start, w_end)
            
            # Используем 1000 мм для допуска
            if dist < MAX_DISTANCE_TOLERANCE and dist < min_dist: 
                min_dist = dist
                host_wall_id = wall['id']
        
        # 5. Добавляем найденный объект, ТОЛЬКО ЕСЛИ ОН ПРИВЯЗАН К СТЕНЕ
        if host_wall_id:
            openings.append({
                "id": f"opening-{len(openings)+1}",
                "type": opening_type,
                "layer": insert.dxf.layer,
                "position": [x, y],
                "width": round(width, 2),
                "rotation": rotation,
                "wall_id": host_wall_id,
                "block_name": name
            })
        else:
            # DEBUG: Причина 2: Блок найден, но не привязался к стене
            print(f"SKIP: Блок {name} ({opening_type}) не привязался к стене (Min Dist: {min_dist}).")

    print(f"DEBUG: Финальное количество найденных проемов: {len(openings)}")
    print("-" * 50)
    return openings