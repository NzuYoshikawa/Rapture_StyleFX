# -*- coding: utf-8 -*-
# Watercolor R&D sibling material M_RaptureStyleFX_WC = the NPR clone stack plus
# three watercolor layers: (1) edge bleed = warp the sampling UV by low-freq
# noise, (2) pigment granulation = noise modulating value, looked up either in
# SCREEN space (WCMode 1) or WORLD-NORMAL UV (WCMode 2), (3) paper grain.
# WCMode 0 == pure NPR (identical to the clean clone). Keeps M_RaptureStyleFX
# untouched. Run via ue_remote.
import unreal

MAT_NAME = "M_RaptureStyleFX_WC"
MAT_DIR = "/Game/StyleFX"
MAT_PATH = MAT_DIR + "/" + MAT_NAME
MI_NAME = "MI_RaptureStyleFX_WC"
MI_PATH = MAT_DIR + "/" + MI_NAME
NOISE_PATH = "/Game/StyleFX/Textures/T_WC_Noise"
PAPER_PATH = "/Game/StyleFX/Textures/T_WC_Paper"
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

SCALARS = [
    ("DepthViewDistance", 120.0), ("DepthContrast", 1350.0), ("BGMix", 0.75),
    ("OutlineThreshold", 0.05), ("OutlineSoftness", 0.05),
    ("OutlineWidth", 1.0), ("OutlineWidthFar", 0.0),
    ("HatchTh1", 0.45), ("HatchTh2", 0.20), ("HatchScale", 1.4),
    ("HatchRot1", 35.0), ("HatchRot2", -35.0), ("HatchAngleOffset", 0.0),
    ("HatchLineWidth", 0.14), ("HatchStrength", 0.6),
    ("InkTh1", 0.30), ("InkVal1", 0.62), ("InkTh2", 0.10), ("InkVal2", 0.32),
    ("DepthClipFar", 5000.0), ("LineartOnly", 0.0),
    # watercolor
    ("WCMode", 0.0), ("BleedAmount", 3.0), ("BleedScale", 3.0),
    ("Granulation", 0.25), ("GranScale", 5.0),
    ("PaperStrength", 0.18), ("PaperScale", 4.0),
    ("TriScale", 40.0),
]
VECTORS = [
    ("NearColor", (0.95, 0.93, 0.88)),
    ("FarColor", (0.55, 0.59, 0.66)),
    ("LineColor", (0.07, 0.06, 0.09)),
]
SCENE_PINS = ["SceneDepthPin", "SceneColorPin", "WorldNormalPin"]
TEX_PINS = ["NoiseTex", "PaperTex"]

HLSL = r"""
float2 uv0 = GetDefaultSceneTextureUV(Parameters, 14);
float2 invSize = ResolvedView.ViewSizeAndInvSize.zw;
float2 px = uv0 / invSize;

// DEBUG (WCMode 9): visualise reconstructed world position as frac(wp/200)
if (WCMode > 8.5)
{
    float sdd = SceneTextureLookup(uv0, 1, false).r;
    float dtx = 1.0 / ResolvedView.ViewToClip[0][0];
    float dty = 1.0 / ResolvedView.ViewToClip[1][1];
    float3 dray = ResolvedView.ViewForward
                + (uv0.x*2.0-1.0)*dtx*ResolvedView.ViewRight
                + (1.0-uv0.y*2.0)*dty*ResolvedView.ViewUp;
    float3 dwp = DFHackToFloat(ResolvedView.WorldCameraOrigin) + dray*sdd;
    return frac(dwp / 200.0);
}

// (WC-1) edge bleed: warp sampling uv by low-freq noise
float2 uv = uv0;
if (WCMode > 0.5)
{
    float2 bUV = px * (BleedScale / 512.0);
    float bx = Texture2DSample(NoiseTex, NoiseTexSampler, bUV).r;
    float by = Texture2DSample(NoiseTex, NoiseTexSampler, bUV + float2(0.37, 0.21)).r;
    uv = uv0 + (float2(bx, by) - 0.5) * (2.0 * BleedAmount) * invSize;
}

float dC = SceneTextureLookup(uv, 1, false).r;
float3 c = SceneTextureLookup(uv, 14, false).rgb;

// 1) depth remap background
float t = saturate((dC - DepthViewDistance) / DepthContrast);
if (dC > 1e7) t = 1.0;
float3 bg = lerp(NearColor.rgb, FarColor.rgb, t);
float3 base = lerp(c, bg, BGMix);
float luma = dot(base, float3(0.299, 0.587, 0.114));

// 2) depth Sobel outline (distance-scaled width)
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
float edge = smoothstep(OutlineThreshold, OutlineThreshold + max(OutlineSoftness, 1e-4), rel);

if (LineartOnly > 0.5)
{
    float la = 1.0 - edge;
    return float3(la, la, la);
}

// 3) hatch
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

// 4) ink posterise
float i1 = smoothstep(InkTh1, InkTh1 - 0.04, luma);
float i2 = smoothstep(InkTh2, InkTh2 - 0.03, luma);
float ink_mul = (1.0 - i1*(1.0 - InkVal1)) * (1.0 - i2*(1.0 - InkVal2));
outc *= ink_mul;

// 5) outline composite
outc = lerp(outc, LineColor.rgb, edge);

// (WC-2) pigment granulation + (WC-3) paper grain
if (WCMode > 0.5)
{
    float gn;
    if (WCMode > 2.5)
    {
        // (C) triplanar, WORLD-POSITION-LOCKED granulation from engine-truth
        // depth+normal -> pigment sticks to geometry (temporally coherent).
        float sd = SceneTextureLookup(uv, 1, false).r;
        float tanX = 1.0 / ResolvedView.ViewToClip[0][0];
        float tanY = 1.0 / ResolvedView.ViewToClip[1][1];
        float ndcx = uv.x * 2.0 - 1.0;
        float ndcy = 1.0 - uv.y * 2.0;
        float3 ray = ResolvedView.ViewForward
                   + ndcx * tanX * ResolvedView.ViewRight
                   + ndcy * tanY * ResolvedView.ViewUp;
        float3 wpos = DFHackToFloat(ResolvedView.WorldCameraOrigin) + ray * sd;
        float3 wn = abs(normalize(WorldNormalPin.rgb));
        float3 bl = wn / (wn.x + wn.y + wn.z + 1e-4);
        float s = max(TriScale, 1.0);
        float tx = Texture2DSample(NoiseTex, NoiseTexSampler, wpos.yz / s).r;
        float ty = Texture2DSample(NoiseTex, NoiseTexSampler, wpos.zx / s).r;
        float tz = Texture2DSample(NoiseTex, NoiseTexSampler, wpos.xy / s).r;
        gn = tx * bl.x + ty * bl.y + tz * bl.z;
    }
    else if (WCMode > 1.5)
    {
        // world-normal UV (form-following)
        gn = Texture2DSample(NoiseTex, NoiseTexSampler,
                             frac(WorldNormalPin.xy * 0.5 + 0.5) * GranScale).r;
    }
    else
    {
        // screen projection
        gn = Texture2DSample(NoiseTex, NoiseTexSampler, px * (GranScale / 512.0)).r;
    }
    outc *= 1.0 - Granulation * (gn - 0.5) * 2.0;

    float pg = Texture2DSample(PaperTex, PaperTexSampler, px * (PaperScale / 256.0)).r;
    outc *= 1.0 - PaperStrength * (1.0 - pg);
}

return saturate(outc);
"""

# ---- build ----
log("BUILD %s" % MAT_PATH)
if eal.does_asset_exist(MAT_PATH):
    mat = eal.load_asset(MAT_PATH)
    trya("delete_all_material_expressions", lambda: mel.delete_all_material_expressions(mat))
else:
    mat = tools.create_asset(MAT_NAME, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
log("mat = %r" % (mat.get_name() if mat else None))


def mkexpr(cls, x, y):
    e = mel.create_material_expression(mat, cls, x, y)
    if e is None:
        raise RuntimeError("create_material_expression None for %r" % cls)
    return e


trya("domain", lambda: mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS))
trya("blendable", lambda: mat.set_editor_property("blendable_location", unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING))

custom = mkexpr(unreal.MaterialExpressionCustom, 0, 0)
trya("output_type", lambda: custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3))
trya("desc", lambda: custom.set_editor_property("description", "RaptureStyleFX_WC"))
trya("code", lambda: custom.set_editor_property("code", HLSL))

input_names = list(SCENE_PINS) + list(TEX_PINS) + [n for n, _ in SCALARS] + [n for n, _ in VECTORS]


def make_input(name):
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", unreal.Name(name))
    return ci


trya("inputs (%d)" % len(input_names),
     lambda: custom.set_editor_property("inputs", [make_input(n) for n in input_names]))

# scene texture pins
st_specs = [("SceneDepthPin", unreal.SceneTextureId.PPI_SCENE_DEPTH),
            ("SceneColorPin", unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0),
            ("WorldNormalPin", unreal.SceneTextureId.PPI_WORLD_NORMAL)]
yy = -360
for pin, sid in st_specs:
    st = mkexpr(unreal.MaterialExpressionSceneTexture, -600, yy)
    yy += 120
    st.set_editor_property("scene_texture_id", sid)
    ok = mel.connect_material_expressions(st, "Color", custom, pin)
    if not ok:
        ok = mel.connect_material_expressions(st, "", custom, pin)
    log("  [%s] scenetex %s" % ("ok" if ok else "ERR", pin))

# texture object parameters
noise_tex = eal.load_asset(NOISE_PATH)
paper_tex = eal.load_asset(PAPER_PATH)
for pin, tex in (("NoiseTex", noise_tex), ("PaperTex", paper_tex)):
    tn = mkexpr(unreal.MaterialExpressionTextureObjectParameter, -600, yy)
    yy += 120
    tn.set_editor_property("parameter_name", unreal.Name(pin))
    tn.set_editor_property("texture", tex)
    ok = mel.connect_material_expressions(tn, "", custom, pin)
    log("  [%s] texobj %s tex=%r" % ("ok" if ok else "ERR", pin, tex.get_name() if tex else None))

# scalar params
for name, dv in SCALARS:
    try:
        node = mkexpr(unreal.MaterialExpressionScalarParameter, -600, yy)
        yy += 60
        node.set_editor_property("parameter_name", unreal.Name(name))
        node.set_editor_property("default_value", float(dv))
        ok = mel.connect_material_expressions(node, "", custom, name)
        if not ok:
            log("  [ERR] scalar %s" % name)
    except Exception as e:
        log("  [ERR] scalar %s : %s" % (name, e))
log("scalars wired")

for name, (r, g, b) in VECTORS:
    try:
        node = mkexpr(unreal.MaterialExpressionVectorParameter, -600, yy)
        yy += 90
        node.set_editor_property("parameter_name", unreal.Name(name))
        node.set_editor_property("default_value", unreal.LinearColor(r, g, b, 1.0))
        mel.connect_material_expressions(node, "", custom, name)
    except Exception as e:
        log("  [ERR] vector %s : %s" % (name, e))
log("vectors wired")

trya("emissive", lambda: mel.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR))
trya("recompile", lambda: mel.recompile_material(mat))
n_expr, _ = trya("num_expr", lambda: mel.get_num_material_expressions(mat))
trya("save", lambda: eal.save_asset(MAT_PATH))

# MI (reuse)
if eal.does_asset_exist(MI_PATH):
    mi = eal.load_asset(MI_PATH)
else:
    mi = tools.create_asset(MI_NAME, MAT_DIR, unreal.MaterialInstanceConstant,
                            unreal.MaterialInstanceConstantFactoryNew())
trya("MI parent", lambda: mel.set_material_instance_parent(mi, mat))
trya("MI clear", lambda: mel.clear_all_material_instance_parameters(mi))
trya("MI save", lambda: eal.save_asset(MI_PATH))

log("WC build done. expressions=%r" % n_expr)
print("\n".join(LOG))
