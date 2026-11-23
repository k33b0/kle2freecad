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
        import traceback

        from PySide import QtCore, QtWidgets

        from .dialog import KLEPromptDialog
        from .kle_json_cleaner import countKeys
        from .ks_draw import CutoutCollector, addCutouts, drawCherryKey, drawCherryStab, findKeyCenters

        dlg = KLEPromptDialog(Gui.getMainWindow())
        if not dlg.exec():
            return  # Cancel

        adv_w = dlg.adv_w.value()
        adv_h = dlg.adv_h.value()
        adv_k = dlg.adv_k.value() # Kerf
        flt_r = dlg.fillet_rad.value() # Switch fillet radius
        flt_c = dlg.fillet_cut.value() # Stab fillet radius
        kle_parsed = findKeyCenters(dlg.kle_parsed, adv_w, adv_h)

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
        # loop here
        progress = QtWidgets.QProgressDialog("Drawing key cutouts...", None, 0, countKeys(kle_parsed), Gui.getMainWindow())
        progress.setWindowTitle("KLE Sketch Generator")
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.forceShow()

        try:
            cutouts = CutoutCollector()  # collect first, so overlapping cutouts can be merged
            step = 0
            for row in kle_parsed or []:
                if not isinstance(row, list):
                    continue
                for item in row:
                    if isinstance(item, dict):
                        cx = item.get("cx",0)
                        cy = item.get("cy",0)
                        drawCherryKey(cutouts, cx, cy, flt_r, adv_k)
                        w = item.get("w",1)
                        h = item.get("h",1)
                        if w >= 2 or h >= 2:
                            drawCherryStab(cutouts, cx, cy, w, h, item.get("r",0), flt_c, adv_k)
                        step += 1
                    progress.setValue(step)
                    QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
            addCutouts(sketch, cutouts.loops, max(flt_r, flt_c), cutouts.construction)  # inside corners: the larger radius, so every part fits
        except Exception as e:
            print(str(e))
            traceback.print_exc()

        progress.close()
        # commit and recompute
        doc.commitTransaction()
        doc.recompute()

        if not in_edit:
            Gui.ActiveDocument.setEdit(sketch.Name)


Gui.addCommand("KLE2FreeCAD", TestCommand())


class _AddToSketchToolbar:
    def modifyToolBars(self):
        return [{"append": "KLE2FreeCAD", "toolBar": "Sketcher"}]


Gui.addWorkbenchManipulator(_AddToSketchToolbar())


from .ks_prefs import KSprefsPage  # noqa: E402

Gui.addIconPath(ICONS)  # for the preferences page icon, preferences-kle_plate_generator.svg
Gui.addPreferencePage(KSprefsPage, "KLE Plate Generator")


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
