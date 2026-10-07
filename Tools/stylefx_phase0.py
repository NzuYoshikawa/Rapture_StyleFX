# -*- coding: utf-8 -*-
r"""
stylefx_phase0.py  (SF01 Phase 0 / 2026-06-12)

制作シーンのbeauty+真値depth EXRに対し、SF01 §4.2の4機能
(depth remap背景 / depthアウトライン / 輝度2段ハッチング / インク)を
オフラインで適用するlook-devモック。UE実装(優先度1)前の仮説検証用。

- 入力: Saved\MovieRenders\RaptureAOVTestScene_S1_v1\{beauty,depth}\*_%04d.exr
- 出力: Saved\StyleFX\phase0\{stylized,lineart,panels}\
- 既知の差分(レポート記載): S1はAOV契約レンダ(linear)のため、
  本スクリプトはACES近似トーンマップを前置する。UE版はAfter Tonemapping。
- ハッチはスクリーン空間(シャワードア現象は意図的に記録=問題提示素材)

使用例:
  python stylefx_phase0.py                       # 代表3フレームのパネル
  python stylefx_phase0.py --frames 1069,1169
  python stylefx_phase0.py --all --video         # 248f + mp4(stylized/compare)
  python stylefx_phase0.py --set HatchTh1=0.5 --set BGMix=0.7
"""
import sys, os, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.ndimage import median_filter, maximum_filter
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
S1 = r"E:\UE5\AOV_test\Saved\MovieRenders\RaptureAOVTestScene_S1_v1"
OUT = os.path.join(ROOT, "phase0")
TEX_DIR = os.path.join(ROOT, "textures")
FRAME_RANGE = (1069, 1316)
SAMPLE_FRAMES = [1069, 1190, 1316]

# ---- パラメータ既定値(§4.4と同名。UE実装時はMPCへ移植) ----
PARAMS = dict(
    OutlineThreshold=0.05,   # 近傍中央値に対する相対depth差
    OutlineWidth=1,          # サンプリングオフセット(px)
    OutlineDilate=1,         # 線の太らせ(px、0=なし)
    HatchTh1=0.45,           # 1段目ハッチ輝度閾値
    HatchTh2=0.20,           # 2段目(クロス)
    HatchScale=1.4,          # スクリーンUV倍率
    HatchRot1=35.0,          # deg
    HatchRot2=-35.0,
    HatchStrength=0.6,
    InkTh1=0.30, InkVal1=0.62,
    InkTh2=0.10, InkVal2=0.32,
    DepthViewDistance=120.0,  # cm(S1 shot全体min≈79を考慮、shot固定)
    DepthContrast=1350.0,     # cm(同max≈1594)
    NearColor=(0.95, 0.93, 0.88),
    FarColor=(0.55, 0.59, 0.66),
    LineColor=(0.07, 0.06, 0.09),
    BGMix=0.55,              # 0=シーン色 / 1=depth remap背景
    DepthClipFar=5000.0,     # sobel用depthクランプ(sky=1e8対策)
)


# ---- EXR I/O(washout_real.py 検証済みパターン) ----
def read_exr_rgb(path):
    import OpenEXR, Imath
    f = OpenEXR.InputFile(str(path))
    header = f.header()
    dw = header["dataWindow"]
    W = dw.max.x - dw.min.x + 1
    H = dw.max.y - dw.min.y + 1
    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    ch = list(header["channels"].keys())
    pick = [c for c in ("R", "G", "B") if c in ch]
    bufs = [np.frombuffer(f.channel(n, pt), dtype=np.float32).reshape(H, W) for n in pick]
    return np.stack(bufs, axis=-1)


def read_exr_single(path):
    import OpenEXR, Imath
    f = OpenEXR.InputFile(str(path))
    header = f.header()
    dw = header["dataWindow"]
    W = dw.max.x - dw.min.x + 1
    H = dw.max.y - dw.min.y + 1
    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    ch = list(header["channels"].keys())
    return np.frombuffer(f.channel(ch[0], pt), dtype=np.float32).reshape(H, W).copy()


# ---- ユーティリティ ----
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def aces_tonemap(x):
    """Narkowicz ACES近似 + sRGBガンマ(UE After Tonemappingの代用、差分はレポート記載)"""
    x = np.clip(x, 0.0, None)
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    y = np.clip(x * (a * x + b) / (x * (c * x + d) + e), 0.0, 1.0)
    return y ** (1.0 / 2.2)


def shift(img, dy, dx):
    """edgeクランプ付きシフト(np.rollのwrap禁止)"""
    H, W = img.shape
    ys = np.clip(np.arange(H) + dy, 0, H - 1)
    xs = np.clip(np.arange(W) + dx, 0, W - 1)
    return img[ys][:, xs]


def sample_tiled(tex, H, W, scale, rot_deg):
    """スクリーンpx座標を回転・スケールしてタイルテクスチャをbilinearサンプル"""
    th = np.deg2rad(rot_deg)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (np.cos(th) * x - np.sin(th) * y) * scale
    v = (np.sin(th) * x + np.cos(th) * y) * scale
    ts = tex.shape[0]
    u %= ts; v %= ts
    u0 = np.floor(u).astype(np.int64); v0 = np.floor(v).astype(np.int64)
    u1 = (u0 + 1) % ts; v1 = (v0 + 1) % ts
    fu = u - u0; fv = v - v0
    t00 = tex[v0, u0]; t01 = tex[v0, u1]; t10 = tex[v1, u0]; t11 = tex[v1, u1]
    return (t00 * (1 - fu) * (1 - fv) + t01 * fu * (1 - fv)
            + t10 * (1 - fu) * fv + t11 * fu * fv)


# ---- コア: 1フレームのスタイライズ ----
class StyleFX:
    def __init__(self, p):
        self.p = p
        self.tex_line = np.asarray(
            Image.open(os.path.join(TEX_DIR, "T_Hatch_Line.png")), dtype=np.float32) / 255.0
        self.hatch_cache = None  # スクリーン空間=全フレーム共通なのでキャッシュ

    def hatch_fields(self, H, W):
        if self.hatch_cache is None:
            p = self.p
            h1 = sample_tiled(self.tex_line, H, W, p["HatchScale"], p["HatchRot1"])
            h2 = sample_tiled(self.tex_line, H, W, p["HatchScale"], p["HatchRot2"])
            self.hatch_cache = (h1, h2)
        return self.hatch_cache

    def stylize(self, beauty_lin, depth):
        p = self.p
        H, W = depth.shape
        ldr = aces_tonemap(beauty_lin)

        # 1) depth remap背景
        t = np.clip((depth - p["DepthViewDistance"]) / p["DepthContrast"], 0.0, 1.0)
        t[depth > 1e7] = 1.0
        near = np.array(p["NearColor"], np.float32)
        far = np.array(p["FarColor"], np.float32)
        depth_bg = near[None, None, :] + t[..., None] * (far - near)[None, None, :]
        base = ldr + (depth_bg - ldr) * p["BGMix"]

        # 輝度はBGMix合成後の画から取る(暗所シーンで全面ハッチ化するのを防ぐ。
        # UE版でも同一シェーダ内なので合成後参照に揃えられる)
        luma = base[..., 0] * 0.299 + base[..., 1] * 0.587 + base[..., 2] * 0.114

        # 2) depthアウトライン(3x3相当sobel、近傍中央値比の相対閾値)
        dc = np.minimum(depth, p["DepthClipFar"])
        med = median_filter(dc, size=3)
        w = max(int(p["OutlineWidth"]), 1)
        gx = (shift(dc, 0, w) - shift(dc, 0, -w)
              + 0.5 * (shift(dc, w, w) - shift(dc, w, -w))
              + 0.5 * (shift(dc, -w, w) - shift(dc, -w, -w)))
        gy = (shift(dc, w, 0) - shift(dc, -w, 0)
              + 0.5 * (shift(dc, w, w) - shift(dc, -w, w))
              + 0.5 * (shift(dc, w, -w) - shift(dc, -w, -w)))
        grad = np.sqrt(gx * gx + gy * gy) / (2.0 * w)
        rel = grad / np.maximum(med, 30.0)
        edge = smoothstep(p["OutlineThreshold"], p["OutlineThreshold"] * 2.0, rel)
        if p["OutlineDilate"] > 0:
            edge = maximum_filter(edge, size=int(p["OutlineDilate"]) * 2 + 1)

        # 3) ハッチング(輝度2段、スクリーン空間)
        h1, h2 = self.hatch_fields(H, W)
        m1 = smoothstep(p["HatchTh1"], p["HatchTh1"] - 0.10, luma)
        m2 = smoothstep(p["HatchTh2"], p["HatchTh2"] - 0.08, luma)
        hatch_dark = (1.0 - h1) * m1 + (1.0 - h2) * m2
        out = base * (1.0 - p["HatchStrength"] * np.clip(hatch_dark, 0, 1))[..., None]

        # 4) インク(輝度2段ポスタライズ)
        i1 = smoothstep(p["InkTh1"], p["InkTh1"] - 0.04, luma)
        i2 = smoothstep(p["InkTh2"], p["InkTh2"] - 0.03, luma)
        ink_mul = (1.0 - i1 * (1.0 - p["InkVal1"])) * (1.0 - i2 * (1.0 - p["InkVal2"]))
        out *= ink_mul[..., None]

        # 5) アウトライン合成(最前面)
        line = np.array(p["LineColor"], np.float32)
        out = out + (line[None, None, :] - out) * edge[..., None]
        return np.clip(out, 0, 1), ldr, depth_bg, edge


def to_u8(img):
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def save_png(img, path):
    Image.fromarray(to_u8(img)).save(path)


def make_panel(ldr, depth_bg, stylized, edge, frame, path):
    H, W = edge.shape
    pad = 4
    canvas = Image.new("RGB", (W * 2 + pad * 3, H * 2 + pad * 3 + 20), (24, 24, 24))
    lineart = 1.0 - edge
    cells = [
        (to_u8(ldr), "A beauty (ACES tonemapped)"),
        (to_u8(depth_bg), "B depth remap BG"),
        (to_u8(stylized), "C stylized"),
        (to_u8(np.repeat(lineart[..., None], 3, axis=2)), "D lineart (ControlNet cand.)"),
    ]
    drw = ImageDraw.Draw(canvas)
    for i, (img, label) in enumerate(cells):
        x = pad + (i % 2) * (W + pad)
        y = pad + (i // 2) * (H + pad)
        canvas.paste(Image.fromarray(img), (x, y))
        drw.text((x + 6, y + 6), label, fill=(255, 220, 80))
    drw.text((pad, H * 2 + pad * 3 + 2), f"S1 frame {frame}  stylefx_phase0", fill=(200, 200, 200))
    canvas.save(path)


def encode_mp4(frame_paths, out_path, fps=24, side_by_side_with=None):
    """PyAVでmp4化。side_by_side_with: 同名indexのPNG列と横連結"""
    import av
    first = np.asarray(Image.open(frame_paths[0]))
    H, W = first.shape[:2]
    if side_by_side_with:
        W *= 2
    container = av.open(out_path, "w")
    stream = container.add_stream("h264", rate=fps)
    stream.width = W; stream.height = H
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "18"}
    for i, fp in enumerate(frame_paths):
        img = np.asarray(Image.open(fp).convert("RGB"))
        if side_by_side_with:
            img2 = np.asarray(Image.open(side_by_side_with[i]).convert("RGB"))
            img = np.concatenate([img2, img], axis=1)
        frame = av.VideoFrame.from_ndarray(img, format="rgb24")
        for pkt in stream.encode(frame):
            container.mux(pkt)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()
    print("mp4:", out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=None, help="comma区切りframe番号")
    ap.add_argument("--all", action="store_true", help="全248フレーム")
    ap.add_argument("--video", action="store_true", help="mp4出力(--all推奨)")
    ap.add_argument("--set", action="append", default=[], help="PARAMS上書き key=val")
    args = ap.parse_args()

    p = dict(PARAMS)
    for kv in args.set:
        k, v = kv.split("=", 1)
        if k not in p:
            raise SystemExit(f"unknown param: {k}")
        p[k] = type(p[k])(eval(v)) if not isinstance(p[k], tuple) else tuple(eval(v))
    print("PARAMS:", {k: v for k, v in p.items()})

    if args.all:
        frames = list(range(FRAME_RANGE[0], FRAME_RANGE[1] + 1))
    elif args.frames:
        frames = [int(s) for s in args.frames.split(",")]
    else:
        frames = SAMPLE_FRAMES

    for sub in ("stylized", "lineart", "panels"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)

    fx = StyleFX(p)
    t0 = time.time()
    sty_paths, beauty_png_paths = [], []
    for n, fr in enumerate(frames):
        beauty = read_exr_rgb(os.path.join(S1, "beauty", f"beauty_{fr:04d}.exr"))
        depth = read_exr_single(os.path.join(S1, "depth", f"depth_{fr:04d}.exr"))
        stylized, ldr, depth_bg, edge = fx.stylize(beauty, depth)

        sp = os.path.join(OUT, "stylized", f"stylized_{fr:04d}.png")
        save_png(stylized, sp); sty_paths.append(sp)
        lp = os.path.join(OUT, "lineart", f"lineart_{fr:04d}.png")
        save_png(np.repeat((1.0 - edge)[..., None], 3, axis=2), lp)
        if args.video:
            bp = os.path.join(OUT, "stylized", f"_beauty_{fr:04d}.png")
            save_png(ldr, bp); beauty_png_paths.append(bp)
        if fr in SAMPLE_FRAMES or not args.all:
            make_panel(ldr, depth_bg, stylized, edge, fr,
                       os.path.join(OUT, "panels", f"panel_{fr:04d}.png"))
        if n == 0:
            d = depth[depth < 1e7]
            print(f"frame {fr}: depth p1/p50/p99 = "
                  f"{np.percentile(d,1):.0f}/{np.percentile(d,50):.0f}/{np.percentile(d,99):.0f} cm, "
                  f"sky {100.0*(depth>1e7).mean():.1f}%, {time.time()-t0:.2f}s/frame")
    dt = time.time() - t0
    print(f"done {len(frames)} frames in {dt:.1f}s ({dt/max(len(frames),1):.2f}s/frame)")

    if args.video:
        encode_mp4(sty_paths, os.path.join(OUT, "stylized.mp4"))
        encode_mp4(sty_paths, os.path.join(OUT, "compare_beauty_vs_stylized.mp4"),
                   side_by_side_with=beauty_png_paths)


if __name__ == "__main__":
    main()
