import os

import FreeCAD as App
import FreeCADGui as Gui

ICONS = os.path.join(os.path.dirname(__file__), "resources", "icons")


def _findTarget():
    """Return where new cutouts go: (document, open sketch or None, (body, object, face name) or None).
    2. a sketch is open: append to it
    1. one flat face of a Body is selected: a new sketch in that Body, attached to the face
    3. anything else: a new sketch"""

    vp = Gui.ActiveDocument and Gui.ActiveDocument.getInEdit()
    sketch = vp.Object if vp and vp.Object.TypeId == "Sketcher::SketchObject" else None
    if sketch:
        return sketch.Document, sketch, None

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
            return obj.Document, None, (body, obj, name)

    return App.ActiveDocument or App.newDocument(), None, None


def _newSketch(doc, body_face):
    """Make the new sketch for _findTarget scenarios 1 and 3."""
    if body_face:
        body, obj, name = body_face
        sketch = body.newObject("Sketcher::SketchObject", "Sketch")
        sketch.AttachmentSupport = [(obj, name)]
        sketch.MapMode = "FlatFace"
        return sketch
    return doc.addObject("Sketcher::SketchObject", "Sketch")


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
        from .ks_draw import CutoutCollector, addCutouts, findKeyCenters
        from .stb_chrry_mx import drawCherryStab
        from .swt_chrry_mx import drawCherryKey

        dlg = KLEPromptDialog(Gui.getMainWindow())
        if not dlg.exec():
            return  # Cancel

        adv_w = dlg.adv_w.value()
        adv_h = dlg.adv_h.value()
        adv_k = dlg.adv_k.value() # Kerf
        flt_r = dlg.fillet_rad.value() # Switch fillet radius
        flt_c = dlg.fillet_cut.value() # Stab fillet radius
        draw_key = dlg.cutout_type.currentText() != "None"
        draw_stab = dlg.cutout_stab.currentText() != "None"
        kle_parsed = findKeyCenters(dlg.kle_parsed, adv_w, adv_h)

        doc, sketch, body_face = _findTarget()
        in_edit = sketch is not None

        doc.openTransaction("Draw square")
        if not in_edit:
            sketch = _newSketch(doc, body_face)
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
                        if draw_key:
                            drawCherryKey(cutouts, cx, cy, flt_r, adv_k)
                        w = item.get("w",1)
                        h = item.get("h",1)
                        if draw_stab and (w >= 2 or h >= 2):
                            drawCherryStab(cutouts, cx, cy, w, h, item.get("r",0), flt_c, adv_k)
                        step += 1
                    progress.setValue(step)
                    QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
            addCutouts(sketch, cutouts.loops, max(flt_r, flt_c) + adv_k / 2, cutouts.construction)  # inside corners: the larger radius, so every part fits; + kerf/2, as the beam shrinks inside corners by that much
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


class DxfCommand:
    INSIDE_RADIUS = 0.5  # inside corners of merged cutouts; the dialog's default fillet radius

    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONS, "dxf2sketch.svg"),
            "MenuText": "Import plate DXF",
            "ToolTip": "Import the cutouts of a plate DXF into a sketch",
            "CmdType": "ForEdit",  # stay active while a sketch is open, so it can append to it
        }

    def Activated(self):
        import traceback

        from PySide import QtWidgets

        from .dxf_read import readDxfLoops
        from .ks_draw import addCutouts
        from .ks_prefs import get_dxf_dir, set_dxf_dir

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            Gui.getMainWindow(), "Import plate DXF", get_dxf_dir(), "DXF files (*.dxf)"
        )
        if not path:
            return  # Cancel
        set_dxf_dir(os.path.dirname(path))

        doc, sketch, body_face = _findTarget()
        in_edit = sketch is not None

        try:
            loops, skipped = readDxfLoops(path)
        except Exception as e:
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(Gui.getMainWindow(), "Import plate DXF", f"Cannot read {path}:\n{e}")
            return
        if skipped:
            App.Console.PrintWarning(f"Import plate DXF: skipped {skipped} edge chains that do not close\n")
        if not loops:
            QtWidgets.QMessageBox.warning(Gui.getMainWindow(), "Import plate DXF", f"No closed cutouts in {path}")
            return

        doc.openTransaction("Import plate DXF")
        try:
            if not in_edit:
                sketch = _newSketch(doc, body_face)
            addCutouts(sketch, loops, self.INSIDE_RADIUS)
        except Exception as e:
            doc.abortTransaction()
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(Gui.getMainWindow(), "Import plate DXF", str(e))
            return
        doc.commitTransaction()
        doc.recompute()

        if not in_edit:
            Gui.getDocument(doc.Name).setEdit(sketch.Name)


Gui.addCommand("DXF2FreeCAD", DxfCommand())


# class _AddToSketchToolbar:
#     def modifyToolBars(self):
#         return [{"append": "KLE2FreeCAD", "toolBar": "Sketcher"}]


# Gui.addWorkbenchManipulator(_AddToSketchToolbar())


class KLE2FreeCADWorkbench(Gui.Workbench):
    MenuText = "KLE Plate Generator"
    ToolTip = "Convert KLE output to a sketch"
    Icon = os.path.join(ICONS, "kle2sketch.svg")

    def Initialize(self):
        Gui.addIconPath(ICONS)
        self.appendToolbar("KLE Plate Generator", ["KLE2FreeCAD", "DXF2FreeCAD"])
        self.appendMenu("KLE Plate Generator", ["KLE2FreeCAD", "DXF2FreeCAD"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(KLE2FreeCADWorkbench())
