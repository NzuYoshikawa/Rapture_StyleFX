# -*- coding: utf-8 -*-
# SF01 priority-1 FULL build : Concept Art Shader 2 clone as a single Post
# Process material (Custom HLSL). Features = depth-remap background, depth Sobel
# outline (relative threshold), 2-stage luminance hatching (procedural stripes),
# 2-stage ink posterise, and a lineart-only mode. All knobs are Material
# parameters (V3 defaults, BGMix=0.75) so a Material Instance can tune them.
# Faithful port of the validated offline mock stylefx_phase0 (ACES is dropped:
# this runs at After-Tonemapping on the already-tonemapped image).
# Idempotent. Run via ue_remote. No literal dot-py token in this body.
import unreal

MAT_NAME = "M_RaptureStyleFX"
MAT_DIR = "/Game/StyleFX"
MAT_PATH = MAT_DIR + "/" + MAT_NAME
MI_NAME = "MI_RaptureStyleFX"
MI_PATH = MAT_DIR + "/" + MI_NAME

LOG = []


def log(s=""):
    LOG.append(str(s))


def trya(label, fn):
    try:
        r = fn()
        log("  [ok] %s -> %r" % (label, r))
        return r, True
    except Exception as e:
        log("  [ERR] %s : %s" % (label, e))
        return None, False


mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

# ---- V3 parameter defaults ----
SCALARS = [
    ("DepthViewDistance", 120.0), ("DepthContrast", 1350.0), ("BGMix", 0.75),
    ("OutlineThreshold", 0.08), ("OutlineSoftness", 0.03),
    ("OutlineWidth", 1.0), ("OutlineWidthFar", 0.0),
    ("HatchTh1", 0.45), ("HatchTh2", 0.20), ("HatchScale", 3.0),
    ("HatchRot1", 35.0), ("HatchRot2", -35.0), ("HatchAngleOffset", 0.0),
    ("HatchLineWidth", 0.07), ("HatchStrength", 0.6),
    ("InkTh1", 0.30), ("InkVal1", 0.62), ("InkTh2", 0.10), ("InkVal2", 0.32),
    ("DepthClipFar", 5000.0), ("LineartOnly", 0.0),
]
VECTORS = [
    ("NearColor", (0.95, 0.93, 0.88)),
    ("FarColor", (0.55, 0.59, 0.66)),
    ("LineColor", (0.07, 0.06, 0.09)),
]
SCENE_PINS = ["SceneDepthPin", "SceneColorPin"]

HLSL = r"""
float2 uv = GetDefaultSceneTextureUV(Parameters, 14);
float2 invSize = View.ViewSizeAndInvSize.zw;

float dC = SceneDepthPin.r;
float3 c = SceneColorPin.rgb;

// 1) depth remap background
float t = saturate((dC - DepthViewDistance) / DepthContrast);
if (dC > 1e7) t = 1.0;
float3 bg = lerp(NearColor.rgb, FarColor.rgb, t);
float3 base = lerp(c, bg, BGMix);

// luma from composited base (matches offline mock)
float luma = dot(base, float3(0.299, 0.587, 0.114));

// 2) depth Sobel outline. Sampling width grows with distance (t) so far
//    geometry gets thicker lines (CAS2 distance-based width).
float w = max(OutlineWidth, 1.0) * (1.0 + OutlineWidthFar * t);
float dcC = min(dC, DepthClipFar);
float Ls = min(SceneTextureLookup(uv + float2(-w, 0)*invSize, 1, false).r, DepthClipFar);
float Rs = min(SceneTextureLookup(uv + float2( w, 0)*invSize, 1, false).r, DepthClipFar);
float Ts = min(SceneTextureLookup(uv + float2( 0,-w)*invSize, 1, false).r, DepthClipFar);
float Bs = min(SceneTextureLookup(uv + float2( 0, w)*invSize, 1, false).r, DepthClipFar);
float TLs = min(SceneTextureLookup(uv + float2(-w,-w)*invSize, 1, false).r, DepthClipFar);
float TRs = min(SceneTextureLookup(uv + float2( w,-w)*invSize, 1, false).r, DepthClipFar);
float BLs = min(SceneTextureLookup(uv + float2(-w, w)*invSize, 1, false).r, DepthClipFar);
float BRs = min(SceneTextureLookup(uv + float2( w, w)*invSize, 1, false).r, DepthClipFar);
float gx = (Rs - Ls) + 0.5*(BRs - BLs) + 0.5*(TRs - TLs);
float gy = (Bs - Ts) + 0.5*(BRs - TRs) + 0.5*(BLs - TLs);
float grad = sqrt(gx*gx + gy*gy) / (2.0*w);
float rel = grad / max(dcC, 30.0);
// OutlineSoftness = width of the gradient over which the line fades out
float edge = smoothstep(OutlineThreshold, OutlineThreshold + max(OutlineSoftness, 1e-4), rel);

// lineart-only mode: white paper, black line
if (LineartOnly > 0.5)
{
    float la = 1.0 - edge;
    return float3(la, la, la);
}

// 3) hatching: 2 procedural stripe layers, luma-gated.
//    HatchAngleOffset rotates the whole cross, HatchLineWidth = line thickness.
float2 px = uv / invSize;
float freq = (1.0/8.0) * max(HatchScale, 0.01);
float a1 = (HatchRot1 + HatchAngleOffset) * 3.14159265 / 180.0;
float a2 = (HatchRot2 + HatchAngleOffset) * 3.14159265 / 180.0;
float r1 = px.x*cos(a1) - px.y*sin(a1);
float r2 = px.x*cos(a2) - px.y*sin(a2);
float d1 = abs(frac(r1*freq + 0.5) - 0.5);
float d2 = abs(frac(r2*freq + 0.5) - 0.5);
float lw = clamp(HatchLineWidth, 0.0, 0.49);
float line1 = 1.0 - smoothstep(lw, lw + 0.08, d1);
float line2 = 1.0 - smoothstep(lw, lw + 0.08, d2);
float m1 = smoothstep(HatchTh1, HatchTh1 - 0.10, luma);
float m2 = smoothstep(HatchTh2, HatchTh2 - 0.08, luma);
float hatch_dark = saturate(line1*m1 + line2*m2);
float3 outc = base * (1.0 - HatchStrength*hatch_dark);

// 4) ink posterise (2 stage multiply)
float i1 = smoothstep(InkTh1, InkTh1 - 0.04, luma);
float i2 = smoothstep(InkTh2, InkTh2 - 0.03, luma);
float ink_mul = (1.0 - i1*(1.0 - InkVal1)) * (1.0 - i2*(1.0 - InkVal2));
outc *= ink_mul;

// 5) outline composite on top
outc = lerp(outc, LineColor.rgb, edge);
return outc;
"""

# ---- idempotent: reuse existing asset (it may be referenced by a PPV /
# SceneCapture), just clear its expression graph and rebuild. Deleting an
# in-use asset returns None from create_asset and breaks the whole build. ----
log("=" * 60)
log("BUILD %s" % MAT_PATH)
log("-" * 60)
if eal.does_asset_exist(MAT_PATH):
    mat = eal.load_asset(MAT_PATH)
    trya("delete_all_material_expressions",
         lambda: mel.delete_all_material_expressions(mat))
    log("reused existing material: %r" % (mat.get_name() if mat else None))
else:
    mat = tools.create_asset(MAT_NAME, MAT_DIR, unreal.Material,
                             unreal.MaterialFactoryNew())
    log("created material: %r" % (mat.get_name() if mat else None))

if mat is None:
    print("\n".join(LOG))
    raise SystemExit("FATAL: material is None")


def mkexpr(cls, x, y):
    e = mel.create_material_expression(mat, cls, x, y)
    if e is None:
        raise RuntimeError("create_material_expression returned None for %r" % cls)
    return e
trya("material_domain=MD_POST_PROCESS",
     lambda: mat.set_editor_property("material_domain",
                                     unreal.MaterialDomain.MD_POST_PROCESS))
trya("blendable_location=AFTER_TONEMAPPING",
     lambda: mat.set_editor_property(
         "blendable_location",
         unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING))

# Custom node
custom = mkexpr(unreal.MaterialExpressionCustom, 0, 0)
trya("output_type=CMOT_FLOAT3",
     lambda: custom.set_editor_property("output_type",
                                        unreal.CustomMaterialOutputType.CMOT_FLOAT3))
trya("description",
     lambda: custom.set_editor_property("description", "RaptureStyleFX_v3"))
trya("code", lambda: custom.set_editor_property("code", HLSL))

# define all named inputs first
input_names = list(SCENE_PINS) + [n for n, _ in SCALARS] + [n for n, _ in VECTORS]


def make_input(name):
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", unreal.Name(name))
    return ci


trya("set custom.inputs (%d)" % len(input_names),
     lambda: custom.set_editor_property("inputs", [make_input(n) for n in input_names]))

# scene texture nodes -> scene pins
st_depth = mkexpr(unreal.MaterialExpressionSceneTexture, -500, -300)
trya("st_depth id=PPI_SCENE_DEPTH",
     lambda: st_depth.set_editor_property("scene_texture_id",
                                          unreal.SceneTextureId.PPI_SCENE_DEPTH))
st_scene = mkexpr(unreal.MaterialExpressionSceneTexture, -500, -150)
trya("st_scene id=PPI_POST_PROCESS_INPUT0",
     lambda: st_scene.set_editor_property("scene_texture_id",
                                          unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0))


def connect_color(src, dst_input):
    if mel.connect_material_expressions(src, "Color", custom, dst_input):
        return True
    return mel.connect_material_expressions(src, "", custom, dst_input)


trya("connect SceneDepth->SceneDepthPin", lambda: connect_color(st_depth, "SceneDepthPin"))
trya("connect SceneColor->SceneColorPin", lambda: connect_color(st_scene, "SceneColorPin"))

# scalar parameters
yy = 0
for name, dv in SCALARS:
    try:
        node = mkexpr(unreal.MaterialExpressionScalarParameter, -500, yy)
        yy += 70
        node.set_editor_property("parameter_name", unreal.Name(name))
        node.set_editor_property("default_value", float(dv))
        ok = mel.connect_material_expressions(node, "", custom, name)
        log(("  [ok] scalar %s=%.3f" % (name, dv)) if ok
            else ("  [ERR] connect scalar %s" % name))
    except Exception as e:
        log("  [ERR] scalar %s : %s" % (name, e))

# vector parameters
for name, (r, g, b) in VECTORS:
    try:
        node = mkexpr(unreal.MaterialExpressionVectorParameter, -500, yy)
        yy += 90
        node.set_editor_property("parameter_name", unreal.Name(name))
        node.set_editor_property("default_value", unreal.LinearColor(r, g, b, 1.0))
        ok = mel.connect_material_expressions(node, "", custom, name)
        log(("  [ok] vector %s=(%.2f,%.2f,%.2f)" % (name, r, g, b)) if ok
            else ("  [ERR] connect vector %s" % name))
    except Exception as e:
        log("  [ERR] vector %s : %s" % (name, e))

trya("connect custom->MP_EMISSIVE_COLOR",
     lambda: mel.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR))
trya("recompile_material", lambda: mel.recompile_material(mat))
n_expr, _ = trya("get_num_material_expressions", lambda: mel.get_num_material_expressions(mat))
trya("save material", lambda: eal.save_asset(MAT_PATH))

# Material Instance for tuning. Reuse (do NOT delete+recreate): deleting it
# invalidates any PPV/SceneCapture that references the MI.
if eal.does_asset_exist(MI_PATH):
    mi = eal.load_asset(MI_PATH)
    log("reused MI")
else:
    mi = tools.create_asset(MI_NAME, MAT_DIR, unreal.MaterialInstanceConstant,
                            unreal.MaterialInstanceConstantFactoryNew())
    log("created MI")
trya("MI parent", lambda: mel.set_material_instance_parent(mi, mat))
trya("MI clear params (inherit current defaults)",
     lambda: mel.clear_all_material_instance_parameters(mi))
trya("save MI", lambda: eal.save_asset(MI_PATH))

log("")
log("FULL build done. expressions=%r" % n_expr)
report = r"E:\UE5\AOV_test\Saved\StyleFX\stylefx_build_report.txt"
print("\n".join(LOG))
try:
    with open(report, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG))
    print("\n[build] wrote " + report)
except Exception as e:
    print("\n[build] report write failed: %s" % e)
