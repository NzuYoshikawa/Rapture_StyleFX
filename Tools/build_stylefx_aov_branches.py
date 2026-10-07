# -*- coding: utf-8 -*-
# Add StyleFX AOV render layers to MRG_S1_cc07_StyleFX (additive; existing
# char/bg/outline/... branches untouched). New branches:
#   stylefx  -> full-scene beauty with MI_RaptureStyleFX as a post-process material
#   lineart  -> same with MI_RaptureStyleFX_Lineart (LineartOnly=1)
# Mechanism mirrors the 'outline' branch: DeferredRenderPassNode.
# additional_post_process_materials. Wiring follows cc06 (add_labeled_edge +
# connected() verification).
import unreal

GRAPH = "/Game/MRG_S1_cc07_StyleFX"
MAT_DIR = "/Game/StyleFX"
BASE_MAT = "/Game/StyleFX/M_RaptureStyleFX"
MI_STYLE = "/Game/StyleFX/MI_RaptureStyleFX"
MI_LINE = "/Game/StyleFX/MI_RaptureStyleFX_Lineart"
NONE = unreal.Name()
LOG = []


def log(s):
    LOG.append(str(s))


mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

# 1) lineart MI (LineartOnly=1)
if not eal.does_asset_exist(MI_LINE):
    mi = tools.create_asset("MI_RaptureStyleFX_Lineart", MAT_DIR,
                            unreal.MaterialInstanceConstant,
                            unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, eal.load_asset(BASE_MAT))
else:
    mi = eal.load_asset(MI_LINE)
mel.set_material_instance_scalar_parameter_value(mi, "LineartOnly", 1.0)
eal.save_asset(MI_LINE)
log("lineart MI ready")

cfg = eal.load_asset(GRAPH)
existing = [str(b) for b in cfg.get_branch_names()]
log("branches before: %r" % existing)

inode = cfg.get_input_node()
onode = cfg.get_output_node()


def connected(a, b):
    for pin in a.get_output_pins():
        for c in pin.get_all_connected_pins():
            if c.get_editor_property("node").get_name() == b.get_name():
                return True
    return False


def edge(a, la, b, lb, desc):
    cfg.add_labeled_edge(a, la, b, lb)
    log("  [%s] %s" % ("ok" if connected(a, b) else "FAIL", desc))


def make_pp(mat, name):
    p = unreal.MoviePipelinePostProcessPass()
    p.set_editor_property("material", mat)
    p.set_editor_property("name", name)
    try:
        p.set_editor_property("enabled", True)
    except Exception:
        pass
    return p


def add_branch(name, mat_path, y):
    if name in existing:
        log("branch %s already exists, skip" % name)
        return
    cfg.add_input(name)
    cfg.add_output(name)
    rl = cfg.create_node_by_class(unreal.MovieGraphRenderLayerNode)
    rl.set_editor_property("layer_name", name)
    rl.set_editor_property("override_layer_name", True)
    drp = cfg.create_node_by_class(unreal.MovieGraphDeferredRenderPassNode)
    # StyleFX is After-Tonemapping -> keep tonemapping ON
    try:
        drp.set_editor_property("disable_tone_curve", False)
        drp.set_editor_property("override_b_disable_tone_curve", True)
    except Exception as e:
        log("  tone curve set ERR %s" % e)
    # beauty OFF so the PP material's output IS the layer output (mirror outline)
    drp.set_editor_property("include_beauty_render_in_output", False)
    drp.set_editor_property("override_b_include_beauty_render_in_output", True)
    pp = make_pp(eal.load_asset(mat_path), name)
    if pp is not None:
        drp.set_editor_property("additional_post_process_materials", [pp])
        try:
            drp.set_editor_property("override_additional_post_process_materials", True)
        except Exception as e:
            log("  override app_materials ERR %s" % e)
    # wire Input.name -> drp -> rl -> Output.name
    edge(inode, unreal.Name(name), drp, NONE, "Input.%s->drp" % name)
    if not connected(drp, rl):
        edge(drp, NONE, rl, NONE, "drp->rl")
    edge(rl, NONE, onode, unreal.Name(name), "rl->Output.%s" % name)
    for i, n in enumerate((drp, rl)):
        n.set_node_pos_x(-200 + i * 300)
        n.set_node_pos_y(y)
    log("branch %s built" % name)


add_branch("stylefx", MI_STYLE, 1300)
add_branch("lineart", MI_LINE, 1500)

log("branches after: %r" % [str(b) for b in cfg.get_branch_names()])
log("save graph: %r" % eal.save_asset(GRAPH))
print("\n".join(LOG))
