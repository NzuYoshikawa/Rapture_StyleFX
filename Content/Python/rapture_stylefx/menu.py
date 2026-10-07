# -*- coding: utf-8 -*-
"""Tools > Rapture_StyleFX (ToolMenus, 100% Python). Idempotent; called from init_unreal.py."""
import unreal

_TOOLS_MENU = "LevelEditor.MainMenu.Tools"
_SUB_NAME = "Rapture_StyleFX"
_SUB_FULL = _TOOLS_MENU + "." + _SUB_NAME
_SECTION = "main"

_ENTRIES = [
    ("sfx_npr", "Toggle NPR (outline / hatching / ink)", "import rapture_stylefx as s; print(s.toggle('npr'))"),
    ("sfx_wc", "Toggle Watercolor (world-locked pigment)", "import rapture_stylefx as s; print(s.toggle('watercolor'))"),
    ("sfx_line", "Toggle Lineart only", "import rapture_stylefx as s; print(s.toggle('lineart'))"),
    ("sfx_off", "Normal view (clear)", "import rapture_stylefx as s; print(s.clear())"),
    ("sfx_status", "Status", "import rapture_stylefx as s; print(s.status())"),
    ("sfx_bundle", "Bundle materials from /Game/StyleFX (once, dev project)",
     "import rapture_stylefx.package as p; p.bundle()"),
]


def _entry(name, label, command):
    e = unreal.ToolMenuEntry(name=unreal.Name(name), type=unreal.MultiBlockType.MENU_ENTRY)
    e.set_label(label)
    e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, unreal.Name(""), command)
    return e


def unregister():
    menus = unreal.ToolMenus.get()
    if menus:
        try:
            menus.remove_menu(unreal.Name(_SUB_FULL))
        except Exception:
            pass


def register():
    menus = unreal.ToolMenus.get()
    if not menus:
        unreal.log_warning("[Rapture_StyleFX] ToolMenus subsystem not available")
        return False
    tools = menus.find_menu(unreal.Name(_TOOLS_MENU))
    if not tools:
        unreal.log_warning("[Rapture_StyleFX] '%s' not found - menu not registered" % _TOOLS_MENU)
        return False
    unregister()
    sub = tools.add_sub_menu(tools.get_name(), unreal.Name(""), unreal.Name(_SUB_NAME), "Rapture_StyleFX",
                             "Post-process stylization: outline, hatching, ink, watercolour")
    if not sub:
        unreal.log_warning("[Rapture_StyleFX] add_sub_menu returned None - menu not registered")
        return False
    sub.add_section(unreal.Name(_SECTION), "StyleFX viewport toggle")
    for name, label, cmd in _ENTRIES:
        sub.add_menu_entry(unreal.Name(_SECTION), _entry(name, label, cmd))
    menus.refresh_all_widgets()
    unreal.log("[Rapture_StyleFX] menu registered: Tools > Rapture_StyleFX (%d entries)" % len(_ENTRIES))
    return True
