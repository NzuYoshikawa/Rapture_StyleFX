# -*- coding: utf-8 -*-
"""Bundle the StyleFX materials into THIS plugin's content (/Rapture_StyleFX/), from a project that still has
them in /Game/StyleFX (the S1 / AOV_test development projects). Run once:

    import rapture_stylefx.package as p; p.bundle()

Copies the two materials + the two watercolour textures, then (re)creates the three Material Instances the
toggle uses, parented to the bundled materials, carrying over the current /Game MI parameter values (so the
tuning is kept) and pointing the watercolour textures at the bundled copies (self-contained).
Ported from rapture_aov.stylefx_package; only the destination changed.
"""
import unreal

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

PDIR = "/Rapture_StyleFX"
GDIR = "/Game/StyleFX"
TEX = ["T_WC_Noise", "T_WC_Paper"]
MATS = ["M_RaptureStyleFX", "M_RaptureStyleFX_WC"]
# (MI name, parent material, fixed scalar overrides)
MIS = [
    ("MI_RaptureStyleFX", "M_RaptureStyleFX", {}),
    ("MI_RaptureStyleFX_Lineart", "M_RaptureStyleFX", {"LineartOnly": 1.0}),
    ("MI_RaptureStyleFX_WC", "M_RaptureStyleFX_WC", {"WCMode": 3.0}),
]


def _dup(src, dst):
    if eal.does_asset_exist(dst):
        return "exists"
    if not eal.does_asset_exist(src):
        return "SRC MISSING"
    a = eal.duplicate_asset(src, dst)
    if a is None:
        return "DUP FAIL"
    eal.save_asset(dst)
    return "bundled"


def _copy_params(src_mi, dst_mi, parent_mat):
    if src_mi is None:
        return
    for n in mel.get_scalar_parameter_names(parent_mat):
        try:
            mel.set_material_instance_scalar_parameter_value(
                dst_mi, n, mel.get_material_instance_scalar_parameter_value(src_mi, n))
        except Exception:
            pass
    for n in mel.get_vector_parameter_names(parent_mat):
        try:
            mel.set_material_instance_vector_parameter_value(
                dst_mi, n, mel.get_material_instance_vector_parameter_value(src_mi, n))
        except Exception:
            pass


def rebuild_watercolor():
    """A duplicated M_RaptureStyleFX_WC still points its two texture parameters' DEFAULTS at the source project's
    textures (/Game/StyleFX/Textures/...): standalone, the material then fails to compile. Rebuild it from the build script
    (Tools/build_stylefx_wc.py) with this plugin's paths; the Material Instance values are kept.

    NOTE: run this in a FRESH editor session after bundle() (restart the editor first). Inside the session that has just
    duplicated the textures the rebuild can still see the old references (seen 2026-10-07); a second session is clean."""
    import os
    path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Tools", "build_stylefx_wc.py"))
    code = open(path, encoding="utf-8").read()
    for a, b in (('MAT_DIR = "/Game/StyleFX"', 'MAT_DIR = "%s"' % PDIR),
                 ('"/Game/StyleFX/Textures/T_WC_Noise"', '"%s/Textures/T_WC_Noise"' % PDIR),
                 ('"/Game/StyleFX/Textures/T_WC_Paper"', '"%s/Textures/T_WC_Paper"' % PDIR)):
        if a not in code:
            return "rebuild_watercolor: pattern not found in the build script: %s" % a
        code = code.replace(a, b)
    mip = PDIR + "/MI_RaptureStyleFX_WC"
    mi = eal.load_asset(mip) if eal.does_asset_exist(mip) else None
    keep_s, keep_v = {}, {}
    if mi is not None:
        parent = mi.get_editor_property("parent")
        if parent is not None:
            for n in mel.get_scalar_parameter_names(parent):
                keep_s[n] = mel.get_material_instance_scalar_parameter_value(mi, n)
            for n in mel.get_vector_parameter_names(parent):
                keep_v[n] = mel.get_material_instance_vector_parameter_value(mi, n)
    exec(compile(code, path, "exec"), {"__name__": "rapture_stylefx_rebuild"})
    mi = eal.load_asset(mip)
    for n, v in keep_s.items():
        mel.set_material_instance_scalar_parameter_value(mi, n, v)
    for n, v in keep_v.items():
        mel.set_material_instance_vector_parameter_value(mi, n, v)
    for pn, tn in (("NoiseTex", "T_WC_Noise"), ("PaperTex", "T_WC_Paper")):
        mel.set_material_instance_texture_parameter_value(mi, pn, eal.load_asset(PDIR + "/Textures/" + tn))
    eal.save_asset(mip)
    return "rebuild_watercolor: M_RaptureStyleFX_WC rebuilt with plugin textures; MI values restored (%d scalars)" % len(keep_s)


def bundle(force=False, src=None):
    """src: where the materials are now (default /Game/StyleFX; /RaptureAOVPipeline/StyleFX for the copy the old
    Rapture AOV plugin carried)."""
    GDIR = src or globals()["GDIR"]
    log = []
    if force:
        for nm in list(MATS) + ["Textures/" + t for t in TEX]:
            p = PDIR + "/" + nm
            if eal.does_asset_exist(p):
                eal.delete_asset(p)
    for t in TEX:
        log.append("tex %-12s %s" % (t, _dup(GDIR + "/Textures/" + t, PDIR + "/Textures/" + t)))
    for m in MATS:
        log.append("mat %-20s %s" % (m, _dup(GDIR + "/" + m, PDIR + "/" + m)))
    for mi_name, parent_name, fixed in MIS:
        mip = PDIR + "/" + mi_name
        parent = eal.load_asset(PDIR + "/" + parent_name)
        if eal.does_asset_exist(mip):
            mi = eal.load_asset(mip)
        else:
            mi = tools.create_asset(mi_name, PDIR, unreal.MaterialInstanceConstant,
                                    unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, parent)
        src = eal.load_asset(GDIR + "/" + mi_name) if eal.does_asset_exist(GDIR + "/" + mi_name) else None
        _copy_params(src, mi, parent)
        for k, v in fixed.items():
            mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
        if parent_name == "M_RaptureStyleFX_WC":
            for pn, tn in (("NoiseTex", "T_WC_Noise"), ("PaperTex", "T_WC_Paper")):
                tex = eal.load_asset(PDIR + "/Textures/" + tn)
                try:
                    mel.set_material_instance_texture_parameter_value(mi, pn, tex)
                except Exception as e:
                    log.append("  texparam %s ERR %s" % (pn, e))
        eal.save_asset(mip)
        log.append("MI  %-26s ready (parent=%s)" % (mi_name, parent_name))
    msg = "=== [rapture_stylefx.package] bundle ===\n" + "\n".join("  " + x for x in log)
    unreal.log(msg)
    return msg
