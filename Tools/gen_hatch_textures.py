# -*- coding: utf-8 -*-
r"""
gen_hatch_textures.py  (SF01 Phase 0 / 2026-06-12)

線ハッチ・点ハッチの2種をプロシージャル生成する(クリーンルーム自作)。
- 512px / タイリング保証(全変調を整数周波数の周期関数で構成) / グレースケールPNG
- 出力: textures\T_Hatch_Line.png / T_Hatch_Dot.png + プレビュー(2x2タイル)
- 後のUE import(SF01 優先度1)と共用する資産
実行: python_embeded\python.exe gen_hatch_textures.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image

SIZE = 512
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def line_hatch(size=SIZE, period=16, wobble_amp=2.2, ink=0.85):
    """横線ハッチ。wobble・太さ変調は全て画像周期の整数倍 → タイリング保証"""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    # 手描き風うねり(整数周波数2成分)
    wob = (wobble_amp * np.sin(2 * np.pi * 3 * x / size)
           + 0.6 * wobble_amp * np.sin(2 * np.pi * 7 * x / size + 1.3))
    v = (y + wob) % period
    d = np.abs(v - period / 2.0)              # 線中心からの距離
    n_rows = size // period
    row = np.floor((y + wob) / period) % n_rows
    # 線ごとの太さ・濃さ変調(行indexの周期関数)
    thick = 1.6 + 0.8 * np.sin(2 * np.pi * 5 * row / n_rows) \
                + 0.5 * np.sin(2 * np.pi * 11 * row / n_rows + 0.7)
    dark = ink * (0.75 + 0.25 * np.sin(2 * np.pi * 3 * row / n_rows + 2.1))
    stroke = (1.0 - smoothstep(thick * 0.6, thick * 1.4, d)) * dark
    # 線に沿った擦れ(x方向の整数周波数変調)
    dry = 0.85 + 0.15 * np.sin(2 * np.pi * 23 * x / size + row * 2.39996)
    return np.clip(1.0 - stroke * dry, 0.0, 1.0)


def dot_hatch(size=SIZE, grid=16, radius=3.4, ink=0.8, seed=7):
    """点ハッチ。格子点に乱数テーブルjitter(格子index mod nで参照=タイリング保証)。
    トーラス距離で端の点も切れずにwrap"""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    n = size // grid
    gx = np.floor(x / grid).astype(np.int64)
    gy = np.floor(y / grid).astype(np.int64)
    rng = np.random.default_rng(seed)
    jx_t = rng.uniform(-0.32, 0.32, (n, n)).astype(np.float32) * grid
    jy_t = rng.uniform(-0.32, 0.32, (n, n)).astype(np.float32) * grid
    r_t = rng.uniform(0.65, 1.25, (n, n)).astype(np.float32) * radius
    k_t = rng.uniform(0.6, 1.0, (n, n)).astype(np.float32) * ink
    gi = gy % n
    gj = gx % n
    cx = gx * grid + grid / 2.0 + jx_t[gi, gj]
    cy = gy * grid + grid / 2.0 + jy_t[gi, gj]
    dx = np.abs(x - cx); dx = np.minimum(dx, size - dx)
    dy = np.abs(y - cy); dy = np.minimum(dy, size - dy)
    d = np.sqrt(dx * dx + dy * dy)
    r = r_t[gi, gj]
    dot = (1.0 - smoothstep(r * 0.7, r * 1.3, d)) * k_t[gi, gj]
    return np.clip(1.0 - dot, 0.0, 1.0)


def seam_check(img):
    """タイリング検査: 上下端・左右端の差分最大値"""
    return float(np.abs(img[0, :] - img[-1, :]).max()), \
           float(np.abs(img[:, 0] - img[:, -1]).max())


def save_gray(img, path):
    Image.fromarray((img * 255).astype(np.uint8), mode="L").save(path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    texs = {"T_Hatch_Line": line_hatch(), "T_Hatch_Dot": dot_hatch()}
    previews = []
    for name, img in texs.items():
        path = os.path.join(OUT_DIR, name + ".png")
        save_gray(img, path)
        sv, sh = seam_check(img)
        print(f"{name}: saved {path}  seam(v,h)=({sv:.4f},{sh:.4f})")
        tiled = np.tile(img, (2, 2))
        previews.append(tiled)
    prev = np.concatenate(previews, axis=1)
    save_gray(prev, os.path.join(OUT_DIR, "preview_tiled_2x2.png"))
    print("preview:", os.path.join(OUT_DIR, "preview_tiled_2x2.png"))


if __name__ == "__main__":
    main()
