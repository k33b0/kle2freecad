import math

import FreeCAD as App
import Part
import Sketcher

V = App.Vector


def draw_centered_square(sketch, x=0.0, y=0.0, size=14.0, radius=0.0, construction=True):
    """Draw a center point at (x, y) mm and a square with sides of `size` mm around it.
    If `size` is a string, it is the name of a constraint in the sketch: the side length
    becomes the expression .Constraints.<size>, so it follows that constraint.
    If `radius` is not 0, the corners are rounded with arcs of that radius in mm.
    `radius` can also be a constraint name, the same as `size`. The corner radii are
    named R1 (top-left), R2 (top-right), R3 (bottom-right), R4 (bottom-left), and R2-R4
    follow R1 through the expression .Constraints.K<n>R1.
    `construction` sets the lines and arcs as construction geometry.
    Returns (center point index, [top, right, bottom, left] line indices)."""
    expr = None
    if isinstance(size, str):
        expr = f".Constraints.{size}"
        size = sketch.getDatum(size).Value
    r_expr = None
    if isinstance(radius, str):
        r_expr = f".Constraints.{radius}"
        radius = sketch.getDatum(radius).Value
    h = size / 2
    r = radius
    center = sketch.addGeometry(Part.Point(V(x, y)), True)
    # each line stops r short of the corners, to leave room for the arcs
    lines = sketch.addGeometry([
        Part.LineSegment(V(x - h + r, y + h), V(x + h - r, y + h)),  # top, left to right
        Part.LineSegment(V(x + h, y + h - r), V(x + h, y - h + r)),  # right, top to bottom
        Part.LineSegment(V(x + h - r, y - h), V(x - h + r, y - h)),  # bottom, right to left
        Part.LineSegment(V(x - h, y - h + r), V(x - h, y + h - r)),  # left, bottom to top
    ], construction)
    top, right, bottom, left = lines

    if r:
        def quarter_arc(cx, cy, start_angle):  # counterclockwise
            return Part.ArcOfCircle(Part.Circle(V(cx, cy), V(0, 0, 1), r), start_angle, start_angle + math.pi / 2)

        tr, br, bl, tl = sketch.addGeometry([
            quarter_arc(x + h - r, y + h - r, 0),
            quarter_arc(x + h - r, y - h + r, 1.5 * math.pi),
            quarter_arc(x - h + r, y - h + r, math.pi),
            quarter_arc(x - h + r, y + h - r, 0.5 * math.pi),
        ], construction)
        corners = {
            # endpoint-to-endpoint tangency, which also makes the ends meet
            "TR1": Sketcher.Constraint("Tangent", top, 2, tr, 2),
            "TR2": Sketcher.Constraint("Tangent", tr, 1, right, 1),
            "BR1": Sketcher.Constraint("Tangent", right, 2, br, 2),
            "BR2": Sketcher.Constraint("Tangent", br, 1, bottom, 1),
            "BL1": Sketcher.Constraint("Tangent", bottom, 2, bl, 2),
            "BL2": Sketcher.Constraint("Tangent", bl, 1, left, 1),
            "TL1": Sketcher.Constraint("Tangent", left, 2, tl, 2),
            "TL2": Sketcher.Constraint("Tangent", tl, 1, top, 1),
            "R1": Sketcher.Constraint("Radius", tl, r),
            "R2": Sketcher.Constraint("Radius", tr, r),
            "R3": Sketcher.Constraint("Radius", br, r),
            "R4": Sketcher.Constraint("Radius", bl, r),
        }
        # the lines are shorter than the square, so measure the width between the left and right sides
        width = Sketcher.Constraint("DistanceX", left, 1, right, 1, size)
    else:
        corners = {
            # each line's end meets the next line's start
            "TR": Sketcher.Constraint("Coincident", top, 2, right, 1),
            "BR": Sketcher.Constraint("Coincident", right, 2, bottom, 1),
            "BL": Sketcher.Constraint("Coincident", bottom, 2, left, 1),
            "TL": Sketcher.Constraint("Coincident", left, 2, top, 1),
        }
        width = Sketcher.Constraint("Distance", top, size)

    constraints = {
        "X": Sketcher.Constraint("Block", center),  # fixes the center point at (x, y)
        **corners,
        "TH": Sketcher.Constraint("Horizontal", top),
        "BH": Sketcher.Constraint("Horizontal", bottom),
        "RV": Sketcher.Constraint("Vertical", right),
        "LV": Sketcher.Constraint("Vertical", left),
        # top-left and bottom-right corners mirror each other through the center point
        "S": Sketcher.Constraint("Symmetric", top, 1, bottom, 1, center, 1),
        "W": width,
        "ES": Sketcher.Constraint("Equal", top, right),
    }

    # names must be unique in the sketch, so number each square: K0W, K1W, ...
    used = {c.Name for c in sketch.Constraints}
    n = 0
    while f"K{n}X" in used:
        n += 1
    for role, c in constraints.items():
        c.Name = f"K{n}{role}"
    sketch.addConstraint(list(constraints.values()))
    if expr:
        sketch.setExpression(f"Constraints.K{n}W", expr)
    if r_expr:
        sketch.setExpression(f"Constraints.K{n}R1", r_expr)
    if r:
        for i in (2, 3, 4):
            sketch.setExpression(f"Constraints.K{n}R{i}", f".Constraints.K{n}R1")
    return center, lines
