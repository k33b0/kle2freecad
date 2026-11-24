# -*- coding: utf-8 -*-

import FreeCAD

_PREF_PATH = "User parameter:BaseApp/Preferences/Mod/kle2sketch"
_PREF_KEY = "LayoutJSON"


def _pref_group():
    return FreeCAD.ParamGet(_PREF_PATH)


def get_saved_layout(default=""):
    """Return persisted layout text or a fallback."""
    saved = _pref_group().GetString(_PREF_KEY)
    return saved if saved else default


def set_saved_layout(text: str) -> None:
    """Persist layout text."""
    _pref_group().SetString(_PREF_KEY, text or "")


def get_dxf_dir():
    """Return the folder of the last imported DXF, or an empty string."""
    return _pref_group().GetString("LastDxfDir")


def set_dxf_dir(path: str) -> None:
    """Remember the folder of the last imported DXF."""
    _pref_group().SetString("LastDxfDir", path)
