from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List


def generate_stub_result(task_id: str, file_name: str) -> Dict[str, Any]:
    """
    Генерирует тестовый BIM-объект.
    Здесь НЕТ настоящего анализа DWG/DXF – только пример структуры,
    чтобы фронт видел «живой» JSON.
    """
    processed_at = datetime.utcnow().isoformat() + "Z"

    rooms: List[Dict[str, Any]] = [
        {
            "id": "room-1",
            "number": "101",
            "name": "Комната 101",
            "area": 18.5,
            "perimeter": 17.2,
            "floor": 1,
            "level_mark": 0,
            "boundary_polygon": [
                [0, 0],
                [4, 0],
                [4, 4.5],
                [0, 4.5],
            ],
            "enclosures": ["wall-1", "wall-2", "wall-3", "wall-4", "window-1", "door-1"],
        },
        {
            "id": "room-2",
            "number": "102",
            "name": "Комната 102",
            "area": 12.3,
            "perimeter": 14.0,
            "floor": 1,
            "level_mark": 0,
            "boundary_polygon": [
                [4, 0],
                [7, 0],
                [7, 4],
                [4, 4],
            ],
            "enclosures": ["wall-2", "wall-5", "wall-6", "window-2"],
        },
    ]

    walls: List[Dict[str, Any]] = [
        {
            "id": "wall-1",
            "type": "outer",
            "geometry": {"points": [[0, 0], [4, 0]]},
            "length": 4.0,
            "thickness": 0.25,
            "floor": 1,
            "start_room": "room-1",
            "end_room": None,
            "layer": "AR_WALL_OUTER",
        }
    ]

    windows: List[Dict[str, Any]] = [
        {
            "id": "window-1",
            "wall_id": "wall-1",
            "position": [2.0, 0.0],
            "width": 1.2,
            "height": 1.5,
            "block_name": "W_1200x1500",
        }
    ]

    doors: List[Dict[str, Any]] = [
        {
            "id": "door-1",
            "wall_id": "wall-2",
            "room_from": "room-1",
            "room_to": "room-2",
            "width": 0.9,
            "height": 2.0,
            "block_name": "DOOR_900",
        }
    ]

    summary: Dict[str, Any] = {
        "rooms_count": len(rooms),
        "walls_count": len(walls),
        "windows_count": len(windows),
        "doors_count": len(doors),
        "notes": "Части BIM-структуры пока тестовые (заглушка). Геометрия DXF анализируется отдельно.",
    }

    qc_report: Dict[str, Any] = {
        "errors": [],
        "warnings": [],
        "summary": "QC пока не выполняется, так как используется заглушка BIM-структуры.",
    }

    return {
        "task_id": task_id,
        "file_name": file_name,
        "processed_at": processed_at,
        "source_info": {},          # этот блок потом перезапишем из analyze_dxf_geometry
        "geometry_analysis": None,  # сюда тоже кладём результат геометрии
        "summary": summary,
        "rooms": rooms,
        "walls": walls,
        "windows": windows,
        "doors": doors,
        "qc_report": qc_report,
    }
