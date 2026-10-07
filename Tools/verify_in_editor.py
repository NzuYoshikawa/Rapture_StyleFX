# -*- coding: utf-8 -*-
"""Run inside the editor of a project that has /Game/StyleFX and the RaptureStyleFX plugin:
bundles the materials into the plugin, builds a tiny test level, toggles npr / normal / watercolor / lineart through
the plugin's own API and captures each look with a SceneCapture2D that relies on the toggle's level PPV only.
Waits between steps so the shaders can compile (a material that has never been drawn is the default material at first).
Output: <project>/Saved/verify/sfx_<mode>.png ; log lines start with [sfxverify]."""
import os, time, unreal

log = lambda m: unreal.log("[sfxverify] " + m)
OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "verify")
os.makedirs(OUT, exist_ok=True)
eal = unreal.EditorAssetLibrary
import rapture_stylefx as sfx
import rapture_stylefx.package as pk

if not eal.does_asset_exist('/Rapture_StyleFX/M_RaptureStyleFX'):
    log(pk.bundle())          # first time only (never overwrites tuned MIs)
for n in ("M_RaptureStyleFX", "M_RaptureStyleFX_WC", "MI_RaptureStyleFX", "MI_RaptureStyleFX_WC", "MI_RaptureStyleFX_Lineart",
          "Textures/T_WC_Noise", "Textures/T_WC_Paper"):
    log("asset /Rapture_StyleFX/%s exists=%s" % (n, eal.does_asset_exist("/Rapture_StyleFX/" + n)))
log("params npr: %s" % sorted(sfx.list_params("npr").keys()))
log(sfx.set_param("npr", "OutlineWidth", sfx.get_param("npr", "OutlineWidth") or 1.0))

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
log("new_level -> %s" % les.new_level("/Game/SFX_TestLevel"))
V = unreal.Vector


def mesh(path, loc, scale, label):
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc)
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(eal.load_asset(path))
    a.set_actor_scale3d(scale)
    return a


mesh("/Engine/BasicShapes/Plane", V(0, 0, 0), V(30, 30, 1), "SFX_Floor")
mesh("/Engine/BasicShapes/Cube", V(0, 0, 50), V(1, 1, 1), "SFX_Cube")
mesh("/Engine/BasicShapes/Sphere", V(150, -80, 50), V(1, 1, 1), "SFX_Sphere")
mesh("/Engine/BasicShapes/Cube", V(400, 150, 150), V(1.5, 1.5, 3), "SFX_Pillar")
sun = eas.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 500), unreal.Rotator(0, -45, 40))
sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 8.0)
eas.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 400))

world = ues.get_editor_world()
STEPS = [("npr", 30.0), ("normal", 4.0), ("watercolor", 40.0), ("lineart", 30.0)]
S = {"i": -1, "t": 0.0, "phase": "start", "h": None, "caps": 0}


def capture(mode):
    for a in list(eas.get_all_level_actors()):
        if a.get_actor_label() == "SC_SFX_Verify":
            eas.destroy_actor(a)
    cam_loc = V(-420, -520, 260)
    look = unreal.MathLibrary.find_look_at_rotation(cam_loc, V(120, 20, 80))
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, cam_loc, look)
    cap.set_actor_label("SC_SFX_Verify")
    comp = cap.capture_component2d
    comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property("fov_angle", 70.0)
    rt = unreal.RenderingLibrary.create_render_target2d(world, 960, 540, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    comp.set_editor_property("texture_target", rt)
    comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, "sfx_%s.png" % mode)
    S["caps"] += 1
    log("captured %s" % mode)


def tick(dt):
    S["t"] += dt
    if S["phase"] == "start":
        S["phase"], S["t"] = "advance", 0
        return
    if S["phase"] == "advance":
        S["i"] += 1
        if S["i"] >= len(STEPS):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("DONE captures=%d" % S["caps"])
            unreal.SystemLibrary.quit_editor()
            return
        mode, wait = STEPS[S["i"]]
        log("%s -> %s" % (mode, sfx.clear() if mode == "normal" else sfx.toggle(mode)))
        log(sfx.status())
        S["phase"], S["t"], S["wait"] = "wait", 0.0, wait
        return
    if S["phase"] == "wait" and S["t"] >= S["wait"]:
        mode = STEPS[S["i"]][0]
        capture(mode)
        S["phase"], S["t"] = "second", 0.0
        return
    if S["phase"] == "second" and S["t"] >= 3.0:
        capture(STEPS[S["i"]][0])           # the first draw may still be the default material; the second one counts
        S["phase"] = "advance"


S["h"] = unreal.register_slate_post_tick_callback(tick)
