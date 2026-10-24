# Phase 2 — Offline firmware analysis (Windows, read-only)

**Nothing in this folder touches the camera.** It inspects a *local copy* of
officially downloaded firmware to answer one question: *where does the Ace Pro 2
store its colour / look data, and is that data replaceable without breaking the
device?* It can only read. There is no repack or reflash code here, by design.

## Safety rules enforced in code
- Opens firmware read-only (`"rb"`). No packing/encoding path exists.
- Records SHA-256 before and after and **aborts if the input changed**.
- Refuses paths that look like a removable/camera volume.
- Reports signature-like markers but never attempts to defeat them.

## What you need (your Surface)
1. **Python 3.12** from python.org (tick "Add to PATH" during install).
2. Optional extras for deeper extraction of the Linux rootfs section:
   ```powershell
   pip install ubi_reader
   ```
   7-Zip (7-zip.org) is handy for squashfs/ext sections if present.

## Get the firmware (official only)
1. On the Surface, open the Insta360 download page for the Ace Pro 2 and
   download `Insta360AcePro2FW.bin` (the same file the camera uses).
2. Put it in a folder like `C:\insta360\orig\`.
3. Make a working copy and keep the original read-only:
   ```powershell
   New-Item -ItemType Directory C:\insta360\work -Force
   Copy-Item C:\insta360\orig\Insta360AcePro2FW.bin C:\insta360\work\
   Set-ItemProperty C:\insta360\orig\Insta360AcePro2FW.bin -Name IsReadOnly -Value $true
   # record the hash so you can prove it never changed
   Get-FileHash C:\insta360\orig\Insta360AcePro2FW.bin -Algorithm SHA256
   ```

## Run the analyzer
```powershell
cd <this repo>\insta360-ace-pro-2\phase2
python analyze_firmware.py "C:\insta360\work\Insta360AcePro2FW.bin" -o "C:\insta360\analysis" --carve
```

## What you get in `C:\insta360\analysis`
- `report.json` — container type, section table, section kinds (kernel / ROMFS /
  UBI / squashfs / device tree), and any signature-like markers found.
- `colour_hints.json` — every offset where look-related strings appear
  (`lut`, `.cube`, `gamma`, `tone`, `color_mode`, `leica`, `vivid`, `flat`,
  `idsp`, `ccm`, `sharpen`, `denoise`, ...), with printable context.
- `sections/` — each carved section as its own `.bin` (with `--carve`).
- `romfs_XX/` — files extracted from any Ambarella ROMFS section, CRC-checked.

## How to read the results (Phase 4 feeds on these)
- **If `colour_hints.json` points into a ROMFS file or the rootfs**, the looks
  are likely *file resources* → the reversible SD-card route (Phase 1 route B)
  becomes worth testing offline first.
- **If the hints land only inside a compiled binary / IDSP blob**, the look math
  is baked into code → custom LUT import is much harder and route B may not help.
- **If `signature_evidence` shows PKCS#7 / certificate / RSA blocks around the
  boot or update sections**, treat firmware replacement as signed → **do not**
  pursue flashing; stay on the supported LUT workflow.

Send me `report.json` and `colour_hints.json` (paste or attach) and I will do the
Phase 4 feasibility and recovery review against the actual evidence.
