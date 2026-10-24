#!/usr/bin/env python3
"""
Phase 3 - offline film-simulation LUT generator.

Produces five .cube 3D LUTs (33^3) implementing the looks you asked for:
  1. kodak_warm_film      - Kodak-inspired warm film
  2. fuji_classic_neg     - Fujifilm-inspired classic negative
  3. cinematic_teal       - cinematic teal shadows
  4. warm_vintage         - warm vintage film
  5. natural_muted        - natural muted colours

These are standard Adobe/Resolve .cube files. They work today in the Insta360
app, Insta360 Studio, Premiere and DaVinci on your Surface - the supported,
fully reversible colour workflow. Whether they can later be pushed INTO the
camera is a separate open question handled in Phase 2/4; nothing here touches
the camera.

The maths is deliberately transparent and self-contained (numpy only), so every
look is editable and explainable - the Fujifilm-style point of the project.

Usage:
    python generate_luts.py            # writes luts/*.cube
    python generate_luts.py --size 65  # finer grid
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------- #
# Small colour-grading primitives. Input/output are float arrays in [0,1],
# shape (...,3), linear-ish display RGB (we grade in gamma space on purpose,
# matching how these looks are authored for 8-bit delivery).
# --------------------------------------------------------------------------- #

def _clip(x):
    return np.clip(x, 0.0, 1.0)


def lift_gamma_gain(rgb, lift=(0, 0, 0), gamma=(1, 1, 1), gain=(1, 1, 1)):
    lift = np.asarray(lift, dtype=np.float32)
    gamma = np.asarray(gamma, dtype=np.float32)
    gain = np.asarray(gain, dtype=np.float32)
    out = rgb * gain + lift * (1.0 - rgb)
    out = _clip(out)
    out = np.power(_clip(out), 1.0 / np.maximum(gamma, 1e-4))
    return _clip(out)


def saturation(rgb, s):
    luma = (rgb * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    return _clip(luma + (rgb - luma) * s)


def contrast(rgb, c, pivot=0.435):
    return _clip((rgb - pivot) * c + pivot)


def tone_curve(rgb, shadows=0.0, highlights=0.0, black=0.0, white=1.0):
    """Soft S-curve: lift/crush shadows and roll off highlights."""
    x = _clip((rgb - black) / max(white - black, 1e-4))
    # shadow and highlight shaping via smoothstep-weighted offsets
    sh = (1.0 - x) ** 2
    hi = x ** 2
    x = x + shadows * sh - highlights * hi * (1.0 - x) * 0 + highlights * (x - x ** 1.2)
    return _clip(x)


def highlight_rolloff(rgb, knee=0.75, strength=0.6):
    """Compress values above `knee` toward 1.0 for a filmic shoulder."""
    out = rgb.copy()
    mask = rgb > knee
    comp = knee + (rgb - knee) / (1.0 + strength * (rgb - knee) / max(1 - knee, 1e-4))
    out[mask] = comp[mask]
    return _clip(out)


def channel_mix_warm(rgb, amount=0.06):
    """Push warmth: add to R, subtract from B, gently."""
    out = rgb.copy()
    out[..., 0] = _clip(rgb[..., 0] + amount)
    out[..., 2] = _clip(rgb[..., 2] - amount)
    return out


def split_tone(rgb, shadow_rgb, highlight_rgb, balance=0.5, amount=0.15):
    luma = (rgb * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    w_sh = _clip(1.0 - luma / max(balance, 1e-4))
    w_hi = _clip((luma - balance) / max(1 - balance, 1e-4))
    sh = np.asarray(shadow_rgb, np.float32)
    hi = np.asarray(highlight_rgb, np.float32)
    return _clip(rgb + amount * (w_sh * (sh - 0.5) + w_hi * (hi - 0.5)) * 2.0)


# --------------------------------------------------------------------------- #
# The five looks. Each is a pure function rgb->rgb in [0,1].
# Keep them small and readable so they can be tuned by eye.
# --------------------------------------------------------------------------- #

def look_kodak_warm(rgb):
    x = channel_mix_warm(rgb, 0.05)
    x = lift_gamma_gain(x, lift=(0.015, 0.008, 0.0), gamma=(1.0, 1.0, 0.95),
                        gain=(1.03, 1.0, 0.96))
    x = contrast(x, 1.12)
    x = saturation(x, 1.12)
    x = split_tone(x, shadow_rgb=(0.42, 0.45, 0.55), highlight_rgb=(0.58, 0.52, 0.40),
                   balance=0.5, amount=0.12)
    x = highlight_rolloff(x, knee=0.78, strength=0.5)
    return x


def look_fuji_classic_neg(rgb):
    x = lift_gamma_gain(rgb, lift=(0.0, 0.006, 0.02), gamma=(1.02, 1.0, 1.02),
                        gain=(1.0, 0.99, 1.0))
    x = contrast(x, 1.18)
    x = saturation(x, 0.92)          # muted, with
    # selective: lift blue/green in shadows, warm midtones (classic-neg feel)
    x = split_tone(x, shadow_rgb=(0.40, 0.48, 0.58), highlight_rgb=(0.55, 0.50, 0.42),
                   balance=0.45, amount=0.16)
    x = highlight_rolloff(x, knee=0.72, strength=0.7)
    return x


def look_cinematic_teal(rgb):
    x = contrast(rgb, 1.15)
    x = split_tone(x, shadow_rgb=(0.30, 0.52, 0.58), highlight_rgb=(0.60, 0.50, 0.38),
                   balance=0.5, amount=0.22)   # teal shadows, warm highlights
    x = saturation(x, 1.05)
    x = lift_gamma_gain(x, lift=(0.0, 0.01, 0.015), gamma=(1.0, 1.0, 1.0),
                        gain=(1.02, 1.0, 0.98))
    x = highlight_rolloff(x, knee=0.75, strength=0.6)
    return x


def look_warm_vintage(rgb):
    x = channel_mix_warm(rgb, 0.07)
    x = lift_gamma_gain(x, lift=(0.05, 0.035, 0.02), gamma=(0.95, 0.97, 1.0),
                        gain=(1.0, 0.97, 0.90))   # faded, lifted blacks
    x = contrast(x, 0.92)             # lower contrast = aged
    x = saturation(x, 0.85)
    x = split_tone(x, shadow_rgb=(0.52, 0.46, 0.40), highlight_rgb=(0.60, 0.54, 0.42),
                   balance=0.5, amount=0.14)
    x = highlight_rolloff(x, knee=0.70, strength=0.8)
    return x


def look_natural_muted(rgb):
    x = contrast(rgb, 1.03)
    x = saturation(x, 0.88)
    x = lift_gamma_gain(x, lift=(0.005, 0.005, 0.005), gamma=(1.0, 1.0, 1.0),
                        gain=(1.0, 1.0, 1.0))
    x = highlight_rolloff(x, knee=0.82, strength=0.4)
    return x


LOOKS = {
    "kodak_warm_film": look_kodak_warm,
    "fuji_classic_neg": look_fuji_classic_neg,
    "cinematic_teal": look_cinematic_teal,
    "warm_vintage": look_warm_vintage,
    "natural_muted": look_natural_muted,
}

TITLES = {
    "kodak_warm_film": "Kodak-inspired warm film",
    "fuji_classic_neg": "Fujifilm-inspired classic negative",
    "cinematic_teal": "Cinematic teal shadows",
    "warm_vintage": "Warm vintage film",
    "natural_muted": "Natural muted colours",
}


def build_lut(fn, size=33):
    """Evaluate look `fn` on a size^3 identity lattice. Returns (N,3) in cube order."""
    idx = np.linspace(0.0, 1.0, size, dtype=np.float32)
    # .cube order: red varies fastest
    b, g, r = np.meshgrid(idx, idx, idx, indexing="ij")
    grid = np.stack([r, g, b], axis=-1).reshape(-1, 3)
    return fn(grid)


def write_cube(path: Path, title: str, data: np.ndarray, size: int):
    with open(path, "w", newline="\n") as f:
        f.write(f"# {title}\n")
        f.write("# Generated offline for Insta360 Ace Pro 2 film-sim project.\n")
        f.write(f'TITLE "{title}"\n')
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        for r, g, b in data:
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=33, choices=[17, 33, 65])
    ap.add_argument("-o", "--out", type=Path, default=Path(__file__).parent / "luts")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, fn in LOOKS.items():
        data = build_lut(fn, args.size)
        out = args.out / f"{name}.cube"
        write_cube(out, TITLES[name], data, args.size)
        print(f"wrote {out}  ({args.size}^3)")
    print("done. Load these in the Insta360 app / Studio / Premiere / DaVinci.")


if __name__ == "__main__":
    main()
