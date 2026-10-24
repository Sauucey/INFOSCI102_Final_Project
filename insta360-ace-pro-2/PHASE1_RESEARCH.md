# Insta360 Ace Pro 2 — Phase 1 Research Report

Date: 2026-10-24. Status: research only. No device contact, no downloads flashed, nothing modified.

Legend: **[V]** verified from a primary or first-hand source · **[S]** sibling-product evidence (not Ace Pro 2) · **[H]** hypothesis, unverified.

---

## 1. Hardware and firmware architecture

| Item | Finding | Tag | Source |
|---|---|---|---|
| Main SoC | Ambarella **CV5** (5 nm). Ambarella's Nov-2024 investor call states Ace Pro 2 "is based on our 5nm CV5". Insta360 markets it as "5nm AI chip" + "Pro Imaging Chip". | [V] | [Ambarella Q3 FY25 call](https://investor.ambarella.com/static-files/bdf8b2ee-b49b-4b83-9b7c-7a66b4795ee1), [Ace Pro: CV5/CV52](https://investor.ambarella.com/static-files/df2b9320-48d5-4c2a-ae3a-404e6213fc73) |
| "Pro Imaging Chip" | Second chip handling denoise/ISP. Vendor and function unidentified. No teardown found that reads the markings. | [H] | [Insta360 launch blog](https://www.insta360.com/blog/news/insta360-ace-pro-2-announcement-ai-action-camera.html) |
| OS model (CV5 family) | Dual-world: Ambarella ThreadX RTOS runs the IDSP/sensor pipeline; Linux 5.10 (AArch64) runs Insta360 userspace (`instaAIP`, `instaAlg`, `amba_camctrl`). Documented on the X5 (also CV5). | [S] | [X5 FW Mod: Architecture_Report](https://github.com/shack-32/Insta360-X5-FW-Mod/blob/main/docs/Architecture_Report.md) |
| Firmware container (CV5, X5) | Ambarella multi-partition image: BOOTSTRAP, two ROMFS drives (NN models, `imx586.db` sensor calibration, AI-ISP RTOS binary, voice prompts), LINUX_Kernel, SYS_SW (UBI/UBIFS rootfs), SECURE + SYS_DATA (device trees). | [S] | same |
| Firmware container (H22, Link/GO/X3) | Same family: outer header with CRC32 per partition, `flpart_t` partition headers, 200-byte trailer with per-component MD5 and whole-file MD5. **Checksums only, no RSA/ECDSA, no encryption, no anti-rollback** on the Link. X3 and GO tools unpack/repack the same format. | [S] | [Link FW RE](https://github.com/schlarpc/insta360-link-firmware-re), [X3 tools](https://github.com/nneonneo/Insta360-X3-Firmware-Tools), [GO tools](https://github.com/enekochan/insta360-go-firmware-tool) |
| Secure boot on CV5 | CV5 silicon supports Enhanced Secure Boot / OTP / TrustZone. **Whether Insta360 fused it on is unknown.** The X5 analysis found RSA-2048 signatures appended to some *asset* XML files, so Insta360 does use asset-level signing somewhere. | [H] | [CV5 product brief](https://www.ambarella.com/wp-content/uploads/Ambarella_CV5_Product_Brief_20SEP2021.pdf), X5 Architecture_Report |
| Update file | `Insta360AcePro2FW.bin`, copied to camera root in U-Disk mode; camera reboots and self-flashes. ~145 MB per third-party mirrors. | [V] | [Official manual](https://onlinemanual.insta360.com/acepro2/en-us/camera/maintenance/firmware) |
| Download host pattern | `https://file.insta360.com/static/<hash>/Insta360<Model>FW.bin` (pattern from X3 links). Official page: `insta360.com/download/insta360-acepro2`. | [V] | X3 tools README |

## 2. Firmware version history (third-party trackers; not Insta360 release notes)

| Version | Date | Notes relevant to color |
|---|---|---|
| 2.0.3 | Nov 2025 | Added Leica Eternal, Leica B&W High Contrast profiles; added Retro Neon, Vintage Vacation filters |
| 2.0.6 | 24 Nov 2025 | "Optimized CC Film, CC2 Film, NC Film, NC2 Film filters" |
| 2.0.17 / 2.0.24 | early 2026 | Low-light improvements |
| 2.0.42 | 10 Jun 2026 | Flash + Fill Light accessory support |
| 2.0.50 | 6 Jul 2026 | Stability |
| 2.0.51 | 30 Jul 2026 | Stability (latest listed) |

Sources: [updatemystuff](https://updatemystuff.com/insta360/insta360-ace-pro-2), [touslesdrivers 2.0.50](https://touslesdrivers.com/index.php?v_code=86377&v_page=23), [Notebookcheck 2.0.3](https://www.notebookcheck.net/Insta360-refreshes-Ace-Pro-2-action-camera-with-new-accessories-and-major-firmware-update.1161450.0.html). Takeaway **[V]**: new looks ship *inside firmware images*, which means the look data is a firmware resource, not a downloadable pack. Where it lives is Phase 2's job.

## 3. How colour is implemented today

| Finding | Tag |
|---|---|
| Ace Pro 2 in-camera "Filters": Standard, Vivid, Flat, Leica Natural, Leica Vivid, Warm, Film/FI, Urban, Vintage, Orange&Teal, NC/NC2/CC/CC2 Film, Leica B&W HC, Leica Eternal, Retro Neon, Vintage Vacation. One filter at a time, selected via swipe-from-right > Filter. Availability varies by mode. ([manual](https://onlinemanual.insta360.com/acepro2/en-us/operation-tutorials/shoot-preview/shooting-parameters/filter)) | [V] |
| I-Log (10-bit log) exists for video; LUTs are applied **after** capture in the Insta360 app or Studio. No official in-camera LUT import path exists. ([I-Log](https://onlinemanual.insta360.com/acepro2/en-us/camera/features/log), [App LUT](https://onlinemanual.insta360.com/app/en-us/operation-tutorial/edit-function/lut)) | [V] |
| On the X5 (same SoC generation), `camera_params.json` (`/usr/local/share/script/`, overridable from `/pref/`) is a **UI/schema** file: `color_mode` = STANDARD/VIVID/FLAT, `filter_mode` list, `i_log_switch`, `p3_switch`. It gates which options are shown; it does **not** contain tone curves or LUT tables. The selected option is relayed to the RTOS over RPMsg (`/dev/rpsmg_insta360_scull`). ([ILog guide](https://github.com/shack-32/Insta360-X5-FW-Mod/blob/main/docs/ILog_Mod_and_Architecture_Guide.md)) | [S] |
| Actual filter/LUT math: not located by any public project. Candidates: (a) 3D LUT tables or tone/sat parameter blocks inside the Linux `instaAlg` / `instaAIP` binaries or rootfs data; (b) IDSP tuning tables in the ROMFS / AI-ISP RTOS binary; (c) a GPU/NN post-stage. | [H] |
| Official SDKs (Android/iOS/C++) expose GammaMode/colour mode and filter *selection* only, under an EULA that forbids reverse engineering and open-source mixing. No custom-LUT upload API. ([SDK EULA](https://www.insta360.com/support/supportcourse?post_id=20734), [Android SDK](https://github.com/Insta360Develop/Android-SDK)) | [V] |
| WiFi protocol: TCP 6666 protobuf, reverse-engineered from the ONE RS; option enums (`PhotographyOptionType`) include colour-mode values but no LUT payload. Ace Pro 2 compatibility untested. ([RigacciOrg](https://github.com/RigacciOrg/insta360-wifi-api)) | [S] |

## 4. Debug / runtime access evidence

| Finding | Tag |
|---|---|
| **X5 (CV5) firmware ships with SD-card boot hooks** in `/etc/init.d/S99bootdone`: if `/tmp/SD0/instaAIP` is executable it is run *instead of* the stock daemon; if `/tmp/SD0/bootup.sh` is executable it runs as root; `/mnt/SCAM/cv1_auto_run.sh` likewise. Only the executable bit is checked, no signature. Author reports root `adb shell` and serial console this way, with all overrides in RAM; removing the card restores stock. Author's "zero-risk" claim is **not independently verified** and covers one device. | [S] |
| Older Insta360 (ONE RS, ONE X2): telnet to 192.168.42.1 as root over camera WiFi, no password. Not confirmed on Ace Pro 2. | [S] |
| Insta360 Link: unauthenticated USB vendor class allows arbitrary file read/write on internal volume; `amboot` accepted a modified application partition. Different SoC (H22). | [S] |
| USB "Android" / "Control with Android" mode exists on the Ace series (used by X3 SD-install trick). Whether it exposes ADB on Ace Pro 2 is unknown. | [H] |
| **No** public Ace Pro 2 firmware unpack, root, or LUT project exists on GitHub as of today. The only Ace Pro 2 repos are a Gyroflow issue and a Karoo remote-control app. | [V] |

## 5. Existing reversible modifications

| Project | Device | Reversible? | Tested on Ace Pro 2? |
|---|---|---|---|
| shack-32 X5 SD harness | X5 (CV5) | Claimed yes (RAM-only, pull card) | No |
| nneonneo X3 repack | X3 (H22) | No (flash) | No |
| enekochan GO repack | GO 2/3/3S (H22) | No (flash) | No |

None exists for the Ace Pro 2. **No reversible Ace Pro 2 modification is demonstrated anywhere.**

## 6. Recovery reality

- Official guidance for a failed update is "retry via PC with correct filename and >30 % battery", else repair service. There is **no documented unbrick / bootloader-recovery mode** for the Ace Pro 2. ([update failure](https://onlinemanual.insta360.com/acepro2/en-us/troubleshooting/update-issues/update-failure))
- Ambarella parts usually have a USB boot-ROM download mode, but it is undocumented for CV5 and if secure boot is fused it would require Insta360-signed loaders. Treat flash-level recovery as **unavailable**.

## 7. Candidate routes, ranked (safest first)

| # | Route | Applies in camera? | JPEG + video? | Survives reboot? | Reversible? | Recovery proven on Ace Pro 2? | Verdict today |
|---|---|---|---|---|---|---|---|
| A | Use built-in filters + I-Log + post LUT | Partly (built-in only) | Yes | Yes | n/a | n/a | Supported. Baseline; does not meet goal 1. |
| B | Runtime SD-card hook (if Ace Pro 2 has the X5 `S99bootdone` hooks): bind-mount replacement LUT/param resources from the card, nothing written to flash | Yes, if looks are file resources | Depends on where resources live | Yes while card is inserted | Yes (pull card), **pending verification** | Not applicable to flash; but a bad script could still write to `/pref` | **Most promising. Requires Phase 2 offline confirmation first.** |
| C | Persistent override in `/pref/` (RW flash) via route B | Yes | same | Yes | Needs shell to undo | No | Only after B is proven; deferred. |
| D | Repack and flash modified `Insta360AcePro2FW.bin` | Yes | Yes | Yes | Only by re-flashing stock | **No** | **Recommend against** until container, signature and secure-boot status are known and a recovery path exists. |
| E | WiFi/USB API to switch built-in looks | Selection only | Yes | n/a | Yes | n/a | Useful for a phone-free "profile switcher" but no custom colour. |

## 8. What remains unknown (Phase 2 targets)

1. Does the Ace Pro 2 image unpack with the X3/GO/X5 tooling (same `flpart_t` / ROMFS / UBI layout)?
2. Are the partitions plaintext? Is there any RSA block in the header or trailer beyond MD5/CRC?
3. Does `/etc/init.d/S99bootdone` (or equivalent) contain the SD hooks on Ace Pro 2 firmware?
4. Where is the filter math: file-based 3D LUT tables (search for 17³/33³/65³ float or 16-bit grids, `.cube`, `.3dl`, "lut" strings), parameter blocks, or compiled into RTOS/IDSP code?
5. Are those resources signed (like the X5 thermal XML files)?
6. Is secure boot fused? (Indirect evidence only: look for signature verification code paths in BOOTSTRAP and in the updater.)

## 9. Blocker for the cloud session

This sandbox's proxy denies all `*.insta360.com` hosts (CONNECT 403), so the official firmware cannot be downloaded here. Phase 2 therefore runs on your Windows laptop: you download the official file, and the analysis scripts in this folder run against your local copy. Nothing is sent to the camera.

## 10. Proposed Phase 2 (offline only, Windows)

1. Install: Python 3.12 (python.org), `pip install binwalk` is Linux-centric, so instead use: `7-Zip`, `pip install ubi_reader lief`, and a copy of the X3 `fwtool.py` / GO tool adapted to the Ace Pro 2 header. Ghidra (free, Java) for binaries.
2. Download `Insta360AcePro2FW.bin` from insta360.com/download/insta360-acepro2; record SHA-256; keep the original read-only; work on a copy.
3. Parse container header, partition table, CRCs, trailer MD5; dump partitions.
4. Extract ROMFS and UBIFS; grep init scripts for SD hooks; inventory colour/LUT candidates; check for signatures.
5. Produce a findings report and go/no-go for route B.

## 11. Bottom line

- Verified: CV5 SoC, firmware-delivered looks, no official custom-LUT path, no Ace Pro 2 mod ecosystem, no documented recovery mode.
- Plausible and reversible (pending proof): the X5-style SD-card runtime hook, if present and if looks are file resources.
- Not recommended now: flashing modified firmware.
