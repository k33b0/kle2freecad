# -*- coding: utf-8 -*-
"""Stabilizer cutouts"""

import math

import FreeCAD
import Part
import Sketcher


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
    elif z >= 4.5:  # JIS / JLA-450
        o_o = 35.0
    elif z >= 4.25:  # JIS / JLA-425
        o_o = 30.0
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
    drawStabPad(sketch, x1, y1, 7, 15, flt_r, k, kerf=kerf)
    drawStabPad(sketch, x2, y2, 7, 15, flt_r, k, kerf=kerf)
    return True

# ----------------------------------------------------------------------------

def drawStabPad(sketch, x, y, w, h, r, k, shift=3.0, kerf=0):
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
        two top arcs, bottom line and two bottom arcs

    kerf: the beam burns kerf/2 off each side, so the pad is drawn that much smaller.
    The shift stays the same."""

    w, h, r = w - kerf, h - kerf, max(r - kerf / 2, 0)
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

    # clockwise, like drawRect: top, right side down, bottom, left side up, each corner after its side
    # (sketch arcs always run counterclockwise; only their place in the order follows the outline)
    corner = (lambda acx, acy, start: [arc(acx, acy, start)]) if r > 0 else (lambda *_: [])
    real = (
        [line(-a + r, t, a - r, t)]                # top, inside the opposite pad
        + corner(a - r, t - r, 0)                  # top right
        + [line(a, t - r, a, -t + shift + r),      # right side, common to both pads
           line(a, -t + shift + r, a, -t + r)]     # right side, this pad only
        + corner(a - r, -t + r, 1.5 * math.pi)     # bottom right
        + [line(a - r, -t, -a + r, -t)]            # bottom
        + corner(-a + r, -t + r, math.pi)          # bottom left
        + [line(-a, -t + r, -a, -t + shift + r),   # left side, this pad only
           line(-a, -t + shift + r, -a, t - r)]    # left side, common to both pads
        + corner(-a + r, t - r, 0.5 * math.pi)     # top left
    )
    construction = (
        [line(-a + r, t + shift, a - r, t + shift)]   # opposite pad top
        + corner(a - r, t + shift - r, 0)             # opposite pad top right
        + [line(a, t + shift - r, a, t - r)]          # right side extension
        + corner(a - r, -t + shift + r, 1.5 * math.pi)  # opposite pad bottom right, a reference only
        + [line(a - r, -t + shift, -a + r, -t + shift)]  # opposite pad bottom, a reference only
        + corner(-a + r, -t + shift + r, math.pi)     # opposite pad bottom left, a reference only
        + [line(-a, t - r, -a, t + shift - r)]        # left side extension
        + corner(-a + r, t + shift - r, 0.5 * math.pi)  # opposite pad top left
    )

    ids = list(sketch.addGeometry(real, False)) + list(sketch.addGeometry(construction, True))
    sketch.addConstraint([Sketcher.Constraint('Block', i) for i in ids])
    return True
