#!/usr/bin/env python3
"""Functional tests for the packaged `dhav2mkv` recording converter.

    test_dhav2mkv.py --dhav2mkv <dhav2mkv command> --tanidvr <tanidvr command>

The DHAV stream built here follows the framing implemented by
src/mctools.c: the "DHAV" magic, the 4 byte little endian frame length at
offset 12, the extended header length at offset 22, the trailing "dhav" plus
length footer, and the 4 byte sub-field groups ([id, s0, s1, s2]) from
which the tool reads width (sub-field 0x80/2), height (0x80/3) and frame rate
(0x81/3). The conversion exercised below is the real upstream code path.
"""

import os
import struct
import subprocess
import sys
import tempfile

# The Matroska header emitted by src/mctools.c stores the frame geometry as
# big endian uint16 at these fixed offsets (MKV_HOFF_PixelWidth/Height).
MKV_OFFSET_PIXEL_WIDTH = 0x16E + 2
MKV_OFFSET_PIXEL_HEIGHT = 0x172 + 2
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 25
# extended header: field 0x80 -> [0x80, -, width/8, height/8],
#                   field 0x81 -> [0x81, -, -, frame rate]
EXTENDED_HEADER = bytes(
    [0x80, 0x00, FRAME_WIDTH // 8, FRAME_HEIGHT // 8, 0x81, 0x00, 0x00, FRAME_RATE]
)


def split_commands(argv):
    """Split "--dhav2mkv <tokens...> --tanidvr <tokens...>" without argparse.

    argparse.REMAINDER would swallow the second marker, and plain argparse
    would reject emulator flags such as "-L" inside a command prefix.
    """
    commands = {}
    key = None
    for token in argv:
        if token in ("--dhav2mkv", "--tanidvr"):
            key = token[2:]
            commands[key] = []
        elif key is not None:
            commands[key].append(token)
    return commands


COMMANDS = split_commands(sys.argv[1:])
DHAV2MKV = COMMANDS.get("dhav2mkv", [])
TANIDVR = COMMANDS.get("tanidvr", [])
if not DHAV2MKV or not TANIDVR:
    sys.exit("usage: test_dhav2mkv.py --dhav2mkv <cmd> --tanidvr <cmd>")

EBML_MAGIC = b"\x1a\x45\xdf\xa3"
CLUSTER_ID = b"\x1f\x43\xb6\x75"

passed = []


def check(condition, message):
    if not condition:
        print(f"FAIL: {message}")
        sys.exit(1)
    passed.append(message)
    print(f"ok: {message}")


def run(command, *args, stdin=None):
    return subprocess.run(
        [*command, *args],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )


def nal(nal_type, payload):
    return b"\x00\x00\x00\x01" + bytes([nal_type]) + payload


def dhav_frame(frame_type, timestamp, epoch, body):
    """Build one DHAV frame: 24 byte header + extended header + body + footer."""
    header = bytearray(24)
    header[0:4] = b"DHAV"
    header[4] = frame_type
    struct.pack_into("<I", header, 16, epoch)
    struct.pack_into("<H", header, 20, timestamp)
    header[22] = len(EXTENDED_HEADER)
    total = 24 + len(EXTENDED_HEADER) + len(body) + 8
    struct.pack_into("<I", header, 12, total)
    return (
        bytes(header)
        + EXTENDED_HEADER
        + body
        + b"dhav"
        + struct.pack("<I", total)
    )


def sample_stream():
    sps = nal(0x67, bytes([0x42, 0x00, 0x1E, 0xE9, 0x02, 0x83, 0xF4, 0x00, 0x00]))
    pps = nal(0x68, bytes([0xCE, 0x38, 0x80]))
    key_frame = nal(0x65, bytes([0x88, 0x84, 0x00, 0x33, 0xFF]) + b"\xAB" * 200)
    delta_frame = nal(0x41, bytes([0x9A]) + b"\xCD" * 120)
    epoch = 1700000000
    return (
        dhav_frame(0xFD, 0, epoch, sps + pps + key_frame)
        + dhav_frame(0xFC, 40, epoch, delta_frame)
        + dhav_frame(0xFC, 80, epoch, delta_frame)
    )


workdir = tempfile.mkdtemp(prefix="tanidvr-dhav2mkv-")
source = os.path.join(workdir, "recording.dhav")
target = os.path.join(workdir, "recording.mkv")
stream = sample_stream()
with open(source, "wb") as handle:
    handle.write(stream)

help_result = run(DHAV2MKV, "-h")
help_text = help_result.stdout.decode("utf-8", "replace")
check(help_result.returncode == 0, "dhav2mkv -h exits with 0")
check("dhav2mkv 1.4.1" in help_text, "dhav2mkv -h reports the packaged version")
check(
    "Usage: dhav2mkv [-i <input DHAV file>]" in help_text,
    "dhav2mkv -h prints the upstream usage synopsis",
)

convert = run(DHAV2MKV, "-i", source, "-o", target)
convert_log = convert.stderr.decode("utf-8", "replace")
check(convert.returncode == 0, "dhav2mkv converts a DHAV recording successfully")
check(
    "Media container: DHAV" in convert_log,
    "dhav2mkv identifies the DHAV container format",
)

check(os.path.isfile(target), "dhav2mkv creates the requested output file")
with open(target, "rb") as handle:
    mkv = handle.read()

check(len(mkv) > 0, "dhav2mkv produces a non-empty Matroska file")
check(mkv.startswith(EBML_MAGIC), "the output starts with the EBML magic")
check(b"matroska" in mkv, "the output declares the matroska DocType")
check(
    b"V_MPEG4/ISO/AVC" in mkv,
    "the output advertises the AVC codec of the DHAV frames",
)
pixel_width = struct.unpack_from(">H", mkv, MKV_OFFSET_PIXEL_WIDTH)[0]
pixel_height = struct.unpack_from(">H", mkv, MKV_OFFSET_PIXEL_HEIGHT)[0]
check(
    pixel_width == FRAME_WIDTH,
    f"the output carries the DHAV frame width ({pixel_width} == {FRAME_WIDTH})",
)
check(
    pixel_height == FRAME_HEIGHT,
    f"the output carries the DHAV frame height ({pixel_height} == {FRAME_HEIGHT})",
)
check(
    b"\xAB" * 200 in mkv and b"\xCD" * 120 in mkv,
    "the converted payload keeps the H.264 NAL bodies of every frame",
)
check(
    mkv.count(CLUSTER_ID) == 3,
    "the output contains one Matroska cluster per converted DHAV frame",
)

piped = run(DHAV2MKV, stdin=stream)
check(piped.returncode == 0, "dhav2mkv converts through stdin/stdout")
check(
    piped.stdout == mkv,
    "stdin/stdout conversion is byte-identical to the file based one",
)

rejected = run(DHAV2MKV, "-r", "5", "-i", source, "-o", target)
rejected_log = rejected.stderr.decode("utf-8", "replace")
check(rejected.returncode != 0, "dhav2mkv rejects an out-of-range -r value")
check("Invalid tsproc type." in rejected_log, "dhav2mkv validates -r")

missing_arg = run(DHAV2MKV, "-i")
missing_arg_log = missing_arg.stderr.decode("utf-8", "replace")
check(missing_arg.returncode != 0, "dhav2mkv requires an argument for -i")
check(
    "option requires an argument" in missing_arg_log,
    "dhav2mkv reports the missing -i argument",
)

absent = os.path.join(workdir, "absent.dhav")
missing_file = run(DHAV2MKV, "-i", absent, "-o", target)
missing_file_log = missing_file.stderr.decode("utf-8", "replace")
check(
    "Unable to read DHAV stream data." in missing_file_log,
    "dhav2mkv reports an unreadable input stream",
)

garbage_source = os.path.join(workdir, "garbage.bin")
with open(garbage_source, "wb") as handle:
    handle.write(b"\x11" * 50000)
garbage_target = os.path.join(workdir, "garbage.mkv")
garbage = run(DHAV2MKV, "-i", garbage_source, "-o", garbage_target)
garbage_log = garbage.stderr.decode("utf-8", "replace")
check(
    "Unable to identify media container format" in garbage_log,
    "dhav2mkv reports an unidentifiable media container",
)
check(
    "No DHAV header. Skipping garbage..." in garbage_log,
    "dhav2mkv skips input without a DHAV header",
)
check(
    os.path.getsize(garbage_target) == 0,
    "dhav2mkv writes no Matroska data for an unusable stream",
)

sibling_help = run(TANIDVR, "-h").stdout.decode("utf-8", "replace")
check(
    "TaniDVR 1.4.1" in sibling_help,
    "the tanidvr client shipped by the same package reports the same version",
)

print(f"test_dhav2mkv.py: {len(passed)} assertions passed")
