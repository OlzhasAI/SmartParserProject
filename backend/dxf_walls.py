from __future__ import annotations
import math
from dataclasses import dataclass # <--- ЭТОТ ИМПОРТ ДОЛЖЕН БЫТЬ
from typing import List, Tuple, Dict, Any

import ezdxf

from wall_graph import (
    build_wall_graph, 
    Segment, 
    segments_are_parallel_and_collinear, 
    vector_distance_point_to_segment,
    get_segment_direction
) 
from dxf_walls_utils import calculate_midline_segment # <-- Эту функцию мы добавим ниже

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
# 3. Парсинг геометрии
# -------------------------------------------------------------------

def _collect_segments(doc: ezdxf.EzDxfDocument) -> List[Segment]:
    """Считываем все геометрические сегменты, которые могут быть стенами."""
    # Используем Segment из wall_graph, чтобы не дублировать код
    msp = doc.modelspace()
    segs: List[Segment] = []

    for entity in msp.query('LINE LWPOLYLINE'):
        layer = entity.dxf.layer
        if layer not in WALL_LAYERS_CANDIDATES:
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
# 4. Основной анализ
# -------------------------------------------------------------------

# backend/dxf_walls.py

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

            walls.append({
                "id": f"wall-{wall_id}",
                "layer": seg1.layer,
                # ВАЖНО: Используем ключи 'start' и 'end', чтобы фронтенд понял!
                "start": mid_start, 
                "end": mid_end,
                "length": math.dist(mid_start, mid_end),
                "thickness": round(best_thickness, 3),
                "source_type": "paired_thick_wall",
            })
            processed_indices.add(i)
            processed_indices.add(best_pair)
            wall_id += 1

    # 2. Обработка ОСТАВШИХСЯ СЕГМЕНТОВ
    remaining_segments = [seg for i, seg in segments if i not in processed_indices]
    
    for seg in remaining_segments:
        walls.append({
            "id": f"wall-{wall_id}",
            "layer": seg.layer,
            # ВАЖНО: Используем ключи 'start' и 'end'
            "start": seg.start,
            "end": seg.end,
            "length": seg.length,
            "thickness": 0.1, 
            "source_type": "single_line_wall",
        })
        wall_id += 1
        
    return {
        "total_segments": len(all_segments),
        "total_walls": len(walls),
        "wall_layers_used": sorted({w['layer'] for w in walls}),
        "walls": walls,
    }
