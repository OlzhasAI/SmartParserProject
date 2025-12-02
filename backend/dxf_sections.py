from __future__ import annotations
import re
import ezdxf
from typing import List, Dict, Any


# ===============================
# 1) ПАРСИНГ ОДНОЙ ОТМЕТКИ
# ===============================
def parse_level_text(text: str) -> float | None:
    """
    Принимает текст типа '+3.300', 'Отм. +0.000', '11.250'
    Возвращает float или None, если уровня нет.
    """

    if not text:
        return None

    # Убираем мусор и пробелы
    cleaned = text.replace("Отм.", "").replace("отм.", "").strip()
    cleaned = cleaned.replace(",", ".")  # на всякий

    # Поддержка форматов:
    # +3.300, -0.150, 11.250
    level_regex = r"([+-]?\d+[\.,]?\d*)"

    match = re.search(level_regex, cleaned)
    if not match:
        return None

    try:
        value = float(match.group(1))
        return value
    except:
        return None


# ===============================
# 2) ПОИСК ВСЕХ ОТМЕТОК В DXF
# ===============================
def extract_levels_from_dxf(file_path: str) -> List[Dict[str, Any]]:
    """
    Находит все текстовые отметки в разрезе.
    Возвращает список словарей:
    [
       {"raw": "+3.300", "value": 3.3},
       {"raw": "Отм. +0.000", "value": 0.0},
    ]
    """

    try:
        doc = ezdxf.readfile(file_path)
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки DXF: {e}")

    msp = doc.modelspace()

    results = []

    for e in msp:
        text_value = None

        if e.dxftype() == "TEXT":
            text_value = e.dxf.text

        elif e.dxftype() == "MTEXT":
            text_value = e.text

        if text_value:
            level = parse_level_text(text_value)
            if level is not None:
                results.append({
                    "raw": text_value,
                    "value": level
                })

    # Удаляем дубли по числовому значению
    unique = {}
    for r in results:
        unique[r["value"]] = r

    result_list = list(unique.values())

    # Сортировка по уровню
    result_list.sort(key=lambda x: x["value"])

    return result_list


# ===============================
# 3) ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ===============================
def extract_levels_summary(file_path: str) -> Dict[str, Any]:
    """
    Возвращает удобную структуру:
    {
        "levels": [...],
        "min": -3.150,
        "max": 27.000,
        "floors": 10
    }
    """
    levels = extract_levels_from_dxf(file_path)

    if not levels:
        return {
            "levels": [],
            "min": None,
            "max": None,
            "floors": 0
        }

    values = [v["value"] for v in levels]

    return {
        "levels": levels,
        "min": min(values),
        "max": max(values),
        "floors": len(levels)
    }
