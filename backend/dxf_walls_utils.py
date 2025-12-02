from typing import Tuple
from wall_graph import Segment
import math

Point = tuple[float, float]

def calculate_midline_segment(seg1: Segment, seg2: Segment) -> Tuple[Point, Point]:
    """
    Вычисляет осевой сегмент между двумя параллельными линиями (сегментами).
    Для упрощения, просто берет среднюю точку между концами сегментов.
    
    ВНИМАНИЕ: Для реальных BIM-задач здесь потребуется сложная 
    геометрия (проекция, отступы и обрезка), чтобы получить идеальные углы.
    """
    
    # 1. Определяем, какая пара точек ближе (чтобы правильно сопоставить start и end)
    
    dist_start_to_start = math.dist(seg1.start, seg2.start)
    dist_start_to_end = math.dist(seg1.start, seg2.end)
    
    if dist_start_to_start < dist_start_to_end:
        # Сегменты в одном направлении
        p1a, p1b = seg1.start, seg1.end
        p2a, p2b = seg2.start, seg2.end
    else:
        # Сегменты в противоположном направлении (нужно инвертировать seg2)
        p1a, p1b = seg1.start, seg1.end
        p2a, p2b = seg2.end, seg2.start # Инвертируем p2
        
    # 2. Вычисляем среднюю точку для начала и конца
    
    mid_start = (
        (p1a[0] + p2a[0]) / 2,
        (p1a[1] + p2a[1]) / 2
    )
    
    mid_end = (
        (p1b[0] + p2b[0]) / 2,
        (p1b[1] + p2b[1]) / 2
    )

    return mid_start, mid_end
    
# TODO: В будущем добавить функцию для объединения смежных осевых линий 
# в единую полилинию (L_ось), чтобы избежать фрагментации.