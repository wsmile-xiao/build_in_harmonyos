#!/usr/bin/env python3
"""Exercise mtoc with a deterministic ARM64 Mach-O input fixture."""

import shlex
import shutil
import struct
import subprocess
import sys
from pathlib import Path


MH_MAGIC_64 = 0xFEEDFACF
CPU_TYPE_ARM64 = 0x0100000C
MH_PRELOAD = 5
LC_SEGMENT_64 = 0x19
LC_SYMTAB = 0x02
VM_PROT_READ = 0x01
VM_PROT_EXECUTE = 0x04
PE_MACHINE_ARM64 = 0xAA64
PE32_PLUS_MAGIC = 0x020B
EFI_APPLICATION_SUBSYSTEM = 10
ARM64_RET = b"\xc0\x03\x5f\xd6"
EXPECTED_ASSERTIONS = 18
assertion_count = 0


def require(condition, description):
    global assertion_count
    assertion_count += 1
    if not condition:
        print(f"[FAIL] {description}", file=sys.stderr, flush=True)
        raise AssertionError(description)
    print(f"[PASS] {description}", flush=True)


def run_command(command):
    print(f"[RUN] {shlex.join(command)}", flush=True)
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        print("[EXIT] TIMEOUT")
        print("[STDOUT]")
        print((error.stdout or "").rstrip() or "<empty>")
        print("[STDERR]")
        print((error.stderr or "").rstrip() or "<empty>")
        raise RuntimeError(f"command timed out after 30 seconds: {command[0]}") from error
    print(f"[EXIT] {result.returncode}")
    print("[STDOUT]")
    print(result.stdout.rstrip() or "<empty>")
    print("[STDERR]")
    print(result.stderr.rstrip() or "<empty>")
    return result


def write_macho_fixture(output_path):
    text_offset = 0x1000
    text_size = 0x200
    string_offset = text_offset + text_size

    segment = struct.pack(
        "<II16sQQQQiiII",
        LC_SEGMENT_64,
        72,
        b"__TEXT\0".ljust(16, b"\0"),
        0x1000,
        text_size,
        text_offset,
        text_size,
        VM_PROT_READ | VM_PROT_EXECUTE,
        VM_PROT_READ | VM_PROT_EXECUTE,
        0,
        0,
    )
    symtab = struct.pack(
        "<IIIIII",
        LC_SYMTAB,
        24,
        string_offset,
        0,
        string_offset,
        4,
    )
    header = struct.pack(
        "<IiiIIIII",
        MH_MAGIC_64,
        CPU_TYPE_ARM64,
        0,
        MH_PRELOAD,
        2,
        len(segment) + len(symtab),
        0,
        0,
    )

    image = bytearray(header + segment + symtab)
    image.extend(b"\0" * (text_offset - len(image)))
    image.extend(ARM64_RET)
    image.extend(b"\0" * (text_size - len(ARM64_RET)))
    image.extend(b"\0" * 4)
    output_path.write_bytes(image)


def validate_pecoff(output_path):
    image = output_path.read_bytes()
    require(
        len(image) >= 0x200,
        f"PE/COFF output is at least 512 bytes (actual {len(image)})",
    )
    require(image[:2] == b"MZ", "DOS MZ signature is present")

    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    require(pe_offset == 0x80, f"PE header offset is 0x80 (actual {pe_offset:#x})")
    require(image[pe_offset:pe_offset + 4] == b"PE\0\0", "PE signature is present")

    machine = struct.unpack_from("<H", image, pe_offset + 4)[0]
    section_count = struct.unpack_from("<H", image, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe_offset + 20)[0]
    optional_offset = pe_offset + 24
    require(
        machine == PE_MACHINE_ARM64,
        f"PE machine is AArch64 (actual {machine:#06x})",
    )
    require(section_count == 1, f"PE contains one section (actual {section_count})")
    require(
        optional_size >= 70,
        f"PE optional header is at least 70 bytes (actual {optional_size})",
    )

    optional_magic = struct.unpack_from("<H", image, optional_offset)[0]
    subsystem = struct.unpack_from("<H", image, optional_offset + 68)[0]
    require(
        optional_magic == PE32_PLUS_MAGIC,
        f"optional header identifies PE32+ (actual {optional_magic:#06x})",
    )
    require(
        subsystem == EFI_APPLICATION_SUBSYSTEM,
        f"PE subsystem is EFI application (actual {subsystem})",
    )

    section_offset = optional_offset + optional_size
    section_name = image[section_offset:section_offset + 8].rstrip(b"\0")
    raw_size = struct.unpack_from("<I", image, section_offset + 16)[0]
    raw_offset = struct.unpack_from("<I", image, section_offset + 20)[0]
    require(section_name == b".text", f"first PE section is .text (actual {section_name!r})")
    require(
        raw_size >= len(ARM64_RET),
        f".text raw data holds the ARM64 instruction (actual {raw_size} bytes)",
    )
    require(
        image[raw_offset:raw_offset + len(ARM64_RET)] == ARM64_RET,
        "ARM64 instruction bytes are preserved",
    )


def main():
    print("[STEP 1/5] Validating arguments and packaged executable")
    require(len(sys.argv) == 3, "received MTOC and WORK_FOLDER arguments")
    mtoc = Path(sys.argv[1])
    work_folder = Path(sys.argv[2])
    require(mtoc.is_file(), f"packaged mtoc executable exists at {mtoc}")

    print("[STEP 2/5] Preparing deterministic ARM64 Mach-O fixture")
    shutil.rmtree(work_folder, ignore_errors=True)
    work_folder.mkdir(parents=True)
    macho_path = work_folder / "minimal-arm64.macho"
    pecoff_path = work_folder / "minimal-arm64.efi"
    write_macho_fixture(macho_path)

    print("[STEP 3/5] Converting Mach-O to PE/COFF")
    conversion = run_command(
        [str(mtoc), str(macho_path), str(pecoff_path)]
    )
    require(
        conversion.returncode == 0,
        f"mtoc conversion exits with status 0 (actual {conversion.returncode})",
    )
    require(pecoff_path.is_file(), f"mtoc creates PE/COFF output at {pecoff_path}")

    print("[STEP 4/5] Validating AArch64 EFI PE32+ structure")
    validate_pecoff(pecoff_path)

    print("[STEP 5/5] Verifying the missing-argument error path")
    usage = run_command([str(mtoc)])
    usage_text = usage.stdout + usage.stderr
    require(
        usage.returncode != 0,
        f"mtoc without arguments returns a failure status (actual {usage.returncode})",
    )
    require("Usage:" in usage_text, "mtoc without arguments prints Usage text")

    if assertion_count != EXPECTED_ASSERTIONS:
        raise AssertionError(
            f"assertion count drifted: expected {EXPECTED_ASSERTIONS}, got {assertion_count}"
        )
    print(
        "PASS: mtoc converted ARM64 Mach-O to AArch64 EFI PE32+ "
        f"({assertion_count} assertions)"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"[FAIL] mtoc functional test: {error}", file=sys.stderr)
        sys.exit(1)
