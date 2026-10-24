#!/usr/bin/env python3
"""
Phase 4 - read-only inspection of firmware section 0.

Section 0 is the ~20 MB boot/RTOS/kernel blob. This script scans it (and, if
present, the carved section file) for:
  * embedded filesystem magics (squashfs / UBI / ext / cpio / gzip / cramfs)
  * init-system and debug strings that would allow a REVERSIBLE microSD
    overlay (the only safe route to custom in-camera looks)

It only reads. It never writes to anything, and never touches the camera.

Usage (point it at the analysis dir from Phase 2):
    python inspect_section0.py "C:\\insta360\\analysis"
If that fails to find the section file, pass the firmware directly:
    python inspect_section0.py --firmware "C:\\insta360\\work\\Insta360AcePro2FW.bin"
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

FS_MAGICS = {
    "squashfs (hsqs)": b"hsqs",
    "squashfs (sqsh)": b"sqsh",
    "UBI (UBI#)": b"UBI#",
    "UBIFS node": b"\x31\x18\x10\x06",
    "ext2/3/4": None,  # checked specially at +0x438 of candidate blocks
    "cpio (newc)": b"070701",
    "gzip": b"\x1f\x8b\x08",
    "cramfs": b"\x45\x3d\xcd\x28",
    "jffs2": b"\x19\x85",
    "LZMA (5d00)": b"\x5d\x00\x00",
    "XZ": b"\xfd7zXZ\x00",
    "romfs (amba)": b"\x8a\x32\xfc\x66",
    "ARM64 kernel (ARMd@0x38)": b"ARMd",
}

# Strings that indicate a usable, reversible SD-card hook / shell on this model.
HOOK_STRINGS = [
    b"S99bootdone", b"bootdone", b"bootup.sh", b"autoexec", b"auto_run",
    b"cv1_auto_run", b"instaAIP", b"instaAlg", b"rcS", b"init.d",
    b"/tmp/SD0", b"/tmp/SD1", b"/mnt/SCAM", b"mmcblk", b"/sdcard",
    b"telnet", b"telnetd", b"adbd", b"adb_", b"getty", b"/bin/sh",
    b"mount --bind", b"mount -o bind", b"rt-thread", b"tetras",
    b"camera_params.json", b"/pref/", b"VideoCc", b"_OV50H_",
    b"Linux version", b"busybox", b"/sbin/init",
]


# Magics of 3 bytes or fewer match by chance in large files; report but never
# treat them as evidence of a filesystem.
WEAK = {"ext2/3/4", "jffs2", "LZMA (5d00)", "gzip"}


def find_fs(data: bytes) -> list[dict]:
    hits = []
    for name, pat in FS_MAGICS.items():
        if pat is None:
            # ext magic sits at +0x438 within a block; scan a few candidates
            for m in re.finditer(b"\x53\xef", data):
                off = m.start() - 0x438
                if off >= 0:
                    hits.append({"fs": "ext2/3/4", "offset": off, "weak": True})
                    if len([h for h in hits if h["fs"].startswith("ext")]) > 3:
                        break
            continue
        i = data.find(pat)
        count = data.count(pat)
        if i != -1:
            hits.append({"fs": name, "first_offset": i, "count": count,
                         "weak": name in WEAK})
    return hits


def gunzip_streams(data: bytes, out_dir: Path | None, cap=256 * 1024 * 1024):
    """Validate each gzip header by actually decompressing it (read-only on the
    source). Real streams are saved to out_dir for inspection."""
    import zlib
    found = []
    start = 0
    while True:
        off = data.find(b"\x1f\x8b\x08", start)
        if off == -1:
            break
        start = off + 3
        try:
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            out = d.decompress(data[off:], cap)
        except zlib.error:
            continue
        if len(out) < 1024:
            continue
        rec = {"offset": off, "decompressed_bytes": len(out),
               "arm64_kernel": out[0x38:0x3C] == b"ARMd",
               "has_cpio": b"070701" in out,
               "linux_version": b"Linux version" in out}
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            fp = out_dir / f"section0_gzip_{off:08x}.bin"
            fp.write_bytes(out)
            rec["saved_to"] = str(fp)
        rec["hooks"] = find_hooks(out)
        found.append(rec)
    return found


def find_hooks(data: bytes) -> list[dict]:
    out = []
    for s in HOOK_STRINGS:
        i = data.find(s)
        if i != -1:
            lo = max(0, i - 12)
            hi = min(len(data), i + len(s) + 20)
            ctx = "".join(chr(b) if 32 <= b < 127 else "." for b in data[lo:hi])
            out.append({"string": s.decode("latin1"), "offset": i,
                        "count": data.count(s), "context": ctx})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_dir", nargs="?", type=Path,
                    help="Phase 2 output dir (contains sections/)")
    ap.add_argument("--firmware", type=Path, help="full firmware, used if no carved section")
    args = ap.parse_args()

    data = None
    src = None
    if args.analysis_dir:
        secdir = args.analysis_dir / "sections"
        if secdir.is_dir():
            cands = sorted(secdir.glob("section_00_*.bin"))
            if cands:
                src = cands[0]
                data = src.read_bytes()
    if data is None and args.firmware and args.firmware.is_file():
        # Section 0 payload starts at offset 1712, length ~20.35 MB (from report).
        raw = args.firmware.read_bytes()
        src = args.firmware
        data = raw[1712:1712 + 20347660]
    if data is None:
        print("Could not find section_00_*.bin or --firmware. "
              "Re-run analyze_firmware.py with --carve, or pass --firmware.")
        return 2

    print(f"[src] {src}  ({len(data):,} bytes scanned)\n")

    print("== Embedded filesystem / kernel magics ==")
    fs = find_fs(data)
    if fs:
        for h in fs:
            tag = "  (weak: chance matches likely)" if h.get("weak") else ""
            print("  " + ", ".join(f"{k}={v}" for k, v in h.items() if k != "weak") + tag)
    else:
        print("  none found (section may be compressed or bare RTOS)")

    print("\n== Reversible-overlay / debug strings ==")
    hooks = find_hooks(data)
    if hooks:
        for h in hooks:
            print(f"  {h['string']:<20} x{h['count']:<3} @0x{h['offset']:x}  "
                  f"[{h['context']}]")
    else:
        print("  NONE found. A microSD overlay hook is not evident in section 0.")

    print("\n== Compressed blocks (decompressed and rescanned) ==")
    out_dir = args.analysis_dir if args.analysis_dir else None
    gz = gunzip_streams(data, out_dir)
    if not gz:
        print("  no valid gzip streams")
    for g in gz:
        print(f"  @0x{g['offset']:x}: {g['decompressed_bytes']:,} bytes  "
              f"arm64_kernel={g['arm64_kernel']} cpio={g['has_cpio']} "
              f"linux_version={g['linux_version']}")
        if g.get("saved_to"):
            print(f"    saved: {g['saved_to']}")
        for h in g["hooks"]:
            print(f"    {h['string']:<20} x{h['count']:<3} [{h['context']}]")
        hooks = hooks + g["hooks"]

    print("\n== Reading ==")
    has_fs = any(not h.get("weak") for h in fs) or any(
        g["arm64_kernel"] or g["has_cpio"] or g["linux_version"] for g in gz)
    has_sd = any(h["string"] in ("S99bootdone", "bootup.sh", "cv1_auto_run",
                                 "autoexec", "/tmp/SD0", "/mnt/SCAM")
                 for h in hooks)
    if has_sd:
        print("  A card-side boot hook string is present -> the reversible")
        print("  overlay route (Route A) is PLAUSIBLE. Next step is to read the")
        print("  init script's exact logic before anything is ever deployed.")
    elif has_fs:
        print("  A filesystem is embedded but no obvious SD hook string.")
        print("  Route A is uncertain; the init scripts need extracting to decide.")
    else:
        print("  No embedded fs and no SD hook strings: section 0 is likely")
        print("  compressed or pure RTOS. Route A cannot be confirmed from here;")
        print("  Route B (reflash) stays not-recommended. Paste this output back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
