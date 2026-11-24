# -*- coding: utf-8 -*-
"""Read the cutouts of a plate SVG, as made by plate generators such as Yet Another Keyboard Builder.

FreeCAD's own SVG importer (Draft importSVG) takes 10 to 30 seconds on a plate, so this reads
the SVG itself. It handles <path> (M, L, H, V, A, Z, absolute and relative) and <circle>.
ponytail: no transform attributes, no curves (C, Q), and arcs are circular (rx is used);
plate generators do not write those. Add them when a file needs them."""

import math
import re
import xml.etree.ElementTree as ET

import FreeCAD
import Part

from .dxf_read import edgesToLoops

_PX = 25.4 / 96  # mm per SVG user unit when the file gives no real unit
_UNITS = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72, "pc": 25.4 / 6, "px": _PX}
_TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _mmPerUnit(root):
    """Millimeters per SVG user unit, from the width and viewBox attributes."""
    m = re.fullmatch(r"\s*([\d.]+)\s*([a-z]*)\s*", root.get("width", ""))
    box = root.get("viewBox")
    if not (m and box):
        return _PX
    return float(m.group(1)) * _UNITS.get(m.group(2), _PX) / float(box.replace(",", " ").split()[2])


def _arcMid(p1, p2, r, large, sweep):
    """Return the middle point of an SVG arc from p1 to p2 (SVG endpoint to center conversion)."""
    (x1, y1), (x2, y2) = p1, p2
    hx, hy = (x1 - x2) / 2, (y1 - y2) / 2
    d2 = hx * hx + hy * hy
    r = max(r, math.sqrt(d2))  # a radius that is too small is scaled up, as in the SVG rules
    k = math.sqrt(max(r * r - d2, 0) / d2) * (1 if large != sweep else -1)
    cx, cy = k * hy + (x1 + x2) / 2, -k * hx + (y1 + y2) / 2
    a1 = math.atan2(y1 - cy, x1 - cx)
    da = math.atan2(y2 - cy, x2 - cx) - a1
    if sweep and da < 0:
        da += 2 * math.pi
    elif not sweep and da > 0:
        da -= 2 * math.pi
    return cx + r * math.cos(a1 + da / 2), cy + r * math.sin(a1 + da / 2)


def _pathEdges(d, P):
    """Return the edges of one SVG path. P maps an SVG point to a sketch vector."""
    toks = _TOKEN.findall(d)
    edges, i, cmd = [], 0, None
    cur = start = (0.0, 0.0)

    def num():
        nonlocal i
        i += 1
        return float(toks[i - 1])

    def line(a, b):
        if a != b:
            edges.append(Part.LineSegment(P(a), P(b)).toShape())

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
        elif cmd is None or cmd in "Zz":
            raise ValueError(f"unexpected number in path data: {toks[i]}")
        c = cmd.upper()
        ox, oy = cur if cmd.islower() else (0.0, 0.0)
        if c == "M":
            cur = start = (ox + num(), oy + num())
            cmd = "l" if cmd.islower() else "L"  # more pairs after M are lines
        elif c == "L":
            nxt = (ox + num(), oy + num())
            line(cur, nxt)
            cur = nxt
        elif c == "H":
            nxt = (ox + num(), cur[1])
            line(cur, nxt)
            cur = nxt
        elif c == "V":
            nxt = (cur[0], oy + num())
            line(cur, nxt)
            cur = nxt
        elif c == "A":
            rx, _ry, _rot, large, sweep = num(), num(), num(), num(), num()
            nxt = (ox + num(), oy + num())
            if nxt != cur:
                pm = _arcMid(cur, nxt, rx, int(large), int(sweep))
                edges.append(Part.Arc(P(cur), P(pm), P(nxt)).toShape())
            cur = nxt
        elif c == "Z":
            line(cur, start)
            cur = start
        else:
            raise ValueError(f"unsupported path command: {cmd}")
    return edges


def readSvgLoops(path):
    """Read a plate SVG and return edgesToLoops() of its edges."""
    root = ET.parse(path).getroot()
    s = _mmPerUnit(root)

    def P(p):  # SVG Y runs down, sketch Y runs up
        return FreeCAD.Vector(p[0] * s, -p[1] * s, 0)

    edges = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "path":
            edges += _pathEdges(el.get("d", ""), P)
        elif tag == "circle":
            c = P((float(el.get("cx", 0)), float(el.get("cy", 0))))
            edges.append(Part.makeCircle(float(el.get("r")) * s, c))
    return edgesToLoops(edges)
