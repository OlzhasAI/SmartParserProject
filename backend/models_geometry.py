from dataclasses import dataclass
from typing import Tuple

@dataclass
class Segment:
    start: Tuple[float, float]
    end: Tuple[float, float]
    layer: str
    length: float
