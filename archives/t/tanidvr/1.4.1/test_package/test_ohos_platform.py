#!/usr/bin/env python3
"""HarmonyOS-specific verification of the packaged tanidvr binaries.

    test_ohos_platform.py --tanidvr <tanidvr command> --dhav2mkv <dhav2mkv command>

These checks are specific to the HarmonyOS PC (OHOS aarch64) target: the
delivered executables must be OHOS/musl programs, not glibc Linux binaries
that merely happen to run on aarch64.
"""

import os
import struct
import subprocess
import sys
import tempfile


def split_commands(argv):
    """Split "--tanidvr <tokens...> --dhav2mkv <tokens...>".

    A hand-rolled split is used because argparse.REMAINDER swallows the second
    marker and plain argparse rejects emulator flags such as "-L".
    """
    commands = {}
    key = None
    for token in argv:
        if token in ("--tanidvr", "--dhav2mkv"):
            key = token[2:]
            commands[key] = []
        elif key is not None:
            commands[key].append(token)
    return commands


COMMANDS = split_commands(sys.argv[1:])
TANIDVR = COMMANDS.get("tanidvr", [])
DHAV2MKV = COMMANDS.get("dhav2mkv", [])
if not TANIDVR or not DHAV2MKV:
    sys.exit("usage: test_ohos_platform.py --tanidvr <cmd> --dhav2mkv <cmd>")

EM_AARCH64 = 183
ET_DYN = 3
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
# OHOS ships both musl loader names and they coexist on the device; a glibc
# aarch64 build would ask for /lib64/ld-linux-aarch64.so.2 instead.
OHOS_MUSL_LOADERS = (b"/lib/ld-musl-aarch64.so.1", b"/lib/ld-linux-aarch64.so.1")
GLIBC_LOADER = b"ld-linux-aarch64.so.2"

passed = []


def check(condition, message):
    if not condition:
        print(f"FAIL: {message}")
        sys.exit(1)
    passed.append(message)
    print(f"ok: {message}")


def program_headers(blob, little_endian):
    endian = "<" if little_endian else ">"
    offset = struct.unpack_from(endian + "Q", blob, 32)[0]
    entry_size = struct.unpack_from(endian + "H", blob, 54)[0]
    entry_count = struct.unpack_from(endian + "H", blob, 56)[0]
    headers = []
    for index in range(entry_count):
        base = offset + index * entry_size
        p_type = struct.unpack_from(endian + "I", blob, base)[0]
        p_offset = struct.unpack_from(endian + "Q", blob, base + 8)[0]
        p_vaddr = struct.unpack_from(endian + "Q", blob, base + 16)[0]
        p_filesz = struct.unpack_from(endian + "Q", blob, base + 32)[0]
        headers.append((p_type, p_offset, p_vaddr, p_filesz))
    return headers


def vaddr_to_offset(headers, vaddr):
    for p_type, p_offset, p_vaddr, p_filesz in headers:
        if p_type != PT_LOAD:
            continue
        if p_vaddr <= vaddr < p_vaddr + p_filesz:
            return p_offset + (vaddr - p_vaddr)
    return None


def dynamic_needed(blob, little_endian, headers):
    """Return the DT_NEEDED sonames of an ELF64 binary."""
    endian = "<" if little_endian else ">"
    dynamic = next((h for h in headers if h[0] == PT_DYNAMIC), None)
    if dynamic is None:
        return []
    _, dyn_offset, _, dyn_size = dynamic
    strtab_vaddr = None
    strtab_size = None
    needed_offsets = []
    position = dyn_offset
    while position + 16 <= dyn_offset + dyn_size:
        tag, value = struct.unpack_from(endian + "qQ", blob, position)
        if tag == DT_NULL:
            break
        if tag == DT_STRTAB:
            strtab_vaddr = value
        elif tag == DT_STRSZ:
            strtab_size = value
        elif tag == DT_NEEDED:
            needed_offsets.append(value)
        position += 16
    if strtab_vaddr is None:
        return []
    strtab_offset = vaddr_to_offset(headers, strtab_vaddr)
    if strtab_offset is None:
        return []
    limit = strtab_size or len(blob) - strtab_offset
    table = blob[strtab_offset:strtab_offset + limit]
    sonames = []
    for entry in needed_offsets:
        end = table.find(b"\x00", entry)
        sonames.append(table[entry:end].decode("utf-8", "replace"))
    return sonames


def read_elf(path):
    with open(path, "rb") as handle:
        blob = handle.read()
    check(blob[:4] == b"\x7fELF", f"{os.path.basename(path)} is an ELF binary")
    little_endian = blob[5] == 1
    endian = "<" if little_endian else ">"
    headers = program_headers(blob, little_endian)
    interpreter = None
    for p_type, p_offset, _p_vaddr, p_filesz in headers:
        if p_type == PT_INTERP:
            interpreter = blob[p_offset:p_offset + p_filesz].rstrip(b"\x00")
    return {
        "class": blob[4],
        "machine": struct.unpack_from(endian + "H", blob, 18)[0],
        "type": struct.unpack_from(endian + "H", blob, 16)[0],
        "interpreter": interpreter,
        "needed": dynamic_needed(blob, little_endian, headers),
        "blob": blob,
    }


tanidvr_elf = read_elf(TANIDVR[-1])
dhav2mkv_elf = read_elf(DHAV2MKV[-1])

for label, elf in (("tanidvr", tanidvr_elf), ("dhav2mkv", dhav2mkv_elf)):
    interpreter = elf["interpreter"] or b"<none>"
    check(elf["class"] == 2, f"{label} is a 64-bit ELF")
    check(elf["machine"] == EM_AARCH64, f"{label} targets aarch64")
    check(elf["type"] == ET_DYN, f"{label} is built as a position-independent executable")
    check(
        elf["interpreter"] in OHOS_MUSL_LOADERS,
        f"{label} uses an OHOS musl loader (interpreter={interpreter.decode()})",
    )
    check(
        GLIBC_LOADER not in (elf["interpreter"] or b""),
        f"{label} does not use the glibc loader {GLIBC_LOADER.decode()}",
    )
    check(
        elf["needed"] == ["libc.so"],
        f"{label} has exactly one DT_NEEDED, the OHOS libc.so (got {elf['needed']})",
    )
    check(
        b"libc.so.6" not in elf["blob"],
        f"{label} does not depend on the glibc-only libc.so.6 soname",
    )
    check(
        b"libpthread.so" not in elf["blob"] and b"libdl.so" not in elf["blob"],
        f"{label} relies on the OHOS musl libc which merges pthread/dl into libc",
    )

banners = (
    ("tanidvr", TANIDVR, "TaniDVR 1.4.1"),
    ("dhav2mkv", DHAV2MKV, "dhav2mkv 1.4.1"),
)
for label, command, banner in banners:
    result = subprocess.run(
        [*command, "-h"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    check(result.returncode == 0, f"{label} runs on the OHOS userspace")
    check(
        banner in result.stdout.decode("utf-8", "replace"),
        f"{label} reports its upstream version when executed on OHOS",
    )

workdir = tempfile.mkdtemp(prefix="tanidvr-ohos-")


def dhav_frame(frame_type, timestamp, epoch, body):
    # extended header: field 0x80 -> [0x80, -, width/8, height/8],
    #                   field 0x81 -> [0x81, -, -, frame rate]
    ext_head = bytes([0x80, 0x00, 80, 60, 0x81, 0x00, 0x00, 25])
    header = bytearray(24)
    header[0:4] = b"DHAV"
    header[4] = frame_type
    struct.pack_into("<I", header, 16, epoch)
    struct.pack_into("<H", header, 20, timestamp)
    header[22] = len(ext_head)
    total = 24 + len(ext_head) + len(body) + 8
    struct.pack_into("<I", header, 12, total)
    return bytes(header) + ext_head + body + b"dhav" + struct.pack("<I", total)


payload = b"\x00\x00\x00\x01" + bytes([0x65]) + b"\x11" * 64
stream = dhav_frame(0xFD, 0, 1700000000, payload) + dhav_frame(
    0xFC, 40, 1700000000, payload
)
outputs = []
for run_index in range(2):
    target = os.path.join(workdir, f"run{run_index}.mkv")
    source = os.path.join(workdir, f"input{run_index}.dhav")
    with open(source, "wb") as handle:
        handle.write(stream)
    subprocess.run(
        [*DHAV2MKV, "-i", source, "-o", target],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=300,
        check=True,
    )
    with open(target, "rb") as handle:
        outputs.append(handle.read())

check(len(outputs[0]) > 0, "dhav2mkv writes an MKV file on OHOS")
check(
    outputs[0] == outputs[1],
    "repeated OHOS conversions are byte-identical (stable musl behaviour)",
)
check(
    outputs[0].startswith(b"\x1a\x45\xdf\xa3"),
    "the OHOS-produced Matroska output carries the EBML header",
)

print(f"test_ohos_platform.py: {len(passed)} assertions passed")
