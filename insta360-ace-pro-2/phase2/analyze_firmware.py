#!/usr/bin/env python3
"""
Insta360 Ace Pro 2 - Phase 2 offline firmware ANALYZER (read-only).

Purpose: inspect a LOCAL COPY of officially downloaded firmware to learn how
the camera stores its colour/look data. This tool only READS. It never writes
to the camera, never repacks a flashable image, and never alters the input.

Safety design:
  * Opens the firmware strictly read-binary ("rb"). No pack/encode path exists.
  * Refuses to run against a path on a removable/SD volume by name hint, and
    warns if the file is named exactly like the on-camera update file.
  * Records SHA-256 of the input before and after, and fails if they differ.
  * All output goes to a separate analysis directory you choose.

It is format-aware for the Ambarella multi-section container that Insta360
uses across its action cameras (documented publicly for the GO/X3/X5), so it
can label sections and carve them for inspection. If the Ace Pro 2 layout
differs, the tool falls back to a signature scan and tells you what it saw,
rather than guessing.

Usage (Windows PowerShell, from this folder):
    python analyze_firmware.py "C:\\insta360\\orig\\Insta360AcePro2FW.bin" -o "C:\\insta360\\analysis"

Nothing here is specific to a jailbreak. It is an inventory pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zlib
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ---- Publicly documented Ambarella/Insta360 container constants -------------
# (same values used by the open GO 2/3 and X3 community unpackers)
HEADER_MAGIC = 0x8732DFE6          # outer header magic, little-endian u32
SECTION_MAGIC = 0xA324EB90         # per-section header magic
ROMFS_MAGIC = 0x66FC328A           # Ambarella ROMFS
KERNEL_MAGIC = b"ARMd"             # Linux ARM64 image, at +0x38 of a section
DTB_MAGIC = b"\xd0\x0d\xfe\xed"    # flattened device tree
UBI_MAGIC = b"UBI#"                # UBI erase-block header
UBIFS_MAGIC = b"\x31\x18\x10\x06"  # UBIFS node magic
SQUASHFS_LE = b"hsqs"              # squashfs little-endian
EXT_MAGIC = b"\x53\xef"            # ext2/3/4 superblock magic at +0x438

SECTION_HDR_LEN = 0x100
ROMFS_HDR_LEN = 0xA000
ROMFS_ENTRY_LEN = 76               # 64 name + 4 len + 4 off + 4 crc

# Strings that would indicate colour / look / tone processing resources.
COLOUR_HINTS = [
    b"lut", b"LUT", b".cube", b".3dl", b"tetra", b"lattice",
    b"gamma", b"tone", b"curve", b"saturation", b"contrast",
    b"vivid", b"Vivid", b"flat", b"Flat", b"standard", b"Standard",
    b"leica", b"Leica", b"eternal", b"Eternal",
    b"filter", b"color_mode", b"colormode", b"color_style", b"film",
    b"wb_", b"white_balance", b"sharpen", b"sharpness", b"nr_", b"denoise",
    b"i_log", b"ilog", b"iLog", b"hdr", b"idsp", b"IDSP", b"3dtable", b"ccm",
]

SAFE_TEXT_EXT = re.compile(rb"[ -~]{4,}")  # printable ASCII runs >=4


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Section:
    index: int
    offset: int
    length: int
    load_address: int | None = None
    kind: str = "unknown"
    notes: list[str] = field(default_factory=list)


def guard_input(path: Path) -> None:
    p = str(path).lower().replace("\\", "/")
    removable_hints = ("/sd0", "/sdcard", ":/dcim", "/no name", "/untitled")
    if any(h in p for h in removable_hints):
        sys.exit("REFUSING: path looks like a removable/camera volume. "
                 "Copy the firmware to local disk and analyze the copy.")
    if path.name.lower() == "insta360aceprofw.bin":
        print("WARNING: input is named like the ORIGINAL (correct). Good. "
              "This tool will not modify it.")
    # The exact on-camera update name; fine to read, never write back.


def classify_blob(data: bytes) -> tuple[str, list[str]]:
    """Identify a carved section by its leading bytes / embedded magics."""
    notes: list[str] = []
    if len(data) >= 0x3C and data[0x38:0x3C] == KERNEL_MAGIC:
        return "linux_kernel_arm64", notes
    if data[:4] == DTB_MAGIC:
        return "device_tree_blob", notes
    if len(data) >= 4 and int.from_bytes(data[:4], "little") == ROMFS_MAGIC:
        return "ambarella_romfs", notes
    if data[:4] == UBI_MAGIC or UBIFS_MAGIC in data[:0x4000]:
        return "ubi_ubifs", notes
    if data[:4] == SQUASHFS_LE:
        return "squashfs", notes
    if len(data) >= 0x43A and data[0x438:0x43A] == EXT_MAGIC:
        return "ext_filesystem", notes
    # Ambarella bare image usually starts with an ARM branch table.
    if data[:2] in (b"\x00\x00", b"\x18\xf0") or b"\xea" in data[:8]:
        notes.append("possible bare ARM/RTOS image (branch table at start)")
        return "bare_image_or_rtos", notes
    return "unknown", notes


def parse_container(raw: bytes) -> tuple[list[Section], dict]:
    """
    Best-effort parse of the outer Ambarella header + section table.
    Read-only; returns labelled sections and metadata. If the header magic is
    not where expected, we return an empty section list and let the caller fall
    back to a whole-file signature scan.
    """
    meta: dict = {}
    sections: list[Section] = []

    # Outer header magic sits at +0x20 in the documented layout.
    if len(raw) < 0x240:
        meta["container"] = "too small for known header"
        return sections, meta
    magic_at_20 = int.from_bytes(raw[0x20:0x24], "little")
    if magic_at_20 != HEADER_MAGIC:
        meta["container"] = "outer header magic not found at +0x20"
        meta["bytes_at_0x20"] = raw[0x20:0x24].hex()
        return sections, meta

    meta["container"] = "ambarella_multisection"
    meta["outer_crc32_field"] = int.from_bytes(raw[0x24:0x28], "little")
    # Section size/crc table: 16 entries of (u32 size, u32 crc) starting +0x30.
    table_off = 0x30
    entries = []
    for i in range(16):
        off = table_off + i * 8
        size = int.from_bytes(raw[off:off + 4], "little")
        crc = int.from_bytes(raw[off + 4:off + 8], "little")
        entries.append((size, crc))
    meta["raw_section_table"] = [{"size": s, "crc": c} for s, c in entries]

    # Walk sections. Each section is preceded by a 0x100 header; the real
    # payload length is read from that header (Ambarella flpart_t-style).
    # We locate sections by scanning for SECTION_MAGIC to stay robust to
    # layout drift between models.
    pos = 0
    sec_magic_le = SECTION_MAGIC.to_bytes(4, "little")
    idx = 0
    search_from = 0x240
    while True:
        m = raw.find(sec_magic_le, search_from)
        if m == -1:
            break
        # The 0x100 section header contains, in the documented layout:
        #   +0x00 crc32, +0x04 version, +0x08 date, +0x0C length,
        #   +0x10 load_address, +0x14 flags, +0x18 magic(SECTION_MAGIC)
        hdr_start = m - 0x18
        if hdr_start < 0:
            search_from = m + 4
            continue
        length = int.from_bytes(raw[hdr_start + 0x0C:hdr_start + 0x10], "little")
        load = int.from_bytes(raw[hdr_start + 0x10:hdr_start + 0x14], "little")
        payload_start = hdr_start + SECTION_HDR_LEN
        payload = raw[payload_start:payload_start + length] if 0 < length < len(raw) else b""
        kind, notes = classify_blob(payload) if payload else ("empty_or_bad_length", [])
        sec = Section(index=idx, offset=payload_start, length=length,
                      load_address=load, kind=kind, notes=notes)
        sections.append(sec)
        idx += 1
        search_from = payload_start + max(length, 1)
    meta["section_count_found"] = len(sections)
    return sections, meta


def extract_romfs(payload: bytes, out_dir: Path) -> list[dict]:
    """Read-only ROMFS inventory + carve. Verifies per-file CRC32, never repacks."""
    files: list[dict] = []
    if int.from_bytes(payload[:4], "little") != ROMFS_MAGIC:
        return files
    count = int.from_bytes(payload[4:8], "little")
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        base = 8 + i * ROMFS_ENTRY_LEN
        if base + ROMFS_ENTRY_LEN > len(payload):
            break
        name = payload[base:base + 64].split(b"\0", 1)[0].decode("latin1", "replace")
        length = int.from_bytes(payload[base + 64:base + 68], "little")
        offset = int.from_bytes(payload[base + 68:base + 72], "little")
        crc = int.from_bytes(payload[base + 72:base + 76], "little")
        blob = payload[offset:offset + length]
        crc_ok = (zlib.crc32(blob) & 0xFFFFFFFF) == crc
        safe = name.replace("/", "_").replace("\\", "_") or f"file_{i}"
        (out_dir / safe).write_bytes(blob)
        files.append({"name": name, "size": length, "crc_ok": crc_ok})
    return files


def scan_colour_hints(raw: bytes) -> list[dict]:
    """Report offsets where colour/look-related strings appear."""
    hits: list[dict] = []
    for hint in COLOUR_HINTS:
        start = 0
        seen = 0
        while seen < 50:  # cap per hint
            i = raw.find(hint, start)
            if i == -1:
                break
            # grab surrounding printable context
            lo = max(0, i - 16)
            hi = min(len(raw), i + len(hint) + 24)
            ctx = raw[lo:hi]
            ctx_txt = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
            hits.append({"hint": hint.decode("latin1"), "offset": i, "context": ctx_txt})
            start = i + len(hint)
            seen += 1
    return hits


def detect_signature_blocks(raw: bytes) -> list[dict]:
    """
    Look for signs of code signing WITHOUT attempting to defeat it. We only
    report presence/location so the feasibility review is grounded in evidence.
    """
    markers = {
        "PKCS#7/DER SEQUENCE": b"\x30\x82",
        "RSA 'ssh-rsa' label": b"ssh-rsa",
        "X509 'CERTIFICATE'": b"CERTIFICATE",
        "'-----BEGIN'": b"-----BEGIN",
        "Ambarella 'amba' tag": b"amba",
        "'signature'": b"signature",
        "'RSA'": b"RSA",
    }
    out = []
    for label, pat in markers.items():
        i = raw.find(pat)
        if i != -1:
            out.append({"marker": label, "first_offset": i})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only Insta360 Ace Pro 2 firmware analyzer")
    ap.add_argument("firmware", type=Path, help="LOCAL copy of Insta360AcePro2FW.bin")
    ap.add_argument("-o", "--out", type=Path, required=True, help="analysis output directory")
    ap.add_argument("--carve", action="store_true", help="also write carved sections/ROMFS files")
    args = ap.parse_args()

    fw = args.firmware
    if not fw.is_file():
        return int(bool(sys.stderr.write(f"not found: {fw}\n")) or 2)
    guard_input(fw)

    args.out.mkdir(parents=True, exist_ok=True)
    before = sha256(fw)
    print(f"[hash] SHA-256 before: {before}")

    raw = fw.read_bytes()
    report: dict = {
        "input": str(fw),
        "size": len(raw),
        "sha256_before": before,
        "first_32_bytes": raw[:32].hex(),
    }

    sections, meta = parse_container(raw)
    report["container_meta"] = meta
    report["sections"] = [asdict(s) for s in sections]

    if not sections:
        print("[info] Known container header not matched; running signature scan only.")
        report["fallback_signature_scan"] = {
            "ROMFS": [hex(m.start()) for m in re.finditer(re.escape(ROMFS_MAGIC.to_bytes(4, 'little')), raw)][:20],
            "UBI": [hex(m.start()) for m in re.finditer(re.escape(UBI_MAGIC), raw)][:20],
            "SQUASHFS": [hex(m.start()) for m in re.finditer(re.escape(SQUASHFS_LE), raw)][:20],
            "DTB": [hex(m.start()) for m in re.finditer(re.escape(DTB_MAGIC), raw)][:20],
            "KERNEL_ARMd": [hex(m.start()) for m in re.finditer(re.escape(KERNEL_MAGIC), raw)][:20],
        }

    report["signature_evidence"] = detect_signature_blocks(raw)
    hints = scan_colour_hints(raw)
    report["colour_hint_count"] = len(hints)
    (args.out / "colour_hints.json").write_text(json.dumps(hints, indent=2))

    if args.carve and sections:
        carve_dir = args.out / "sections"
        carve_dir.mkdir(exist_ok=True)
        for s in sections:
            blob = raw[s.offset:s.offset + s.length]
            (carve_dir / f"section_{s.index:02d}_{s.kind}.bin").write_bytes(blob)
            if s.kind == "ambarella_romfs":
                files = extract_romfs(blob, args.out / f"romfs_{s.index:02d}")
                report.setdefault("romfs", {})[s.index] = files

    (args.out / "report.json").write_text(json.dumps(report, indent=2))

    after = sha256(fw)
    if after != before:
        sys.exit("FATAL: input hash changed during analysis. This should never "
                 "happen; investigate before trusting results.")
    print(f"[hash] SHA-256 after : {after}  (unchanged - input preserved)")
    print(f"[done] report: {args.out / 'report.json'}")
    print(f"[done] colour hints: {report['colour_hint_count']} "
          f"(see {args.out / 'colour_hints.json'})")
    if report["signature_evidence"]:
        print("[note] signature-like markers present; see report. "
              "This tool does NOT attempt to bypass them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
