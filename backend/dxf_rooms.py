from __future__ import annotations
from typing import List, Dict, Any, Tuple
import ezdxf
import math


def analyze_rooms(doc: ezdxf.EzDxfDocument) -> Dict[str, Any]:
    """
    Главная функция: ищет помещения на плане.
    """

    msp = doc.modelspace()

    # ---------------------------
    # 1. Собираем кандидатов на границы помещений
    # ---------------------------
    edges = extract_room_edges(msp)

    # ---------------------------
    # 2. Строим граф соединений сегментов
    # ---------------------------
    graph = build_room_graph(edges)

    # ---------------------------
    # 3. Ищем все замкнутые циклы (полигоны)
    # ---------------------------
    polygons = find_polygons(graph)

    # ---------------------------
    # 4. Превращаем полигоны в помещения
    # ---------------------------
    rooms = assemble_rooms(polygons)

    return {
        "room_layers_used": ["auto_detect"],
        "total_polygons": len(polygons),
        "rooms": rooms
    }


# ================================================================
#  ШАГ 1 — СБОР ГРАНИЦ ПОМЕЩЕНИЙ
# ================================================================
def extract_room_edges(msp) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Ищем все геометрические объекты, которые могут формировать помещение:
    - LWPOLYLINE с флагом замкнутости
    - LINE которые лежат в границах помещений
    """

    edges = []

    # Поиск замкнутых полилиний
    for e in msp.query("LWPOLYLINE"):
        pts = [[float(x), float(y)] for x, y, *_ in e.get_points("xy")]
        if e.closed and len(pts) >= 4:
            for i in range(len(pts)):
                a = tuple(pts[i])
                b = tuple(pts[(i+1) % len(pts)])
                edges.append((a, b))

    # Линии как грани
    for e in msp.query("LINE"):
        a = (float(e.dxf.start.x), float(e.dxf.start.y))
        b = (float(e.dxf.end.x), float(e.dxf.end.y))
        edges.append((a, b))

    return edges


# ================================================================
#  ШАГ 2 — ГРАФ ГРАНЕЙ
# ================================================================
def build_room_graph(edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]):
    graph = {}

    def add(a, b):
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)

    for a, b in edges:
        add(a, b)

    return graph


# ================================================================
#  ШАГ 3 — ПОИСК ПОЛИГОНОВ (замкнутых циклов)
# ================================================================
def find_polygons(graph) -> List[List[Tuple[float, float]]]:
    """
    BFS/DFS обход для поиска циклов.
    """
    polygons = []

    visited_edges = set()

    def edge_id(a, b):
        return tuple(sorted([a, b]))

    for start in graph:
        for nxt in graph[start]:
            if edge_id(start, nxt) in visited_edges:
                continue

            path = [start, nxt]
            visited_edges.add(edge_id(start, nxt))

            current = nxt
            prev = start

            while True:
                neighbors = graph[current]
                next_nodes = [p for p in neighbors if p != prev]

                if not next_nodes:
                    break

                nxt2 = next_nodes[0]
                eid = edge_id(current, nxt2)

                if eid in visited_edges:
                    break

                path.append(nxt2)
                visited_edges.add(eid)

                prev, current = current, nxt2

                # нашёл цикл
                if nxt2 == start and len(path) > 3:
                    polygons.append(path)
                    break

    return polygons


# ================================================================
#  ШАГ 4 — СОБИРАЕМ ПОМЕЩЕНИЯ
# ================================================================
def assemble_rooms(polygons: List[List[Tuple[float, float]]]) -> List[Dict[str, Any]]:

    rooms = []
    counter = 1

    for poly in polygons:
        area = polygon_area(poly)
        perim = polygon_perimeter(poly)

        rooms.append({
            "id": f"room-auto-{counter}",
            "number": str(counter),
            "name": f"Room {counter}",
            "area": round(area, 2),
            "perimeter": round(perim, 2),
            "boundary_polygon": poly
        })

        counter += 1

    return rooms


# ================================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ================================================================
def polygon_area(poly) -> float:
    area = 0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % len(poly)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2


def polygon_perimeter(poly) -> float:
    per = 0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % len(poly)]
        per += math.dist((x1, y1), (x2, y2))
    return per

def detect_rooms(wall_graph, segments, insert_blocks):
    """
    Простая версия детектора помещений.
    Возвращает список «помещений» как заглушку MVP.
    Реальная логика появится на Этапе 3.
    """

    rooms = []

    # Попытка извлечь полигоны DXF (если есть замкнутые границы)
    polygons = extract_room_polygons(segments)

    if polygons:
        for i, poly in enumerate(polygons, start=1):
            rooms.append({
                "id": f"room-{i}",
                "boundary": poly,
                "name": f"Room {i}",
                "area": None,
                "perimeter": None,
                "floor": 1
            })

    else:
        # fallback — если полигонов нет, возвращаем пустой список
        rooms = []

    return rooms
