# Insta360 Ace Pro 2 — Custom Colour / Film-Simulation Project

Investigative project: can this camera be given persistent, in-camera film
simulations like a Fujifilm body, safely and reversibly? **Research and offline
prototyping only. No modification of the camera is performed or recommended yet.**

## Safety posture
- No modified firmware is ever written to the camera or SD card.
- Official firmware is analyzed **read-only**, on local copies, with hash checks.
- Firmware replacement is treated as last resort and currently **not recommended**
  (see Phase 1 §7, §11).

## Contents
| Path | What |
|---|---|
| `PHASE1_RESEARCH.md` | Verified findings on hardware, firmware, colour pipeline, routes, risks |
| `phase2/analyze_firmware.py` | Read-only firmware inspector (container, sections, colour/LUT inventory, signature evidence) |
| `phase2/README.md` | Windows setup + how to read the results |
| `phase3/generate_luts.py` | Generates the five `.cube` film-sim LUTs |
| `phase3/preview.py` | Side-by-side look comparison tool |
| `phase4/PHASE4_FINDINGS.md` | Feasibility evidence from the real firmware |
| `phase5/PHASE5_REPORT.md` | Final recommendation and supported workflow |
| `phase3/luts/` | The generated LUTs (load these today in app/Studio/Premiere/DaVinci) |

## Status
- Phase 1 (research): done.
- Phase 2 (offline analysis): toolkit ready; **needs you to download the official
  firmware on Windows and run `analyze_firmware.py`** (this cloud sandbox cannot
  reach insta360.com). Send me the two JSON outputs for Phase 4.
- Phase 3 (offline PoC): working — LUTs + preview delivered.
- Phase 4 (feasibility): done. Looks are internal colour tables; no microSD
  hook exists on this model; firmware reflash is the only in-camera route.
- Phase 5 (report): done. **Recommendation: do not modify the camera.** See
  `phase5/PHASE5_REPORT.md`.
