# -*- coding: utf-8 -*-
# Generate seamless (FFT-periodic) tiling noise textures for the watercolor R&D:
#   T_WC_Noise = low-freq blotchy (pigment pooling / edge bleed warp)
#   T_WC_Paper = high-freq grain (paper texture)
# Clean-room procedural (no external asset). Run with ComfyUI python.
import os
import numpy as np
from PIL import Image

OUT = r"E:\UE5\AOV_test\Saved\StyleFX\textures"
os.makedirs(OUT, exist_ok=True)
N = 1024
fy = np.fft.fftfreq(N)[:, None]
fx = np.fft.fftfreq(N)[None, :]
f2 = fx * fx + fy * fy


def periodic_blur(field, sigma):
    F = np.fft.fft2(field)
    g = np.exp(-2.0 * (np.pi * sigma) ** 2 * f2)
    return np.real(np.fft.ifft2(F * g))


def fbm(sigmas, amps, seed):
    r = np.random.default_rng(seed)
    out = np.zeros((N, N))
    for s, a in zip(sigmas, amps):
        w = r.standard_normal((N, N))
        b = periodic_blur(w, s)
        b = (b - b.mean()) / (b.std() + 1e-6)
        out += a * b
    out = (out - out.min()) / (out.max() - out.min() + 1e-9)
    return out


noise = fbm([50, 25, 12], [0.6, 0.3, 0.15], 7)      # blotchy pigment / bleed
# contrast curve to make it more "pooled"
noise = np.clip((noise - 0.5) * 1.3 + 0.5, 0, 1)
paper = fbm([3.0, 1.6], [0.7, 0.4], 11)             # fine paper grain

Image.fromarray((noise * 255).astype(np.uint8)).save(os.path.join(OUT, "T_WC_Noise.png"))
Image.fromarray((paper * 255).astype(np.uint8)).save(os.path.join(OUT, "T_WC_Paper.png"))
# small preview (2x2 tile to confirm seamlessness)
for nm, arr in (("T_WC_Noise", noise), ("T_WC_Paper", paper)):
    small = Image.fromarray((arr * 255).astype(np.uint8)).resize((256, 256))
    tile = Image.new("L", (512, 512))
    for i in range(2):
        for j in range(2):
            tile.paste(small, (i * 256, j * 256))
    tile.save(os.path.join(OUT, "_preview_tile_%s.png" % nm))
print("saved noise + paper + tile previews to", OUT)
