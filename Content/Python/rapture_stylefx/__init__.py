# -*- coding: utf-8 -*-
"""Rapture_StyleFX: post-process stylization (outline / hatching / ink / world-locked watercolour).

    import rapture_stylefx as sfx
    sfx.toggle('npr')            # viewport: stylized / 'watercolor' / 'lineart'; same mode again = normal view
    sfx.clear()                  # normal view
    sfx.status()
    sfx.set_param('npr', 'OutlineWidth', 1.5)      # a Material Instance parameter (see list_params)
    sfx.list_params('npr')
    sfx.package.bundle()         # once, in a project that has /Game/StyleFX: copy the materials into this plugin
"""
from .toggle import toggle, clear, status, set_param, get_param, list_params  # noqa: F401
from . import package  # noqa: F401
