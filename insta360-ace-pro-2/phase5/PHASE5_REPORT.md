# Phase 5 — Final report and recommendation

Evidence: read-only analysis of the official Ace Pro 2 firmware
(SHA-256 `9b5b98818a05b7e9d95dad00990ad0c8e978aa59de80867d6fc59010d5cb7094`,
unchanged by every scan). Nothing was written to the camera or an SD card.

## Recommendation

**Do not modify this camera.** Every route to custom in-camera looks requires
replacing internal firmware. This model has no verified recovery if that goes
wrong. Use the supported workflow in section 5 instead.

## 1. Verified discoveries

- Built-in looks are stored as separate colour-table resources inside the
  firmware's internal read-only file area, one per look.
- These tables handle colour (hue and saturation). Tone and contrast live in
  separate tuning resources.
- The menu of looks is a fixed list in the firmware. The boot code names each
  look and loads its table from internal storage.
- The boot section is a pure real-time OS image. There is no Linux system, no
  shell, and no hook that reads files from the microSD card at boot.
- The update file is protected by checksums only. No image signature was
  found. Whether the bootloader enforces secure boot is unknown.

## 2. What is technically feasible

| Approach | Feasible? | Reversible? |
|---|---|---|
| Supported post-capture LUTs (app, Studio, editors) | Yes, working today | Yes |
| Built-in filters chosen to approximate each look | Yes | Yes |
| microSD runtime overlay (as on the X5) | No. This model has no card hook | n/a |
| Modified firmware reflash | Possibly, unverified | No verified recovery |

## 3. What remains unknown

- Whether the bootloader would accept a modified image.
- Whether any factory recovery mode exists for this model.
- Neither can be tested without risking the camera, so both stay unknown.

## 4. Safest viable approach

Supported workflow only. In-camera custom looks are not achievable on this
model without accepting a bricking risk that cannot be measured or recovered.

## 5. Proposed plan (no camera modification)

1. **Pick the closest built-in look for phone-free shooting.** Do a short test
   shoot of the same scene in each built-in filter. Then compare against the
   five project LUTs in `phase3/`. Candidates to test first: FILM, CC and CC2
   for warm film. NC and NC2 for classic negative. VINTAGE and VACATION for
   warm vintage. STANDARD for natural muted.
2. **For exact looks, shoot FLAT and apply the project `.cube` LUTs** in the
   Insta360 app, Studio, Premiere or DaVinci. Video and stills match the
   previews.
3. **Request the feature from Insta360.** The firmware already loads looks as
   swappable tables, so user-loadable LUTs would be a small change for them.

## 6. Recovery limitations and risk

| Action | Risk to camera |
|---|---|
| Everything done in this project so far | None. Read-only on local copies |
| Supported workflow above | None |
| Modified firmware reflash | Unquantifiable. A failure could leave the camera unbootable, recoverable only by Insta360 repair, if at all |

This project stops here. No camera modification is proposed.
