# -*- coding: utf-8 -*-

import FreeCAD
import Part
import Sketcher
import math
from .kle_json_cleaner import countCols, countRows, countKeys


# ............................................................................

def drawRect(sketch, x, y, w, h, r, k):
    """Draws a rectangle"""

    if sketch is None:
        return False

    # kerf: the beam burns k/2 off each side, so the cut path is drawn that much smaller
    w, h, r = w - k, h - k, max(r - k / 2, 0)

    lft = x - (w / 2)
    rte = x + (w / 2)
    top = y + (h / 2)
    btm = y - (h / 2)

    # Batch geometry/constraints to reduce per-call overhead when creating many keys.
    if r > 0:
        z = max(w, h) / 2
        if r > z:
            r = z;

        i_lft = lft + r
        i_rte = rte - r
        i_top = top - r
        i_btm = btm + r

        geoms = [
            Part.LineSegment(FreeCAD.Vector(i_lft, top, 0), FreeCAD.Vector(i_rte, top, 0)),
            Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(i_rte, i_top, 0), FreeCAD.Vector(0, 0, 1), r), 0.0, math.pi / 2),
            Part.LineSegment(FreeCAD.Vector(rte, i_top, 0), FreeCAD.Vector(rte, i_btm, 0)),
            Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(i_rte, i_btm, 0), FreeCAD.Vector(0, 0, 1), r), 1.5 * math.pi, 2 * math.pi),
            Part.LineSegment(FreeCAD.Vector(i_rte, btm, 0), FreeCAD.Vector(i_lft, btm, 0)),
            Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(i_lft, i_btm, 0), FreeCAD.Vector(0, 0, 1), r), math.pi, 1.5 * math.pi),
            Part.LineSegment(FreeCAD.Vector(lft, i_btm, 0), FreeCAD.Vector(lft, i_top, 0)),
            Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(i_lft, i_top, 0), FreeCAD.Vector(0, 0, 1), r), math.pi / 2, math.pi),
        ]
    else:
        geoms = [
            Part.LineSegment(FreeCAD.Vector(lft, top, 0), FreeCAD.Vector(rte, top, 0)),
            Part.LineSegment(FreeCAD.Vector(rte, top, 0), FreeCAD.Vector(rte, btm, 0)),
            Part.LineSegment(FreeCAD.Vector(rte, btm, 0), FreeCAD.Vector(lft, btm, 0)),
            Part.LineSegment(FreeCAD.Vector(lft, btm, 0), FreeCAD.Vector(lft, top, 0)),
        ]
    geom_indices = sketch.addGeometry(geoms, False)

    # Block only: with exact arc angles the ends already meet, and Coincident constraints
    # between blocked items make the solver slow on large layouts
    sketch.addConstraint([Sketcher.Constraint('Block', idx) for idx in geom_indices])

    return True # Success

# ----------------------------------------------------------------------------

def drawFrame(sketch, width, height):
    p_vec = FreeCAD.Vector(width / -2, height / 2, 0)

    home_p = Part.Point(p_vec)
    home_i = sketch.addGeometry(home_p, True)
    dx_idx = sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 0, 1, width))
    dy_idx = sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 0, 1, height))
    sketch.setDatum(dx_idx, FreeCAD.Units.Quantity(f"{(width / -2):.6f} mm"))
    sketch.setDatum(dy_idx, FreeCAD.Units.Quantity(f"{(height / 2):.6f} mm"))

    ln1 = Part.LineSegment(p_vec, FreeCAD.Vector(p_vec.x + width, p_vec.y, 0))
    ln1_idx = sketch.addGeometry(ln1, False)
    sketch.addConstraint(Sketcher.Constraint('Coincident', ln1_idx, 1, 0, 1))
    sketch.addConstraint(Sketcher.Constraint('Horizontal', ln1_idx))
    len1_idx = sketch.addConstraint(Sketcher.Constraint('DistanceX', ln1_idx, 1, ln1_idx, 2, width))
    sketch.setDatum(len1_idx, FreeCAD.Units.Quantity(f"{width:.6f} mm"))

    ln2 = Part.LineSegment(FreeCAD.Vector(width / 2, height / 2, 0), FreeCAD.Vector(width / 2, height / -2, 0))
    ln2_idx = sketch.addGeometry(ln2, False)
    len2_idx = sketch.addConstraint(Sketcher.Constraint('DistanceY', ln2_idx, 2, ln2_idx, 1, height))
    sketch.setDatum(len2_idx, FreeCAD.Units.Quantity(f"{height:.6f} mm"))
    sketch.addConstraint(Sketcher.Constraint('Coincident', ln2_idx, 1, ln1_idx, 2))
    sketch.addConstraint(Sketcher.Constraint('Perpendicular', ln1_idx, ln2_idx))

    ln3 = Part.LineSegment(FreeCAD.Vector(width / 2, height / -2, 0), FreeCAD.Vector(width / -2, height / -2, 0))
    ln3_idx = sketch.addGeometry(ln3, False)
    sketch.addConstraint(Sketcher.Constraint('Coincident', ln3_idx, 1, ln2_idx, 2))
    sketch.addConstraint(Sketcher.Constraint('Parallel', ln3_idx, ln1_idx))

    ln4 = Part.LineSegment(FreeCAD.Vector(width / -2, height / -2, 0), FreeCAD.Vector(width / -2, height / 2, 0))
    ln4_idx = sketch.addGeometry(ln4, False)
    sketch.addConstraint(Sketcher.Constraint('Coincident', ln4_idx, 1, ln3_idx, 2))
    sketch.addConstraint(Sketcher.Constraint('Coincident', ln4_idx, 2, ln1_idx, 1))
    sketch.addConstraint(Sketcher.Constraint('Parallel', ln4_idx, ln2_idx))

    return home_i

# ----------------------------------------------------------------------------

def findKeyCenters(kle_clean, m_w, m_h):
    """loop over a clean key array and insert the center coordinates as c:e"""

    if not kle_clean:
        return False

    h_w = countCols(kle_clean) / -2
    h_h = countRows(kle_clean) / 2

    for row in kle_clean:
        if not isinstance(row, list):
            continue
        for item in row:
            if isinstance(item, dict):
                item["cx"] = (h_w + (item.get("x",0) + (item.get("w",1)/2))) * m_w
                item["cy"] = (h_h - (item.get("y",0) + (item.get("h",1)/2))) * m_h

    return kle_clean

# ----------------------------------------------------------------------------

def drawCenter(sketch, cx, cy):
    """Render draft point representing the center"""

    if sketch is None:
        return False

    i = sketch.addGeometry(Part.Point(FreeCAD.Vector(cx, cy, 0)), True)
    sketch.addConstraint(Sketcher.Constraint('Block', i))

    return True

# ----------------------------------------------------------------------------

class CutoutCollector:
    """Stand-in for a sketch: the draw functions add their geometry here, so that
    addCutouts puts all of it into the real sketch with one call."""

    def __init__(self):
        self.loops = []
        self.construction = []

    def addGeometry(self, geoms, construction=False):
        (self.construction if construction else self.loops).append(list(geoms))
        return list(range(len(geoms)))

    def addConstraint(self, constraints):
        pass  # addCutouts adds the Block constraints

# ----------------------------------------------------------------------------

def _edgeToGeometry(edge, snap=lambda p: p):
    """Turn a line, arc or circle edge back into sketch geometry. `snap` maps each end point,
    so that ends that nearly meet become one point."""
    if isinstance(edge.Curve, Part.Line):
        return Part.LineSegment(snap(edge.Vertexes[0].Point), snap(edge.Vertexes[-1].Point))
    if edge.isClosed():  # a full circle: its start and end are the same point
        return Part.Circle(edge.Curve.Center, FreeCAD.Vector(0, 0, 1), edge.Curve.Radius)
    p1 = snap(edge.valueAt(edge.FirstParameter))
    pm = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    p2 = snap(edge.valueAt(edge.LastParameter))
    arc = Part.ArcOfCircle(p1, pm, p2)
    if arc.Axis.z < 0:  # sketch arcs run counterclockwise
        arc = Part.ArcOfCircle(p2, pm, p1)
    return arc

# ----------------------------------------------------------------------------

def addCutouts(sketch, loops, construction=()):
    """Add the cutout loops, and the construction geometry from CutoutCollector, to the
    sketch. Each item is frozen with a Block constraint."""

    ids = list(sketch.addGeometry([g for loop in loops for g in loop], False))
    construction_geoms = [g for gs in construction for g in gs]
    if construction_geoms:
        ids += list(sketch.addGeometry(construction_geoms, True))
    sketch.addConstraint([Sketcher.Constraint('Block', i) for i in ids])
