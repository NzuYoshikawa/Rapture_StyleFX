# -*- coding: utf-8 -*-
"""Viewport toggle for the StyleFX looks (ported from rapture_aov.stylefx, cc-SF 2026-06-23).

Mechanism = one unbound PostProcessVolume (PPV_RaptureStyleFX) whose blendable is a StyleFX Material
Instance, or empty for the normal view. The active mode is remembered on the PPV's actor tag, so each
menu entry is an on/off toggle. Material resolution: this plugin's content first, then /Game/StyleFX
(a project that still has its own copy).
"""
import unreal

PPV_LABEL = "PPV_RaptureStyleFX"
_TAG_PREFIX = "sfxmode:"
PLUGIN_DIR = "/Rapture_StyleFX"

_MI = {"npr": "MI_RaptureStyleFX", "watercolor": "MI_RaptureStyleFX_WC", "lineart": "MI_RaptureStyleFX_Lineart"}
_ROOTS = [PLUGIN_DIR, "/Game/StyleFX"]

_eal = unreal.EditorAssetLibrary
_mel = unreal.MaterialEditingLibrary


def _resolve(mode):
    name = _MI.get(mode)
    for root in _ROOTS:
        p = "%s/%s" % (root, name)
        if name and _eal.does_asset_exist(p):
            return _eal.load_asset(p)
    return None


def _eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _find_ppv():
    for a in _eas().get_all_level_actors():
        if a.get_actor_label() == PPV_LABEL:
            return a
    return None


def _ensure_ppv():
    p = _find_ppv()
    if p is None:
        p = _eas().spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
        p.set_actor_label(PPV_LABEL)
        p.set_editor_property("unbound", True)
        p.set_editor_property("priority", 1000.0)
    return p


def _get_mode(ppv):
    for t in ppv.tags:
        s = str(t)
        if s.startswith(_TAG_PREFIX):
            return s[len(_TAG_PREFIX):]
    return None


def _set_mode_tag(ppv, mode):
    tags = [t for t in ppv.tags if not str(t).startswith(_TAG_PREFIX)]
    if mode:
        tags.append(unreal.Name(_TAG_PREFIX + mode))
    ppv.tags = tags


def _set_blendable(ppv, mi):
    s = ppv.get_editor_property("settings")
    wbs = s.get_editor_property("weighted_blendables")
    wbs.set_editor_property("array", [] if mi is None else [unreal.WeightedBlendable(1.0, mi)])
    s.set_editor_property("weighted_blendables", wbs)
    ppv.set_editor_property("settings", s)


def clear():
    """Normal view: drop the StyleFX blendable (the PPV is kept, empty)."""
    p = _find_ppv()
    if p:
        _set_blendable(p, None)
        _set_mode_tag(p, None)
    return "[StyleFX] normal view"


def toggle(mode):
    """Toggle a StyleFX mode on/off in the viewport. mode in {'npr', 'watercolor', 'lineart'}."""
    mi = _resolve(mode)
    if mi is None:
        return ("[StyleFX] Material Instance for '%s' not found. Run rapture_stylefx.package.bundle() in a project "
                "that has /Game/StyleFX, or copy the plugin's Content." % mode)
    ppv = _ensure_ppv()
    if _get_mode(ppv) == mode:
        _set_blendable(ppv, None)
        _set_mode_tag(ppv, None)
        return "[StyleFX] %s OFF (normal view)" % mode
    _set_blendable(ppv, mi)
    _set_mode_tag(ppv, mode)
    return "[StyleFX] %s ON  (toggle again for normal view)" % mode


def status():
    p = _find_ppv()
    mode = _get_mode(p) if p else None
    avail = {m: bool(_resolve(m)) for m in _MI}
    msg = "[StyleFX] active=%s  available=%s" % (mode, avail)
    unreal.log(msg)
    return msg


# ---- Material Instance parameters (the knobs: OutlineWidth, HatchLineWidth, ...)
def list_params(mode="npr"):
    mi = _resolve(mode)
    if mi is None:
        return {}
    parent = mi.get_editor_property("parent")
    out = {}
    for n in _mel.get_scalar_parameter_names(parent):
        out[str(n)] = _mel.get_material_instance_scalar_parameter_value(mi, n)
    return out


def get_param(mode, name):
    return list_params(mode).get(name)


def set_param(mode, name, value):
    """Set a scalar parameter of the mode's Material Instance and save it."""
    mi = _resolve(mode)
    if mi is None:
        return "[StyleFX] no MI for '%s'" % mode
    _mel.set_material_instance_scalar_parameter_value(mi, name, float(value))   # returns None in 5.7: read it back
    now = list_params(mode).get(name)
    ok = now is not None and abs(now - float(value)) < 1e-4
    if ok:
        _eal.save_loaded_asset(mi)
    return "[StyleFX] %s.%s = %s (%s)" % (mode, name, value, "ok" if ok else "FAILED: no such scalar parameter (list_params)")
