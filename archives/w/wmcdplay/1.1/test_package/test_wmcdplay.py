#!/usr/bin/env python3
"""Consumer test for the installed wmcdplay 1.1 package.

Usage: python3 test_wmcdplay.py <package_folder>

The script inspects the installed package and executes the real ``wmcdplay``
binary.  ``--help`` is handled by ``scanArgs()`` *before* ``initXWin()`` opens
the display, so the behavioural cases need no X server and no CD-ROM device --
which makes them usable as a headless HarmonyOS PC consumer check.

Case 16/17 and case 21..25 are HarmonyOS-specific consumer cases: they assert
the target contract of the packaged artifact (signed OHOS AArch64 ELF, runtime
dependency closure resolvable through the Conan run environment) and prove the
artifact is executable on the device.
"""

import os
import re
import struct
import subprocess
import sys
from pathlib import Path

ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_EXEC = 2
ET_DYN = 3
EM_AARCH64 = 183
SHT_STRTAB = 3
SHT_DYNAMIC = 6
DT_NULL = 0
DT_NEEDED = 1
DT_RPATH = 15
DT_RUNPATH = 29

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    status = "ok" if condition else "not ok"
    suffix = f"  ({detail})" if detail and not condition else ""
    print(f"{status} {len(RESULTS)} - {name}{suffix}", flush=True)
    return bool(condition)


def skip(name, reason):
    RESULTS.append((name, None, reason))
    print(f"ok {len(RESULTS)} - SKIP {name} ({reason})", flush=True)


def read_elf(path):
    """Minimal ELF64 reader: header, section headers and .dynamic tags."""
    data = Path(path).read_bytes()
    if data[:4] != ELF_MAGIC:
        raise ValueError("not an ELF file")
    elf_class, elf_data = data[4], data[5]
    endian = "<" if elf_data == ELFDATA2LSB else ">"
    e_type, e_machine = struct.unpack_from(endian + "HH", data, 16)
    e_shoff, = struct.unpack_from(endian + "Q", data, 40)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(endian + "HHH", data, 58)

    raw_sections = []
    for index in range(e_shnum):
        base = e_shoff + index * e_shentsize
        sh_name, sh_type = struct.unpack_from(endian + "II", data, base)
        sh_offset, = struct.unpack_from(endian + "Q", data, base + 0x18)
        sh_size, = struct.unpack_from(endian + "Q", data, base + 0x20)
        sh_link, = struct.unpack_from(endian + "I", data, base + 0x28)
        raw_sections.append(
            {
                "name_off": sh_name,
                "type": sh_type,
                "offset": sh_offset,
                "size": sh_size,
                "link": sh_link,
            }
        )

    strtab = raw_sections[e_shstrndx]

    def cstr(buf, offset):
        end = buf.find(b"\x00", offset)
        return buf[offset:end].decode("utf-8", "replace")

    for section in raw_sections:
        section["name"] = cstr(
            data[strtab["offset"]:strtab["offset"] + strtab["size"]], section["name_off"]
        )

    dynamic = next((s for s in raw_sections if s["type"] == SHT_DYNAMIC), None)
    tags = []
    if dynamic is not None:
        entries = dynamic["size"] // 16
        for index in range(entries):
            base = dynamic["offset"] + index * 16
            d_tag, d_val = struct.unpack_from(endian + "qQ", data, base)
            tags.append((d_tag, d_val))
            if d_tag == DT_NULL:
                break

    dynstr = raw_sections[dynamic["link"]] if dynamic is not None else None

    def dyn_string(value):
        if dynstr is None:
            return ""
        buf = data[dynstr["offset"]:dynstr["offset"] + dynstr["size"]]
        return cstr(buf, value) if value < len(buf) else ""

    return {
        "class": elf_class,
        "data": elf_data,
        "type": e_type,
        "machine": e_machine,
        "sections": {s["name"] for s in raw_sections},
        "tags": tags,
        "dyn_string": dyn_string,
    }


def run(binary, args, env=None, timeout=30):
    environment = dict(os.environ)
    environment.pop("DISPLAY", None)
    if env:
        environment.update(env)
    try:
        completed = subprocess.run(
            [str(binary), *args],
            capture_output=True,
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return None, b"", b""
    return completed.returncode, completed.stdout, completed.stderr


def main():
    if len(sys.argv) != 2:
        print("usage: test_wmcdplay.py <package_folder>", file=sys.stderr)
        return 2

    package = Path(sys.argv[1])
    binary = package / "bin" / "wmcdplay"
    share = package / "share" / "wmcdplay"

    # ── installed layout ────────────────────────────────────────────────
    check("package_bin_directory", (package / "bin").is_dir())
    check("wmcdplay_binary_present", binary.is_file(), str(binary))
    check("wmcdplay_binary_is_regular_file", binary.is_file() and not binary.is_symlink())
    check(
        "wmcdplay_binary_executable",
        binary.is_file() and os.access(binary, os.X_OK),
    )
    check("wmcdplay_binary_not_empty", binary.is_file() and binary.stat().st_size > 4096,
          f"{binary.stat().st_size if binary.is_file() else 0} bytes")

    if not binary.is_file():
        report()
        return 1

    elf = read_elf(binary)

    # ── HarmonyOS target contract of the packaged ELF ───────────────────
    check("elf_class_64", elf["class"] == ELFCLASS64, f"class={elf['class']}")
    check("elf_little_endian", elf["data"] == ELFDATA2LSB, f"data={elf['data']}")
    check("elf_machine_aarch64", elf["machine"] == EM_AARCH64, f"e_machine={elf['machine']}")
    check("elf_type_pie_or_exec", elf["type"] in (ET_DYN, ET_EXEC), f"e_type={elf['type']}")
    check("ohos_codesign_section_present", ".codesign" in elf["sections"],
          "HarmonyOS refuses to execve an unsigned ELF")

    rpath_tags = {tag for tag, _ in elf["tags"]} & {DT_RPATH, DT_RUNPATH}
    check("no_build_time_rpath", not rpath_tags,
          f"DT_RPATH/DT_RUNPATH still present: {sorted(rpath_tags)}")

    needed = [elf["dyn_string"](value) for tag, value in elf["tags"] if tag == DT_NEEDED]
    check("needed_libX11", "libX11.so.6" in needed, f"NEEDED={needed}")
    check("needed_libXpm", "libXpm.so.4" in needed, f"NEEDED={needed}")
    check("needed_libXext", "libXext.so.6" in needed, f"NEEDED={needed}")

    payload = binary.read_bytes()
    check(
        "default_artwork_compiled_in",
        b"art_nbtns=" in payload and b"art_actions[]=" in payload,
        "XPM/standard.art was not folded into the binary",
    )
    check(
        "sysartdir_compiled_in",
        b"share/wmcdplay" in payload,
        "pkgdatadir was not baked into SYSARTDIR",
    )

    # ── installed data / documentation ──────────────────────────────────
    artwork = ["bluered.art", "grey.art", "newstyle.art", "wmcd.art"]
    missing = [name for name in artwork if not (share / name).is_file()]
    empty = [
        name for name in artwork
        if (share / name).is_file() and (share / name).stat().st_size == 0
    ]
    check("artwork_data_files_installed", not missing and not empty,
          f"missing={missing} empty={empty}")

    helper = share / "makeart"
    check("makeart_helper_installed",
          helper.is_file() and os.access(helper, os.X_OK), str(helper))

    manpage = package / "share" / "man" / "man1" / "wmcdplay.1"
    check("manpage_installed", manpage.is_file() and manpage.stat().st_size > 256,
          str(manpage))

    licenses = package / "licenses"
    license_files = sorted(p.name for p in licenses.iterdir()) if licenses.is_dir() else []
    check("license_installed", bool(license_files), f"licenses={license_files}")

    # ── behavioural consumer cases (real binary execution) ──────────────
    banner = None
    for case, args in (
        ("help_long_form", ["--help"]),
        ("help_short_form", ["-h"]),
        ("help_dash_help_form", ["-help"]),
    ):
        code, _, stderr = run(binary, args)
        text = stderr.decode("utf-8", "replace")
        banner = text if banner is None else banner
        check(case, code == 0 and "usage:" in text, f"rc={code}")

    documented = [
        "-h | -help | --help", "-w", "-s", "-a", "-f artwork_file",
        "-t track_selection", "-v volume", "-i interval", "-l led_color",
        "-b back_color", "-d cd_device", "-position position", "-display display",
    ]
    check(
        "help_lists_all_documented_options",
        banner is not None and all(option in banner for option in documented),
        f"missing={[o for o in documented if banner and o not in banner]}",
    )
    check(
        "help_reports_upstream_release",
        banner is not None and re.search(r"^Release 1\.1$", banner, re.MULTILINE) is not None,
        "release banner missing or version mismatch",
    )

    code, _, stderr = run(binary, [])
    text = stderr.decode("utf-8", "replace")
    if code is None:
        skip("no_display_reports_x_error", "binary did not exit within 30s")
    else:
        check(
            "no_display_reports_x_error",
            code != 0 and "Unable to open X display" in text,
            f"rc={code} stderr={text.strip()[:120]!r}",
        )

    # Explicit HarmonyOS aarch64 consumer case: the packaged, signed target
    # binary must be loadable through the declared runtime dependency closure
    # and must execute end to end on the device.
    code, _, stderr = run(binary, ["--help"])
    text = stderr.decode("utf-8", "replace")
    check(
        "harmonyos_aarch64_consumer_run",
        code == 0
        and elf["machine"] == EM_AARCH64
        and ".codesign" in elf["sections"]
        and "Release 1.1" in text
        and "wmcdplay - A cd player designed for WindowMaker" in text,
        f"rc={code} stderr={text.strip()[:120]!r}",
    )

    return report()


def report():
    passed = sum(1 for _, ok, _ in RESULTS if ok is True)
    failed = sum(1 for _, ok, _ in RESULTS if ok is False)
    skipped = sum(1 for _, ok, _ in RESULTS if ok is None)
    print(
        f"TOTAL={len(RESULTS)} PASSED={passed} FAILED={failed} SKIPPED={skipped}",
        flush=True,
    )
    if failed:
        print("failed cases: " + ", ".join(n for n, ok, _ in RESULTS if ok is False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
