#!/usr/bin/env python3
"""
Phase 3 - offline look preview / comparison tool (Windows-friendly, numpy+Pillow).

What it does, entirely on your laptop:
  * Loads any .cube 3D LUT and applies it to JPEG/PNG stills via trilinear
    interpolation (the same operation the camera's hardware LUT would do).
  * Builds a side-by-side contact sheet: ORIGINAL + each look, labelled.
  * If you give it no images, it synthesises a colour test chart (skin tones,
    sky, foliage, greyscale ramp, saturated primaries) so you can judge the
    looks before shooting anything.

This previews stills. For video, apply the same .cube in DaVinci/Premiere; the
look is identical because it is the same LUT. Nothing here contacts the camera.

Usage:
    python preview.py                              # synthetic chart, all luts/
    python preview.py --images samples/*.jpg       # your own photos
    python preview.py --lut luts/kodak_warm_film.cube --images a.jpg
Outputs: preview_contact_sheet.png (+ per-image/look PNGs with --dump).
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ----------------------------- LUT loading -------------------------------- #

def load_cube(path: Path):
    size = None
    dmin = np.array([0, 0, 0], np.float32)
    dmax = np.array([1, 1, 1], np.float32)
    rows = []
    title = path.stem
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key = s.split()[0].upper()
        if key == "TITLE":
            title = s.split('"')[1] if '"' in s else title
        elif key == "LUT_3D_SIZE":
            size = int(s.split()[1])
        elif key == "DOMAIN_MIN":
            dmin = np.array(list(map(float, s.split()[1:4])), np.float32)
        elif key == "DOMAIN_MAX":
            dmax = np.array(list(map(float, s.split()[1:4])), np.float32)
        else:
            parts = s.split()
            if len(parts) == 3:
                try:
                    rows.append([float(p) for p in parts])
                except ValueError:
                    pass
    if size is None:
        raise ValueError(f"{path}: no LUT_3D_SIZE")
    data = np.asarray(rows, np.float32)
    if data.shape[0] != size ** 3:
        raise ValueError(f"{path}: expected {size**3} entries, got {data.shape[0]}")
    # cube order: red fastest -> reshape to [b,g,r,3]
    lut = data.reshape(size, size, size, 3)
    return {"title": title, "size": size, "lut": lut, "dmin": dmin, "dmax": dmax}


def apply_lut(img: np.ndarray, cube) -> np.ndarray:
    """img: HxWx3 float [0,1]. Trilinear interpolation over the 3D lattice."""
    size = cube["size"]
    lut = cube["lut"]
    dmin, dmax = cube["dmin"], cube["dmax"]
    x = np.clip((img - dmin) / np.maximum(dmax - dmin, 1e-6), 0, 1)
    coord = x * (size - 1)
    i0 = np.floor(coord).astype(np.int32)
    i1 = np.minimum(i0 + 1, size - 1)
    f = coord - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    r1, g1, b1 = i1[..., 0], i1[..., 1], i1[..., 2]
    fr = f[..., 0:1]; fg = f[..., 1:2]; fb = f[..., 2:3]

    def L(bi, gi, ri):            # lut indexed [b,g,r]
        return lut[bi, gi, ri]

    c000 = L(b0, g0, r0); c100 = L(b0, g0, r1)
    c010 = L(b0, g1, r0); c110 = L(b0, g1, r1)
    c001 = L(b1, g0, r0); c101 = L(b1, g0, r1)
    c011 = L(b1, g1, r0); c111 = L(b1, g1, r1)
    c00 = c000 * (1 - fr) + c100 * fr
    c01 = c001 * (1 - fr) + c101 * fr
    c10 = c010 * (1 - fr) + c110 * fr
    c11 = c011 * (1 - fr) + c111 * fr
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg
    out = c0 * (1 - fb) + c1 * fb
    return np.clip(out, 0, 1)


# ----------------------------- test chart --------------------------------- #

def synth_chart(w=640, h=426) -> np.ndarray:
    img = np.zeros((h, w, 3), np.float32)
    # top: sky gradient
    sky = np.linspace([0.25, 0.45, 0.78], [0.72, 0.84, 0.95], h // 3)
    img[:h // 3] = sky[:, None, :]
    # middle: foliage + skin swatches
    mid0 = h // 3; mid1 = 2 * h // 3
    img[mid0:mid1] = np.array([0.20, 0.38, 0.14], np.float32)   # foliage green
    swatches = [(0.86, 0.68, 0.56), (0.70, 0.50, 0.42), (0.95, 0.80, 0.70),
                (0.55, 0.38, 0.30)]                             # skin tones
    sw_w = w // len(swatches)
    for i, c in enumerate(swatches):
        img[mid0:mid0 + (mid1 - mid0) // 2, i * sw_w:(i + 1) * sw_w] = c
    # bottom: greyscale ramp + saturated primaries
    bot = 2 * h // 3
    ramp = np.linspace(0, 1, w)
    img[bot:bot + (h - bot) // 2] = ramp[None, :, None]
    prim = [(0.9, 0.1, 0.1), (0.1, 0.8, 0.2), (0.1, 0.3, 0.9),
            (0.9, 0.8, 0.1), (0.8, 0.1, 0.8), (0.1, 0.8, 0.85)]
    pw = w // len(prim)
    for i, c in enumerate(prim):
        img[bot + (h - bot) // 2:, i * pw:(i + 1) * pw] = c
    return np.clip(img, 0, 1)


# ----------------------------- IO + layout -------------------------------- #

def load_image(path: Path, max_w=640) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)))
    return np.asarray(im, np.float32) / 255.0


def to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    d.rectangle([0, 0, im.width, 22], fill=(0, 0, 0))
    d.text((6, 3), text, fill=(255, 255, 255), font=font)
    return im


def contact_sheet(base: np.ndarray, cubes: list, cols=3, pad=8) -> Image.Image:
    tiles = [label(to_pil(base), "ORIGINAL")]
    for c in cubes:
        tiles.append(label(to_pil(apply_lut(base, c)), c["title"]))
    tw, th = tiles[0].width, tiles[0].height
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * th + (rows + 1) * pad),
                      (28, 28, 30))
    for i, t in enumerate(tiles):
        r, cc = divmod(i, cols)
        sheet.paste(t, (pad + cc * (tw + pad), pad + r * (th + pad)))
    return sheet


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--lut", type=Path, help="single .cube; default: all in luts/")
    ap.add_argument("--images", nargs="*", help="globs of stills; default: synthetic chart")
    ap.add_argument("--dump", action="store_true", help="also write each look as its own PNG")
    ap.add_argument("-o", "--out", type=Path, default=here / "preview_contact_sheet.png")
    args = ap.parse_args()

    if args.lut:
        cube_paths = [args.lut]
    else:
        cube_paths = sorted((here / "luts").glob("*.cube"))
    if not cube_paths:
        raise SystemExit("No .cube files. Run generate_luts.py first.")
    cubes = [load_cube(p) for p in cube_paths]
    print(f"loaded {len(cubes)} LUT(s): {', '.join(c['title'] for c in cubes)}")

    if args.images:
        paths = [Path(p) for g in args.images for p in glob.glob(g)]
        bases = [(p.stem, load_image(p)) for p in paths]
        if not bases:
            raise SystemExit("No images matched.")
    else:
        bases = [("test_chart", synth_chart())]
        print("no images given -> using synthetic colour chart")

    for stem, base in bases:
        sheet = contact_sheet(base, cubes)
        out = args.out if len(bases) == 1 else here / f"preview_{stem}.png"
        sheet.save(out)
        print(f"wrote {out}")
        if args.dump:
            dd = here / "dump"; dd.mkdir(exist_ok=True)
            for c in cubes:
                to_pil(apply_lut(base, c)).save(dd / f"{stem}__{c['title'].replace(' ', '_')}.png")


if __name__ == "__main__":
    main()
