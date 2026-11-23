# -*- coding: utf-8 -*-
"""Switch cutouts"""

from .ks_draw import drawRect


def drawCherryKey(sketch, cx, cy, flt_r, kerf):
    """Draws a 14x14 plate cutout"""

    z = 14
    return drawRect(sketch, cx, cy, z, z, flt_r, kerf)
