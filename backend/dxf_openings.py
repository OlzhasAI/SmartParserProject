# backend/dxf_openings.py

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import math
import ezdxf
from ezdxf.math import Vec3, Matrix44

from wall_graph import vector_distance_point_to_segment

# Ключевые слова для поиска блоков
LAYER_KEYWORDS = {
    "WINDOW": ["WINDOW", "ВИТРАЖ", "ОКНО", "WIN"],
    "DOOR": ["ДВЕРЬ", "DOOR", "ДВ"]
}

# КРИТИЧЕСКАЯ ПЕРЕМЕННАЯ: 1000 единиц (1 метр в мм)
MAX_DISTANCE_TOLERANCE = 1000.0 
# ---------------------------------

def get_block_geometry_center(insert: ezdxf.entities.Insert, doc: ezdxf.EzDxfDocument) -> Tuple[float, float]:
    """
    Вычисляет центр геометрии блока в глобальных координатах,
    применяя матрицу трансформации (сдвиг, поворот, масштаб)
    ко всем линиям внутри блока.
    """
    block_name = insert.dxf.name
    if block_name not in doc.blocks:
        return float(insert.dxf.insert.x), float(insert.dxf.insert.y)

    block = doc.blocks.get(block_name)
    matrix = insert.matrix44()

    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    found_geometry = False

    for entity in block:
        points = []
        if entity.dxftype() == 'LINE':
            points = [entity.dxf.start, entity.dxf.end]
        elif entity.dxftype() == 'LWPOLYLINE':
            # LWPolyline точки могут быть 2D
            points = entity.get_points('xy')
            # Конвертируем в Vec3 для корректной работы matrix.transform_vertices
            points = [Vec3(p[0], p[1], 0) for p in points]
        elif entity.dxftype() == 'POLYLINE':
             points = list(entity.points())

        if points:
            # Трансформируем точки в глобальные координаты
            transformed_points = list(matrix.transform_vertices([Vec3(p) for p in points]))

            for p in transformed_points:
                found_geometry = True
                if p.x < min_x: min_x = p.x
                if p.x > max_x: max_x = p.x
                if p.y < min_y: min_y = p.y
                if p.y > max_y: max_y = p.y

    if not found_geometry:
        # Если геометрии нет, возвращаем точку вставки
        return float(insert.dxf.insert.x), float(insert.dxf.insert.y)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    return center_x, center_y


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
            
        # 3. ИЗВЛЕЧЕНИЕ ПАРАМЕТРОВ (с учетом трансформации)
        # Получаем реальные координаты центра объекта через трансформацию геометрии блока
        real_x, real_y = get_block_geometry_center(insert, doc)
        rotation = float(insert.dxf.rotation)
        
        scale_x = abs(insert.dxf.xscale)
        width = scale_x 
        
        # Логика определения ширины остается прежней (по скейлу),
        # но можно было бы улучшить через bbox (max_x - min_x)
        if width > 50: 
            width /= 1000.0
        elif width < 0.2:
            width = 0.9 if opening_type == "door" else 1.2
            
        # 4. ПРИВЯЗКА К СТЕНЕ (Host Wall)
        host_wall_id = None
        min_dist = float('inf')
        
        p_insert = (real_x, real_y)
        
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
                "position": [real_x, real_y],
                "width": round(width, 2),
                "rotation": rotation,
                "wall_id": host_wall_id,
                "block_name": name
            })
        else:
            # DEBUG: Причина 2: Блок найден, но не привязался к стене
            print(f"SKIP: Блок {name} ({opening_type}) не привязался к стене (Min Dist: {min_dist} at {real_x:.2f}, {real_y:.2f}).")

    print(f"DEBUG: Финальное количество найденных проемов: {len(openings)}")
    print("-" * 50)
    return openings
