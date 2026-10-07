# -*- coding: utf-8 -*-
"""RaptureStyleFX plugin startup (auto-run by UE PythonScriptPlugin). Registers Tools > Rapture_StyleFX.
Guarded: a menu hiccup must never block the editor from starting."""
import unreal

unreal.log("[Rapture_StyleFX] plugin Python init - package rapture_stylefx available")
try:
    import rapture_stylefx.menu as _menu
    _menu.register()
except Exception as _e:
    unreal.log_warning("[Rapture_StyleFX] menu registration at startup failed: %r" % _e)
