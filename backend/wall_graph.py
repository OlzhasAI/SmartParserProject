from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math
import numpy as np  # <--- ДОЛЖЕН БЫТЬ ЭТОТ ИМПОРТ!

Point = tuple[float, float]

@dataclass
class Segment:
    start: tuple[float, float]
    end: tuple[float, float]
    layer: str = ""
    length: float = 0.0  # <--- ДОБАВЛЕНО!

@dataclass
class GraphSegment:
    index: int
    start: Point
    end: Point
    length: float


class WallGraph:
    """
    Граф сегментов стен — объединяет сегменты по совпадающим концам
    (с привязкой snap_eps).
    """

    def __init__(self, segments: List[GraphSegment], snap_eps: float = 1.0) -> None:
        self.segments = segments
        self.snap_eps = snap_eps
        self._adj: Dict[int, List[int]] = {}
        self._build()

    def _snap(self, p: Point) -> Point:
        x, y = p
        k = self.snap_eps
        return (round(x / k) * k, round(y / k) * k)

    def _build(self) -> None:
        node_map: Dict[Point, List[int]] = {}

        for seg in self.segments:
            s = self._snap(seg.start)
            e = self._snap(seg.end)

            node_map.setdefault(s, []).append(seg.index)
            node_map.setdefault(e, []).append(seg.index)

        # Строим список смежности
        for ids in node_map.values():
            for i in ids:
                self._adj.setdefault(i, [])
                for j in ids:
                    if i != j and j not in self._adj[i]:
                        self._adj[i].append(j)

    def connected_components(self) -> List[List[int]]:
        visited = set()
        result: List[List[int]] = []

        for idx in range(len(self.segments)):
            if idx in visited:
                continue

            stack = [idx]
            comp = []

            while stack:
                i = stack.pop()
                if i in visited:
                    continue
                visited.add(i)
                comp.append(i)
                stack.extend(self._adj.get(i, []))

            result.append(comp)

        return result

# Добавить в начало backend/wall_graph.py

def vector_normalize(v: tuple[float, float]) -> tuple[float, float]:
    """Нормализует вектор до единичной длины."""
    x, y = v
    length = math.hypot(x, y)
    return (x / length, y / length) if length > 1e-6 else (0, 0)

def vector_distance_point_to_segment(p: Point, a: Point, b: Point) -> float:
    """
    Вычисляет кратчайшее расстояние от точки P до отрезка AB.
    """
    import numpy as np
    
    # Конвертируем в numpy для векторной математики
    p = np.array(p)
    a = np.array(a)
    b = np.array(b)

    # Длина сегмента
    l2 = np.sum((b - a)**2)
    if l2 == 0.0:
        return np.linalg.norm(p - a)

    # Проекция точки на линию (параметр t)
    t = np.dot(p - a, b - a) / l2
    
    # Если t < 0, ближайшая точка — A
    if t < 0.0:
        return np.linalg.norm(p - a)
    
    # Если t > 1, ближайшая точка — B
    if t > 1.0:
        return np.linalg.norm(p - b)
        
    # Ближайшая точка находится на сегменте
    projection = a + t * (b - a)
    return np.linalg.norm(p - projection)

def get_segment_direction(seg: Segment) -> tuple[float, float]:
    """Возвращает нормализованное направление сегмента."""
    dx = seg.end[0] - seg.start[0]
    dy = seg.end[1] - seg.start[1]
    return vector_normalize((dx, dy))

def segments_are_parallel_and_collinear(seg1: Segment, seg2: Segment, angle_eps: float = 0.01, snap_eps: float = 1.0) -> bool:
    """Проверяет, параллельны ли сегменты и достаточно ли близки для толщины."""
    dir1 = get_segment_direction(seg1)
    dir2 = get_segment_direction(seg2)
    
    # Проверка на параллельность (угол 0 или 180 градусов)
    dot_product = abs(dir1[0] * dir2[0] + dir1[1] * dir2[1])
    is_parallel = abs(dot_product - 1.0) < angle_eps

    if not is_parallel:
        return False
        
    # Проверка на расстояние (для толщины)
    # Используем одну точку L2 и измеряем расстояние до L1
    distance = vector_distance_point_to_segment(seg2.start, seg1.start, seg1.end)
    
    # Проверяем, что толщина лежит в реалистичных пределах (80мм до 600мм, как ты просил)
    if 0.08 < distance < 0.6: 
        return True
        
    return False

# ВАЖНО: Не забудьте добавить import numpy в начало wall_graph.py,
# если его там нет (хотя, ezdxf иногда тянет его за собой)
# import numpy as np

def build_wall_graph(segments, snap_eps: float = 1.0) -> WallGraph:
    """
    Обёртка: превращаем Segment → GraphSegment и строим граф.
    """
    graph_segments = [
        GraphSegment(
            index=i,
            start=s.start,
            end=s.end,
            length=s.length
        )
        for i, s in enumerate(segments)
    ]

    return WallGraph(graph_segments, snap_eps=snap_eps)

def find_cycles(graph, max_length=200):
    """
    Поиск минимальных замкнутых циклов в графе стен.
    graph: словарь {node: [connected_nodes]}
    Возвращает список циклов, каждый - список точек.
    """

    cycles = []
    visited_edges = set()

    for start_node in graph:
        for next_node in graph[start_node]:
            edge = tuple(sorted([start_node, next_node]))
            if edge in visited_edges:
                continue

            path = [start_node, next_node]
            visited_edges.add(edge)
            current = next_node
            prev = start_node

            # Обход по часовой стрелке
            for _ in range(max_length):
                candidates = [n for n in graph[current] if n != prev]
                if not candidates:
                    break

                # Выбираем "самый правый" вектор
                chosen = min(
                    candidates,
                    key=lambda n: angle_from(prev, current, n)
                )

                path.append(chosen)
                prev, current = current, chosen

                if chosen == start_node:
                    # нашли цикл
                    cycles.append(path[:-1])
                    break

    # Удаляем дубликаты
    unique_cycles = []
    for c in cycles:
        s = tuple(sorted(c))
        if s not in unique_cycles:
            unique_cycles.append(s)

    return unique_cycles

import math

def angle_from(a, b, c):
    """Вычисляет угол ABC для выбора направления обхода."""
    ax, ay = a
    bx, by = b
    cx, cy = c
    v1 = (ax - bx, ay - by)
    v2 = (cx - bx, cy - by)
    ang = math.atan2(
        v1[0]*v2[1] - v1[1]*v2[0],
        v1[0]*v2[0] + v1[1]*v2[1]
    )
    return ang if ang > 0 else ang + 2 * math.pi
