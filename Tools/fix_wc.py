# -*- coding: utf-8 -*-
import unreal
log = lambda m: unreal.log("[sfxparams] " + m)
import rapture_stylefx.package as pk
log(pk.rebuild_watercolor())
log("DONE")
unreal.SystemLibrary.quit_editor()
