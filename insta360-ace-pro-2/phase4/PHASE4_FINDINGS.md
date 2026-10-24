# Phase 4 — Feasibility & recovery review (evidence from your firmware)

Based on the read-only analysis of your own `Insta360AcePro2FW.bin`
(151,943,857 bytes, SHA-256 `9b5b98…b7094`, unchanged by the scan). This is
real evidence from the actual device firmware, not sibling-product inference.

## 1. The headline discovery: looks are swappable table files

Section 2 of the firmware (an Ambarella ROMFS) contains **one file per
colour look**, and every one is the **same size, 17,536 bytes**. These are
Ambarella "3D colour-correction" (CC) tables — the camera's equivalent of a
Fujifilm film-simulation table.

Named looks found as individual files (`VideoCc0_OV50H_<LOOK>`):

| In firmware | Camera menu name |
|---|---|
| `VIVID`, `FLAT`, `LOG`, `PT` | Vivid, Flat, I-Log, (passthrough) |
| `FILM`, `VINTAGE`, `URBAN1` | Film/FI, Vintage, Urban |
| `CC`/`TWOCC`, `NC`/`TWONC` | CC Film / CC2, NC Film / NC2 |
| `LCNATURAL`, `LCVIVID`, `LCNTN`, `LCHC` | Leica Natural, Leica Vivid, Leica NTN, Leica B&W High Contrast |
| `NEON`, `VACATION`, `OBULE1`, `SNOW1`, `NIGHT1`, `BIK1` | Retro Neon, Vintage Vacation, Orange&teal/Blue, Snow, Night, Biking |

There are also per-exposure variants (`VideoCc00_Normal0 … White2`) and
`faceoptimize` variants, plus a matching `capture1_CC_3d.bin` (also 17,536 B)
for stills and `cc3d_cc_bw_gamma_lin_*` tables.

**Why this matters for your goal:** the look maths is **data, not compiled
code**. A custom film simulation is, in principle, just another valid
17,536-byte CC table. That is the single most favourable thing we could have
found. It is the Fujifilm-style architecture you wanted, already present.

## 2. The camera's ISP tuning is fully data-driven

Section 2 also holds the tuning that governs the rest of your wish-list
(contrast, saturation, sharpening, noise reduction, white balance):

- `camera_params.json` (699,961 B) — the schema that lists every shooting
  option and its dependencies (`white_balance`, `filter_mode`, `exposure_bias`,
  `i_log_switch`, resolution gating). This is the UI/选项 layer.
- `adj_video_default_0x_OV50H40`, `adj_photo_*`, `adj_still_*` — ISP adjust
  tables (sharpening, NR, colour, etc.) per mode.
- `aiisp_tuning*.bin`, `scene_data_s0x`, `de_default_*` (detail enhance),
  `aaa_default_*` (auto-exposure/WB/focus).
- Sensor is **OmniVision OV50H** (50 MP). Platform RTOS is RT-Thread,
  codename "tetras".

## 3. Signing & encryption — the real picture

My analyzer flagged "signature-like markers". Having traced each one, **they
are not firmware signing**:

| Marker | Where | What it actually is |
|---|---|---|
| `-----BEGIN` / `CERTIFICATE` / base64 blobs near offset 150–151 M | inside `cacert.pem` and `ca-bundle.crt` | the **Mozilla HTTPS CA trust store** (215,902 B), used for TLS, not boot |
| `RSA`, `signature`, `amba` in section 0 | RTOS / crypto-library strings | library text, not an image signature |
| `0x3082` (DER) at 820 K | section 0 | ubiquitous byte pair; weak signal |

The container's integrity is **CRC32 + MD5 only** (the outer CRC field is
present and every section/ROMFS-file CRC validated). There is **no
cryptographic signature wrapping the firmware image or its sections.** This
matches every other Insta360 Ambarella camera studied publicly.

**Important caveat (do not skip):** an unsigned *update image* does **not**
prove the *bootloader* lacks secure-boot enforcement. The Ambarella CV5 chip
supports fused secure boot. The bootloader is **not** in this update file, so
this firmware cannot tell us whether a modified image would actually boot.
Resolving that by experiment is exactly the bricking risk you forbade.

## 4. Two possible routes, and why only one is safe

| Route | Needs | Safety |
|---|---|---|
| **A. Runtime SD overlay** — put replacement CC tables + a boot hook on the microSD, camera reads them at boot, **nothing written to internal flash**; remove card to revert | the camera's Linux/RTOS init must run a hook script from the card (proven on the CV5-based X5, unconfirmed here) | **Safe IF the hook exists** — avoids the secure-boot question entirely |
| **B. Repack + reflash** modified `Insta360AcePro2FW.bin` | rebuild CRC/MD5 and flash | **Unsafe / not recommended** — depends on unverified secure-boot status, and there is **no documented recovery mode** for this model if it fails |

Route A is the whole reason the X5 project exists: it changes behaviour **in
RAM only**, so a bad table cannot brick the camera — you pull the card.

## 5. The one unknown that decides Route A

The X5 overlay worked because its firmware had a Linux root filesystem whose
startup script (`S99bootdone`) ran a file from the SD card. **Your firmware
shows only 4 sections and no separate Linux root filesystem** — the imaging
side looks RT-Thread-based. So the decisive question is:

> Does section 0 contain a startup that will execute a script, or read
> replacement tables, from the microSD card?

That is answered **read-only**, by scanning the already-carved
`section_00_*.bin` for filesystem contents and init/debug strings. Script:
`phase4/inspect_section0.py` (below). It reads; it changes nothing.

## 6. Recovery reality (unchanged, and firm)

- No public unbrick/boot-recovery procedure exists for the Ace Pro 2.
- Official answer to a failed update is "retry via PC, else repair service."
- Therefore **Route B remains not-recommended** regardless of the signing
  finding, until and unless a recovery path is demonstrated on this exact
  model (it has not been).

## 7. Status vs. your six goals

| Goal | Verdict now |
|---|---|
| 1. Import custom LUT into camera | **Architecturally possible** — looks are swappable CC files. Delivery path (Route A) pending section-0 check. |
| 2. Auto-applied at capture | Yes if a custom CC table is loaded — that is how built-in looks already work. |
| 3. Several selectable film sims | The slot system already supports ~25 looks. |
| 4. Tune contrast/sat/roll-off/WB/sharpen/NR | All data-driven (`adj_*`, `aiisp_tuning*`, `camera_params.json`). |
| 5. Keep stabilisation/waterproof/modes | Route A (RAM overlay) preserves everything; Route B risks it. |
| 6. Phone-free use | A loaded look is used on-camera with no phone. |

**Bottom line:** the camera is built the right way for this, and the firmware
is not signed. The remaining gate is purely whether a *reversible* delivery
path exists. We resolve that with one more read-only scan before anything is
ever written to the camera. **We are still at the feasibility gate. No camera
modification is proposed.**
