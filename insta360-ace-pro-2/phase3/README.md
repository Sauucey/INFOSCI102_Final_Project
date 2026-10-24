# Phase 3 — Offline film-simulation proof of concept (Windows)

Two tools, pure image processing, **no camera contact**:

- `generate_luts.py` — writes five editable `.cube` 3D LUTs to `luts/`.
- `preview.py` — applies any `.cube` to stills and builds a labelled
  side-by-side contact sheet. With no photos it uses a synthetic colour chart.

## The five looks
| File | Look |
|---|---|
| `kodak_warm_film.cube` | Kodak-inspired warm film |
| `fuji_classic_neg.cube` | Fujifilm-inspired classic negative |
| `cinematic_teal.cube` | Cinematic teal shadows |
| `warm_vintage.cube` | Warm vintage film |
| `natural_muted.cube` | Natural muted colours |

Each look is a short, readable function in `generate_luts.py` (lift/gamma/gain,
contrast, saturation, split-tone, highlight roll-off). Tune by eye and re-run.

## Setup (your Surface)
```powershell
pip install numpy pillow
cd <repo>\insta360-ace-pro-2\phase3
python generate_luts.py
python preview.py                      # synthetic chart -> preview_contact_sheet.png
python preview.py --images samples\*.jpg --dump
```

## How this maps to your goal
- **Today, fully supported & reversible:** shoot in **Flat** or **I-Log** on the
  camera, then apply the matching `.cube` in the Insta360 app, Studio, Premiere
  or DaVinci. Video uses the identical LUT, so the look matches the preview.
- **In-camera automatic application (goal #1, #2, #6):** depends on Phase 2/4
  findings about where the camera stores look data. Not deployed here.

## Flat vs I-Log capture note
The Ace Pro 2 records 8-bit 4:2:0. For an 8-bit pipeline, grading from the
**Flat** profile is often cleaner than from I-Log (less banding). Shoot a test
of each and compare before committing a workflow.
