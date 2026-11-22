import os

import FreeCAD as App
import FreeCADGui as Gui

ICONS = os.path.join(os.path.dirname(__file__), "resources", "icons")


class TestCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONS, "kle2sketch.svg"),
            "MenuText": "Test",
            "ToolTip": "Draw a 14 mm square in the open sketch, or in a new sketch",
        }

    def Activated(self):
        from .draw import draw_centered_square

        vp = Gui.ActiveDocument and Gui.ActiveDocument.getInEdit()
        sketch = vp.Object if vp and vp.Object.TypeId == "Sketcher::SketchObject" else None
        in_edit = sketch is not None
        doc = sketch.Document if in_edit else (App.ActiveDocument or App.newDocument())

        doc.openTransaction("Draw square")
        if not in_edit:
            sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
        draw_centered_square(sketch, 0, 0, 14, 0.5, True)
        draw_centered_square(sketch, 16, 16, "K0W", "K0R1", False)
        doc.commitTransaction()
        doc.recompute()

        if not in_edit:
            Gui.ActiveDocument.setEdit(sketch.Name)


Gui.addCommand("KLE2FreeCAD_Test", TestCommand())


class KLE2FreeCADWorkbench(Gui.Workbench):
    MenuText = "KLE Plate Generator"
    ToolTip = "Convert KLE output to a sketch"
    Icon = os.path.join(ICONS, "kle2sketch.svg")

    def Initialize(self):
        Gui.addIconPath(ICONS)
        self.appendToolbar("KLE Plate Generator", ["KLE2FreeCAD_Test"])
        self.appendMenu("KLE Plate Generator", ["KLE2FreeCAD_Test"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(KLE2FreeCADWorkbench())
