# Rapture_StyleFX

Post-process stylization for Unreal Engine 5.7: depth outline, hatching, ink, a lineart-only mode and a
watercolour whose pigment is locked to world space (reconstructed from depth, so it does not slide when the camera
moves). Content and Python only - no C++ module. Version 0.1.0 (beta).

Split out of **Rapture AOV** on 2026-10-07: Rapture AOV exports data passes; the look lives here.

## Use

1. Put this folder in `<Project>/Plugins/Rapture_StyleFX` (or a junction to it) and enable the plugin.
2. **Tools > Rapture_StyleFX**: toggle NPR / Watercolor / Lineart in the viewport, or *Normal view*.
3. Python: `import rapture_stylefx as sfx` - `sfx.toggle('npr')`, `sfx.set_param('npr', 'OutlineWidth', 2)`, `sfx.list_params('npr')`.
4. As a render pass: add `/Rapture_StyleFX/MI_RaptureStyleFX` (or `_Lineart` / `_WC`) as an additional post-process pass
   of a Movie Render Graph render layer - with *beauty off* and the tone curve ON (the material works after tonemapping).
   See `Tools/build_stylefx_aov_branches.py` (the original wiring of the two render layers, `stylefx` and `lineart`).

Moving the materials into a project that has them in /Game/StyleFX (once): `import rapture_stylefx.package as p; p.bundle()`,
then restart the editor and run `p.rebuild_watercolor()` (the watercolour material must be rebuilt with this plugin's texture paths).

## Contents

| Path | What |
|---|---|
| `Content/` | `M_RaptureStyleFX` (Custom HLSL, 21 scalar parameters), `M_RaptureStyleFX_WC` (watercolour), the three Material Instances, two watercolour textures |
| `Content/Python/rapture_stylefx/` | toggle, bundle, menu |
| `Tools/` | the original build scripts (they recreate the materials from HLSL), the Phase 0 offline mock, the in-editor verification (`verify_in_editor.py`, `run_verify.ps1`). Some scripts keep the author's local paths (`E:\UE5\...`): they are provenance, change the paths before you run them |

## Lines for compositing

The outline here is taken in the post-process from the **depth** (Sobel, relative threshold) - not from an inverted hull
(backface) mesh. If you want to control the lines per character in a compositor, render the depth / normal / base colour
passes per character (for example with Rapture AOV) and take the lines there.

## Licence: CC0 1.0 (public domain dedication)

To the extent possible under law, Takayuki Yoshikawa has waived all copyright and related rights to Rapture_StyleFX.
Use it, change it, sell work made with it - no permission and no credit needed (credit is welcome).
Full text: `LICENSE.txt` / <https://creativecommons.org/publicdomain/zero/1.0/>. Provided as is, without warranty.

## Provenance

Written from scratch (clean room) from published, long-standing techniques (Sobel edges, luminance thresholds,
tiling textures, triplanar projection, depth remap); no third-party asset or code.

Note: CC0 does not grant rights in anyone else's patents or in Unreal Engine itself - using this plugin still requires
Unreal Engine under Epic's licence.
