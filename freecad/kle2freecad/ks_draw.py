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

    lft = x - (w / 2)
    rte = x + (w / 2)
    top = y + (h / 2)
    btm = y - (h / 2)

    # TODO : account for `kerf`

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

def drawCherryKey(sketch, cx, cy, flt_r, kerf):
    """Draws a 14x14 plate cutout"""

    z = 14
    return drawRect(sketch, cx, cy, z, z, flt_r, kerf)

# ----------------------------------------------------------------------------

def drawCherryStab(sketch, cx, cy, width, height, angle, flt_r, kerf):
    """Draws a plate stab cutout"""

    o_r = int(((angle % 360) / 90.0) + 0.5) % 4
    z = max(width, height)
    if z >= 7:
        o_o = 57.15
    elif z >= 6.25:
        o_o = 50.0
    elif z >= 6:
        o_o = 47.63
    elif z >= 3:
        o_o = 19.05
    elif z >= 2:
        o_o = 11.94
    else:
        o_o = 0

    if (o_r & 1) == 0:
        x1 = cx - o_o
        x2 = cx + o_o
        y1 = y2 = cy + (-1.5 if o_r == 0 else 1.5)
        w = 7
        h = 15
    else:
        x1 = x2 = cx + (-1.5 if o_r == 1 else 1.5)
        y1 = cy - o_o
        y2 = cy + o_o
        w = 15
        h = 7

    # quarter turns that point each pad's opposite-side version the right way:
    # the opposite side is the same pad moved 3 mm, to the other side of the key center line
    k = {0: 0, 1: 3, 2: 2, 3: 1}[o_r]
    drawStabPad(sketch, x1, y1, 7, 15, flt_r, k)
    drawStabPad(sketch, x2, y2, 7, 15, flt_r, k)
    return True

# ----------------------------------------------------------------------------

def drawStabPad(sketch, x, y, w, h, r, k, shift=3.0):
    """Draw one stabilizer pad of w x h mm centered on (x, y) as real geometry, plus the
    pad for the opposite orientation (moved `shift` mm along the pad) as construction
    geometry. Everything is turned k quarter turns counterclockwise; with k = 0 the
    opposite pad is above.

    Each side of the pad is two lines: the lower one only this pad uses, the upper one
    both pads share. So in the Sketcher, with Toggle construction geometry:

    Double-sided, one pad of w x (h + shift) mm that fits both orientations:
      - real -> construction: the pad's top line and its two top arcs
      - construction -> real: the two side extensions, and the opposite pad's top line
        and two top arcs

    Swap to the opposite orientation:
      - real -> construction: the pad's bottom line, two bottom arcs, two lower side
        lines, top line and two top arcs
      - construction -> real: the two side extensions, and the opposite pad's top line,
        two top arcs, bottom line and two bottom arcs"""

    z = max(w, h) / 2
    if r > z:
        r = z
    a, t = w / 2, h / 2

    def P(px, py):  # local point -> sketch point
        for _ in range(k):
            px, py = -py, px
        return FreeCAD.Vector(x + px, y + py, 0)

    def line(x1, y1, x2, y2):
        return Part.LineSegment(P(x1, y1), P(x2, y2))

    def arc(acx, acy, start):  # quarter arc, counterclockwise from `start`
        s = start + k * math.pi / 2
        return Part.ArcOfCircle(Part.Circle(P(acx, acy), FreeCAD.Vector(0, 0, 1), r), s, s + math.pi / 2)

    real = [
        line(-a + r, -t, a - r, -t),  # bottom
        line(a, -t + r, a, -t + shift + r),    # right side, this pad only
        line(a, -t + shift + r, a, t - r),     # right side, common to both pads
        line(a - r, t, -a + r, t),             # top, inside the opposite pad
        line(-a, t - r, -a, -t + shift + r),   # left side, common to both pads
        line(-a, -t + shift + r, -a, -t + r),  # left side, this pad only
    ]
    construction = [
        line(a, t - r, a, t + shift - r),           # right side extension
        line(-a, t - r, -a, t + shift - r),         # left side extension
        line(a - r, t + shift, -a + r, t + shift),  # opposite pad top
        line(-a + r, -t + shift, a - r, -t + shift),  # opposite pad bottom, a reference only
    ]
    if r > 0:
        real += [
            arc(a - r, -t + r, 1.5 * math.pi),  # bottom right
            arc(a - r, t - r, 0),               # top right
            arc(-a + r, t - r, 0.5 * math.pi),  # top left
            arc(-a + r, -t + r, math.pi),       # bottom left
        ]
        construction += [
            arc(a - r, t + shift - r, 0),               # opposite pad top right
            arc(-a + r, t + shift - r, 0.5 * math.pi),  # opposite pad top left
            arc(-a + r, -t + shift + r, math.pi),       # opposite pad bottom left, a reference only
            arc(a - r, -t + shift + r, 1.5 * math.pi),  # opposite pad bottom right, a reference only
        ]

    ids = list(sketch.addGeometry(real, False)) + list(sketch.addGeometry(construction, True))
    sketch.addConstraint([Sketcher.Constraint('Block', i) for i in ids])
    return True

# ----------------------------------------------------------------------------

class CutoutCollector:
    """Stand-in for a sketch: drawRect adds each cutout here as one closed loop, so
    overlapping cutouts can be merged before they go into the real sketch."""

    def __init__(self):
        self.loops = []
        self.construction = []  # (index of the loop it belongs to, geometry)

    def addGeometry(self, geoms, construction=False):
        if construction:
            self.construction.append((len(self.loops) - 1, list(geoms)))
        else:
            self.loops.append(list(geoms))
        return list(range(len(geoms)))

    def addConstraint(self, constraints):
        pass  # addCutouts adds the Block constraints

# ----------------------------------------------------------------------------

def _edgeToGeometry(edge):
    """Turn a line or arc edge of a merged outline back into sketch geometry."""
    if isinstance(edge.Curve, Part.Line):
        return Part.LineSegment(edge.Vertexes[0].Point, edge.Vertexes[-1].Point)
    p1 = edge.valueAt(edge.FirstParameter)
    pm = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    p2 = edge.valueAt(edge.LastParameter)
    arc = Part.ArcOfCircle(p1, pm, p2)
    if arc.Axis.z < 0:  # sketch arcs run counterclockwise
        arc = Part.ArcOfCircle(p2, pm, p1)
    return arc

# ----------------------------------------------------------------------------

def addCutouts(sketch, loops, radius=0, construction=()):
    """Add the cutout loops to the sketch, each item frozen with a Block constraint.
    Loops that overlap or touch, such as the alternative keys of a multi-layout plate
    (a split Backspace on top of a 2u Backspace), are merged into one outline. If
    `radius` is not 0, the inside corners of a merged outline are rounded to it.
    `construction` holds (loop index, geometry) pairs from CutoutCollector; they are added as
    construction geometry, but only for loops that were not merged."""

    faces = [Part.Face(Part.Wire(Part.__sortEdges__([g.toShape() for g in loop]))) for loop in loops]

    # group the loops that overlap or touch
    # ponytail: pair scan is O(n^2) with a bounding-box filter; fine for keyboards, use a spatial grid if layouts get much larger
    parent = list(range(len(faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(faces)):
        for j in range(i + 1, len(faces)):
            if faces[i].BoundBox.intersect(faces[j].BoundBox) and faces[i].distToShape(faces[j])[0] < 1e-7:
                parent[find(i)] = find(j)

    groups = {}
    for i in range(len(faces)):
        groups.setdefault(find(i), []).append(i)

    geoms = []
    for members in groups.values():
        if len(members) == 1:
            geoms += loops[members[0]]
        else:
            merged = faces[members[0]].fuse([faces[m] for m in members[1:]]).removeSplitter()
            if radius > 0:
                # round the inside corners: grow by radius, then shrink back (a 2D closing);
                # the outside corners keep their shape
                merged = Part.Compound(merged.Faces).makeOffset2D(radius, join=0).makeOffset2D(-radius, join=0)
            geoms += [_edgeToGeometry(e) for e in merged.Edges]

    single = {members[0] for members in groups.values() if len(members) == 1}
    construction_geoms = [g for i, gs in construction if i in single for g in gs]

    ids = list(sketch.addGeometry(geoms, False))
    if construction_geoms:
        ids += list(sketch.addGeometry(construction_geoms, True))
    sketch.addConstraint([Sketcher.Constraint('Block', i) for i in ids])
