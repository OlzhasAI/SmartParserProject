
import ezdxf
from ezdxf import path
import math
from typing import Dict, List, Any, Optional, Tuple

# Module A: Semantic Material Mapper

class MaterialMapper:
    DEFAULT_MAPPING = {
        "MONOLIT": {"material": "concrete", "color": "#A9A9A9"},
        "BETON": {"material": "concrete", "color": "#A9A9A9"},
        "ЖЕЛЕЗОБЕТОН": {"material": "concrete", "color": "#A9A9A9"},
        "CONCRETE": {"material": "concrete", "color": "#A9A9A9"},

        "BLOCK": {"material": "brick", "color": "#CD5C5C"},
        "GAS": {"material": "brick", "color": "#CD5C5C"},
        "KIRPICH": {"material": "brick", "color": "#CD5C5C"},
        "BRICK": {"material": "brick", "color": "#CD5C5C"},
        "ГАЗОБЛОК": {"material": "brick", "color": "#CD5C5C"},
        "КИРПИЧ": {"material": "brick", "color": "#CD5C5C"},
    }

    def __init__(self, doc):
        self.doc = doc
        self.legend_mapping = self._parse_legend()

    def _parse_legend(self) -> Dict[str, Dict[str, str]]:
        """
        Attempts to find a legend and extract material mappings.
        Returns a dict: { pattern_name: { 'material': '...', 'color': '...' } }
        """
        mapping = {}
        msp = self.doc.modelspace()

        # 1. Find Legend Header
        legend_header = None
        for entity in msp.query("MTEXT TEXT"):
            text = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
            if not text:
                continue
            if "УСЛОВНЫЕ ОБОЗНАЧЕНИЯ" in text.upper() or "LEGEND" in text.upper():
                legend_header = entity
                break

        if not legend_header:
            return {}

        # 2. Define ROI (Region of Interest) - Below header
        # Assume header is top-left of legend
        try:
            # Get bounding box of header
            # Simple approximation from insertion point
            header_insert = legend_header.dxf.insert
            header_y = header_insert.y
            header_x = header_insert.x

            # Look for items below (y < header_y) and near x (x - 50 < item_x < x + 500)
            # Units are unknown, assuming consistent scale.

            candidates = []

            # Search area: Below header
            bbox_min_y = header_y - 2000 # Heuristic search depth
            bbox_max_y = header_y
            bbox_min_x = header_x - 100
            bbox_max_x = header_x + 1000

            # Collect Hatches and Texts in ROI
            for entity in msp.query("HATCH MTEXT TEXT"):
                if entity == legend_header:
                    continue

                # Get position (insert point or center)
                pos = None
                if entity.dxftype() == "HATCH":
                    # Hatch doesn't have a single insert point easily accessible without processing paths
                    # Use geometric center approximation or first path start
                    if len(entity.paths) > 0:
                        # Use seed point if available
                        if entity.dxf.seeds:
                            pos = entity.dxf.seeds[0]
                        else:
                             # Approximate from boundary
                             # Skipping complex bbox calc for speed, just check layer/type later
                             continue
                else:
                    pos = entity.dxf.insert

                if pos and bbox_min_x < pos.x < bbox_max_x and bbox_min_y < pos.y < bbox_max_y:
                    candidates.append(entity)

            # 3. Cluster by Y (Rows)
            # This is complex to implement robustly without visual analysis libraries.
            # Simplified approach: If we find a Hatch and a Text with similar Y, pair them.

            # For now, return empty as this requires advanced heuristic tuning
            # and the Fallback Strategy is prioritized as Crucial.
            pass

        except Exception:
            pass

        return mapping

    def get_material_props(self, layer_name: str, pattern_name: str) -> Dict[str, str]:
        """
        Returns material properties based on Legend (priority) or Fallback (layer name).
        """
        # 1. Check Legend (Not fully implemented, placeholder)
        if pattern_name in self.legend_mapping:
            return self.legend_mapping[pattern_name]

        # 2. Fallback: Check Layer Name
        layer_upper = layer_name.upper()

        for key, props in self.DEFAULT_MAPPING.items():
            if key in layer_upper:
                return props

        # Default
        return {"material": "generic", "color": "#999999"}


# Module B: Geometry Extraction (Hatch-First)

def _path_to_svg(p: path.Path) -> str:
    """Converts an ezdxf Path object to an SVG path string."""
    parts = []

    # Start
    start = p.start
    parts.append(f"M {start.x:.2f} {start.y:.2f}")

    for cmd in p:
        if cmd.type == path.Command.LINE_TO:
            parts.append(f"L {cmd.end.x:.2f} {cmd.end.y:.2f}")
        elif cmd.type == path.Command.CURVE3_TO:
            parts.append(f"Q {cmd.ctrl.x:.2f} {cmd.ctrl.y:.2f} {cmd.end.x:.2f} {cmd.end.y:.2f}")
        elif cmd.type == path.Command.CURVE4_TO:
            parts.append(f"C {cmd.ctrl1.x:.2f} {cmd.ctrl1.y:.2f} {cmd.ctrl2.x:.2f} {cmd.ctrl2.y:.2f} {cmd.end.x:.2f} {cmd.end.y:.2f}")

    parts.append("Z")
    return " ".join(parts)

def extract_walls_v2(doc) -> List[Dict[str, Any]]:
    mapper = MaterialMapper(doc)
    msp = doc.modelspace()
    walls = []

    # Filter keywords for layers
    WALL_KEYWORDS = ["WALL", "STEN", "MONOLIT", "BLOCK", "BRICK", "GAS", "PARTITION", "PEREG"]

    count = 0
    for hatch in msp.query("HATCH"):
        layer_name = hatch.dxf.layer

        # Filter by Layer
        if not any(k in layer_name.upper() for k in WALL_KEYWORDS):
            continue

        # Get Material
        pattern_name = hatch.dxf.pattern_name
        props = mapper.get_material_props(layer_name, pattern_name)

        # Extract Geometry
        try:
            # We need to construct them properly.

            # To render correctly in SVG/Canvas with holes, we can just concatenate the paths
            # into one SVG string using "M...Z M...Z". Canvas 'evenodd' rule handles holes.

            svg_parts = []

            sub_paths = path.from_hatch(hatch)

            for p in sub_paths:
                svg_parts.append(_path_to_svg(p))

            full_svg_path = " ".join(svg_parts)

            walls.append({
                "id": f"hatch_{hatch.dxf.handle}",
                "material": props["material"],
                "color": props["color"],
                "svgPath": full_svg_path,
                "thickness": 200 # Placeholder/Unknown for hatch.
                # Calculating thickness from hatch is hard (it's an area).
                # We can leave it as a visual property or estimate from area/perimeter.
            })
            count += 1

        except Exception as e:
            print(f"Error processing hatch {hatch.dxf.handle}: {e}")
            continue

    print(f"DEBUG: V2 Parser found {count} hatched walls.")
    return walls

# Module C: JSON Output Structure

def analyze_dxf_v2(doc) -> Dict[str, Any]:
    walls = extract_walls_v2(doc)

    return {
        "scene": {
            "walls": walls,
            "rooms": [], # Not implemented in this task
            "openings": [] # Not implemented in this task
        }
    }
