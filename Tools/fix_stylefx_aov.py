# -*- coding: utf-8 -*-
# Fix stylefx/lineart branches so the PP-material output IS the layer output
# (mirror the working 'outline' branch): beauty OFF + named PP pass.
import unreal

GRAPH = "/Game/MRG_S1_cc07_StyleFX"
LOG = []


def log(s):
    LOG.append(str(s))


eal = unreal.EditorAssetLibrary
g = eal.load_asset(GRAPH)

for br in ("stylefx", "lineart"):
    for n in g.get_nodes_for_branch(unreal.MovieGraphNode, unreal.Name(br)):
        if "Deferred" in n.get_class().get_name():
            # beauty OFF -> the post-process material becomes the layer output
            n.set_editor_property("include_beauty_render_in_output", False)
            n.set_editor_property("override_b_include_beauty_render_in_output", True)
            # rebuild the PP entry with a name (structs are by-value)
            arr = n.get_editor_property("additional_post_process_materials")
            mat = arr[0].get_editor_property("material")
            pp = unreal.MoviePipelinePostProcessPass()
            pp.set_editor_property("material", mat)
            pp.set_editor_property("name", br)
            try:
                pp.set_editor_property("enabled", True)
            except Exception:
                pass
            n.set_editor_property("additional_post_process_materials", [pp])
            n.set_editor_property("override_additional_post_process_materials", True)
            log("%s: beauty OFF, pp material=%r name=%r" %
                (br, mat.get_name() if mat else None, br))

log("save: %r" % eal.save_asset(GRAPH))
print("\n".join(LOG))
