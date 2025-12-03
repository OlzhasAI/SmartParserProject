from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

import ezdxf

from wall_graph import (
    build_wall_graph, 
    Segment, 
    segments_are_parallel_and_collinear, 
    vector_distance_point_to_segment,
    get_segment_direction,
    vector_normalize
) 
from dxf_walls_utils import calculate_midline_segment

# Заменяем Tuple на стандартный тип tuple
Point = tuple[float, float]

# -------------------------------------------------------------------
# 1. Слои, где могут быть стены
# -------------------------------------------------------------------
WALL_LAYERS_CANDIDATES = {
    "СТЕНА",
    "СТЕНЫ",
    "STENA",
    "СТЕНЫ2",
    "стена",
    "AR_WALL_OUTER",
    "AR_WALL_INNER",
    "АР_Газоблок наруж",
    "АР_Газоблок 200мм",
    "АР_ГКЛ",
    "АР_Монолит",
    "PEREG",
    "PARTITION",
    "GKL",
    "BRICK",
    "GAS",
    "ПЕРЕГОРОДКИ",
}

# -------------------------------------------------------------------
# 2. Структуры данных
# -------------------------------------------------------------------

@dataclass
class WallSegment:
    layer: str
    start: Point
    end: Point

    @property
    def length(self) -> float:
        return math.dist(self.start, self.end)

    @property
    def direction(self) -> Tuple[float, float]:
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        L = math.hypot(dx, dy)
        if L == 0:
            return (0, 0)
        return (dx / L, dy / L)


@dataclass
class Wall:
    id: str
    layer: str
    start: Point
    end: Point
    length: float
    source_type: str = "merged"


# -------------------------------------------------------------------
# 3. Утилиты
# -------------------------------------------------------------------

def determine_material(layer_name: str) -> str:
    """Определяет материал стены по имени слоя."""
    layer = layer_name.upper()
    if any(x in layer for x in ["MONOLIT", "ЖЕЛЕЗОБЕТОН", "CONCRETE", "МОНОЛИТ"]):
        return "concrete"
    if any(x in layer for x in ["GAS", "BLOCK", "ГАЗОБЛОК", "KIRPICH", "BRICK", "БЛОК", "КИРПИЧ"]):
        return "brick"
    if any(x in layer for x in ["PEREG", "GKL", "PARTITION", "ПЕРЕГОРОДКИ", "ГКЛ"]):
        return "partition"
    return "generic"

def to_mm(val: float) -> float:
    """Конвертирует значение в мм, если оно похоже на метры (меньше 50)."""
    # Эвристика: стены толщиной > 50м не бывают, значит это мм.
    # Стены < 50 единиц считаем метрами (0.2м = 200мм).
    if val < 50.0:
        return val * 1000.0
    return val

def _get_wall_polygon_corners(start: Point, end: Point, thickness: float) -> List[Point]:
    """Генерирует 4 угла для стены, заданной осевой линией и толщиной."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # Нормаль к вектору стены
    # Вектор (-dy, dx) перпендикулярен (dx, dy)
    normal = vector_normalize((-dy, dx))

    half_t = thickness / 2.0
    ox = normal[0] * half_t
    oy = normal[1] * half_t

    p1 = (start[0] + ox, start[1] + oy)
    p2 = (end[0] + ox, end[1] + oy)
    p3 = (end[0] - ox, end[1] - oy)
    p4 = (start[0] - ox, start[1] - oy)

    return [p1, p2, p3, p4]

# -------------------------------------------------------------------
# 4. Парсинг геометрии
# -------------------------------------------------------------------

def _collect_segments(doc: ezdxf.EzDxfDocument) -> List[Segment]:
    """Считываем все геометрические сегменты, которые могут быть стенами."""
    # Используем Segment из wall_graph, чтобы не дублировать код
    msp = doc.modelspace()
    segs: List[Segment] = []

    for entity in msp.query('LINE LWPOLYLINE'):
        layer = entity.dxf.layer
        # Проверка по ключевым словам (substring match)
        layer_upper = layer.upper()
        if not any(k.upper() in layer_upper for k in WALL_LAYERS_CANDIDATES):
            continue

        if entity.dxftype() == 'LINE':
            start = (float(entity.dxf.start.x), float(entity.dxf.start.y))
            end = (float(entity.dxf.end.x), float(entity.dxf.end.y))
            length = math.dist(start, end)
            segs.append(Segment(start=start, end=end, layer=layer, length=length))

        elif entity.dxftype() == 'LWPOLYLINE':
            pts = [(float(x), float(y)) for x, y, *_ in entity.get_points('xy')]
            for p1, p2 in zip(pts, pts[1:]):
                length = math.dist(p1, p2)
                segs.append(Segment(start=p1, end=p2, layer=layer, length=length))

            if entity.closed and len(pts) > 2:
                length = math.dist(pts[-1], pts[0])
                segs.append(Segment(start=pts[-1], end=pts[0], layer=layer, length=length))

    return segs


# -------------------------------------------------------------------
# 5. Основной анализ
# -------------------------------------------------------------------

def analyze_walls(doc: ezdxf.EzDxfDocument) -> Dict[str, Any]:
    """Основная точка входа для API."""
    all_segments = _collect_segments(doc)
    segments = list(enumerate(all_segments)) 
    
    walls: List[Dict[str, Any]] = []
    wall_id = 1
    processed_indices = set()
    
    # 1. Поиск ПАРНЫХ СЕГМЕНТОВ (стены с толщиной)
    for i, seg1 in segments:
        if i in processed_indices: continue

        best_pair = None
        best_thickness = 0
        
        for j, seg2 in segments:
            if j == i or j in processed_indices: continue

            if segments_are_parallel_and_collinear(seg1, seg2):
                dist1 = vector_distance_point_to_segment(seg2.start, seg1.start, seg1.end)
                dist2 = vector_distance_point_to_segment(seg2.end, seg1.start, seg1.end)
                thickness = (dist1 + dist2) / 2
                
                if thickness > best_thickness: 
                    best_thickness = thickness
                    best_pair = j

        if best_pair is not None:
            seg2 = segments[best_pair][1]
            
            # Вычисляем осевую
            mid_start, mid_end = calculate_midline_segment(seg1, seg2) 

            # Определяем координаты полигона (4 угла)
            # Нужно правильно упорядочить точки двух сегментов
            dist_start_to_start = math.dist(seg1.start, seg2.start)
            dist_start_to_end = math.dist(seg1.start, seg2.end)

            if dist_start_to_start < dist_start_to_end:
                 # Сонаправлены
                 # Порядок обхода: Start1 -> End1 -> End2 -> Start2 -> Start1
                 corners = [seg1.start, seg1.end, seg2.end, seg2.start]
            else:
                 # Противонаправлены (seg2 перевернут относительно seg1)
                 # Порядок обхода: Start1 -> End1 -> Start2 -> End2 -> Start1
                 corners = [seg1.start, seg1.end, seg2.start, seg2.end]

            material = determine_material(seg1.layer)
            thickness_mm = round(to_mm(best_thickness), 1)

            walls.append({
                "id": f"wall-{wall_id}",
                "type": "wall",
                "layer": seg1.layer,
                "material": material,

                # Геометрия для совместимости (осевая)
                "start": mid_start, 
                "end": mid_end,
                "length": math.dist(mid_start, mid_end),

                # Новые поля
                "thickness": thickness_mm,
                "source_type": "paired_thick_wall",
                "coordinates": corners,
            })
            processed_indices.add(i)
            processed_indices.add(best_pair)
            wall_id += 1

    # 2. Обработка ОСТАВШИХСЯ СЕГМЕНТОВ
    remaining_segments = [seg for i, seg in segments if i not in processed_indices]
    
    DEFAULT_THICKNESS = 0.1 # Метры, если координаты в метрах
    # Но если проект в мм, это 0.1 мм?
    # Давайте попробуем угадать масштаб по длине сегментов?
    # Или просто использовать константу, которую потом to_mm превратит в 100мм.

    # Для одиночных линий считаем толщину 100 мм по дефолту

    for seg in remaining_segments:
        material = determine_material(seg.layer)

        # Генерируем полигон искусственно (расширяем линию)
        # Предполагаем thickness 100mm (0.1m) если это перегородка
        # Если это несущая стена (MONOLIT), может 200mm?
        if material == "concrete":
            assumed_thickness = 0.2
        elif material == "brick":
            assumed_thickness = 0.2
        elif material == "partition":
            assumed_thickness = 0.1
        else:
            assumed_thickness = 0.1

        # Проверяем масштаб координат. Если длина сегмента > 1000, то скорее всего мм.
        # Тогда assumed_thickness тоже должен быть в мм (100, 200).
        if seg.length > 500: # Скорее всего мм
             assumed_thickness *= 1000.0

        thickness_mm = round(to_mm(assumed_thickness), 1)

        corners = _get_wall_polygon_corners(seg.start, seg.end, assumed_thickness)

        walls.append({
            "id": f"wall-{wall_id}",
            "type": "wall",
            "layer": seg.layer,
            "material": material,

            "start": seg.start,
            "end": seg.end,
            "length": seg.length,

            "thickness": thickness_mm,
            "source_type": "single_line_wall",
            "coordinates": corners,
        })
        wall_id += 1
        
    return {
        "total_segments": len(all_segments),
        "total_walls": len(walls),
        "wall_layers_used": sorted({w['layer'] for w in walls}),
        "walls": walls,
    }
