import os

import FreeCAD as App
import FreeCADGui as Gui

ICONS = os.path.join(os.path.dirname(__file__), "resources", "icons")


class TestCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONS, "kle2sketch.svg"),
            "MenuText": "Plate cutouts",
            "ToolTip": "Use a KLE json to create a key cutout sketch",
            "CmdType": "ForEdit",  # stay active while a sketch is open, so it can append to it
        }

    def Activated(self):
        from .mx_cutouts import draw_centered_square

        # 2. a sketch is open: append to it
        vp = Gui.ActiveDocument and Gui.ActiveDocument.getInEdit()
        sketch = vp.Object if vp and vp.Object.TypeId == "Sketcher::SketchObject" else None
        in_edit = sketch is not None

        # 1. one flat face of a Body is selected: new sketch in that Body, attached to the face
        body_face = None
        if not in_edit:
            faces = [
                (sel.Object, name)
                for sel in Gui.Selection.getSelectionEx()
                for name in sel.SubElementNames
                if name.startswith("Face")
            ]
            if len(faces) == 1:
                obj, name = faces[0]
                body = obj.getParentGeoFeatureGroup()
                if body and body.isDerivedFrom("PartDesign::Body") and obj.getSubObject(name).findPlane() is not None:
                    body_face = (body, obj, name)

        if in_edit:
            doc = sketch.Document
        elif body_face:
            doc = body_face[1].Document
        else:
            doc = App.ActiveDocument or App.newDocument()

        doc.openTransaction("Draw square")
        if body_face:
            body, obj, name = body_face
            sketch = body.newObject("Sketcher::SketchObject", "Sketch")
            sketch.AttachmentSupport = [(obj, name)]
            sketch.MapMode = "FlatFace"
        elif not in_edit:
            # 3. anything else: a new sketch, as before
            sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
        draw_centered_square(sketch, 0, 0, 14, 0.5, True) # This creates the K0W parameter at 14mm, and the K0R1 radius at 0.5mm.
        draw_centered_square(sketch, 0, 0, 19.05, 0, True) # This creates the K1W parameter ar 19.05mm
        doc.commitTransaction()
        doc.recompute()

        if not in_edit:
            Gui.ActiveDocument.setEdit(sketch.Name)


Gui.addCommand("KLE2FreeCAD", TestCommand())


class _AddToSketchToolbar:
    def modifyToolBars(self):
        return [{"append": "KLE2FreeCAD", "toolBar": "Sketcher"}]


Gui.addWorkbenchManipulator(_AddToSketchToolbar())


# class KLE2FreeCADWorkbench(Gui.Workbench):
#     MenuText = "KLE Plate Generator"
#     ToolTip = "Convert KLE output to a sketch"
#     Icon = os.path.join(ICONS, "kle2sketch.svg")

#     def Initialize(self):
#         Gui.addIconPath(ICONS)
#         self.appendToolbar("KLE Plate Generator", ["KLE2FreeCAD"])
#         self.appendMenu("KLE Plate Generator", ["KLE2FreeCAD"])

#     def GetClassName(self):
#         return "Gui::PythonWorkbench"


# Gui.addWorkbench(KLE2FreeCADWorkbench())
