# -*- coding: utf-8 -*-
"""Read the cutouts of a plate DXF, as made by plate generators such as Yet Another Keyboard Builder"""

from collections import Counter

import FreeCAD
import Import
import Part

from .ks_draw import _edgeToGeometry

TOL = 1e-6  # end points closer than this are one point; generator files have gaps of up to 1.6e-7 mm


def _snapper(tol):
    """Return a function that maps each point to the first earlier point closer than `tol`."""
    grid = {}

    def snap(p):
        i, j = round(p.x / tol), round(p.y / tol)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                q = grid.get((i + di, j + dj))
                if q is not None and (p - q).Length < tol:
                    return q
        return grid.setdefault((i, j), p)

    return snap


def readDxfLoops(path):
    """Read a plate DXF and return edgesToLoops() of its edges."""

    active = FreeCAD.ActiveDocument
    tmp = FreeCAD.newDocument("kle2freecad_dxf", hidden=True, temp=True)
    try:
        FreeCAD.setActiveDocument(tmp.Name)  # the importer adds its layer groups to the active document
        Import.readDXF(path, tmp.Name, True)
        tmp.recompute()
        edges = [e for o in tmp.Objects if hasattr(o, "Shape") for e in o.Shape.Edges]
    finally:
        FreeCAD.closeDocument(tmp.Name)
        if active:
            FreeCAD.setActiveDocument(active.Name)
    return edgesToLoops(edges)


def edgesToLoops(edges):
    """Return (loops, skipped). Each loop is the sketch geometry of one closed cutout outline.
    The plate frame (the outline that contains all others) is dropped, and the cutouts are
    centered on it. `skipped` is the number of edge chains that do not close."""

    groups = Part.sortEdges(edges, TOL)
    boxes = [Part.Compound(g).BoundBox for g in groups]
    frame = max(range(len(groups)), key=lambda i: boxes[i].XLength * boxes[i].YLength, default=None)
    if frame is not None and all(boxes[frame].isInside(b) for i, b in enumerate(boxes) if i != frame):
        center = boxes[frame].Center
    else:  # no frame: center on all cutouts
        frame = None
        center = Part.Compound(edges).BoundBox.Center

    shift = FreeCAD.Vector(-center.x, -center.y, 0)
    snap = _snapper(TOL)
    loops, skipped = [], 0
    for i, group in enumerate(groups):
        if i == frame:
            continue
        geoms = [_edgeToGeometry(e.translated(shift), snap) for e in group]
        # closed: every end point is shared by an even number of edges (circles have no ends)
        ends = Counter(tuple(snap(p)) for g in geoms if not isinstance(g, Part.Circle) for p in (g.StartPoint, g.EndPoint))
        if all(n % 2 == 0 for n in ends.values()):
            loops.append(geoms)
        else:
            skipped += 1
    return loops, skipped
