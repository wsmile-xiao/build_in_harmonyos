#!/usr/bin/env python3
"""HarmonyOS-specific checks on the packaged leaf ELF binary.

These verify that the artefact actually matches what the HarmonyOS PC (aarch64)
runtime requires, which is the part a generic POSIX build cannot guarantee:

  B1  ELF ``e_machine`` is AArch64 (0xB7) — the only arch HarmonyOS PC runs.
  B2  HarmonyOS code signature is present (ELF section ``.codesign``) — an
      unsigned ELF is refused by the HarmonyOS runtime when launched as an app
      component, and this repository signs every shipped binary.
  B3  Program interpreter and ``DT_NEEDED`` entries resolve to OHOS-native
      runtime components (musl ``ld-musl-aarch64.so.1`` / ``libc.so``), i.e. the
      binary is not linked against glibc.

The ELF is parsed directly so the check needs no external binutils.

Usage: ohos_elf_check.py <path-to-elf>
Exit code 0 = all checks passed, 1 = at least one check failed.
"""

import struct
import sys

EM_AARCH64 = 0xB7
DT_NEEDED = 1
DT_STRTAB = 5
DT_SONAME = 14

FAILED = []


def report(ok, name, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok:
        FAILED.append(name)


def read_sections(data):
    """Return list of dicts describing the ELF section headers."""
    (e_shoff,) = struct.unpack_from("<Q", data, 0x28)
    (e_shentsize,) = struct.unpack_from("<H", data, 0x3A)
    (e_shnum,) = struct.unpack_from("<H", data, 0x3C)
    (e_shstrndx,) = struct.unpack_from("<H", data, 0x3E)

    raw = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        name_off, sh_type = struct.unpack_from("<II", data, off)
        sh_offset, sh_size = struct.unpack_from("<QQ", data, off + 0x18)
        sh_link, _ = struct.unpack_from("<II", data, off + 0x28)
        raw.append(
            {
                "name_off": name_off,
                "type": sh_type,
                "offset": sh_offset,
                "size": sh_size,
                "link": sh_link,
            }
        )

    strtab_off = raw[e_shstrndx]["offset"]
    for sec in raw:
        end = data.index(b"\x00", strtab_off + sec["name_off"])
        sec["name"] = data[strtab_off + sec["name_off"]:end].decode("utf-8", "replace")
    return raw


def cstring(data, off):
    end = data.index(b"\x00", off)
    return data[off:end].decode("utf-8", "replace")


def dynamic_needed(data, sections):
    """Extract DT_NEEDED / DT_SONAME strings via the .dynamic section."""
    dyn = next((s for s in sections if s["name"] == ".dynamic"), None)
    if dyn is None:
        return []
    # .dynamic's sh_link points at the dynamic string table (.dynstr).
    strtab = sections[dyn["link"]]
    entries = []
    for off in range(dyn["offset"], dyn["offset"] + dyn["size"], 16):
        (tag, val) = struct.unpack_from("<QQ", data, off)
        if tag in (DT_NEEDED, DT_SONAME):
            entries.append((tag, cstring(data, strtab["offset"] + val)))
    return entries


def main():
    if len(sys.argv) != 2:
        print("usage: ohos_elf_check.py <path-to-elf>", file=sys.stderr)
        return 2

    path = sys.argv[1]
    data = open(path, "rb").read()
    name = "leaf-md OHOS ELF"

    if data[:4] != b"\x7fELF":
        report(False, "B1 AArch64 ELF machine", "not an ELF file")
        return 1

    (machine,) = struct.unpack_from("<H", data, 18)
    report(
        machine == EM_AARCH64,
        "B1 AArch64 ELF machine",
        f"e_machine=0x{machine:x}" + ("" if machine == EM_AARCH64 else " (expected 0xb7)"),
    )

    sections = read_sections(data)
    names = {s["name"] for s in sections}
    report(
        ".codesign" in names,
        "B2 HarmonyOS ELF code signature",
        "section .codesign present" if ".codesign" in names else "no .codesign section (unsigned)",
    )

    interp = next((s for s in sections if s["name"] == ".interp"), None)
    interp_str = cstring(data, interp["offset"]) if interp else "<none>"
    needed = [v for tag, v in dynamic_needed(data, sections) if tag == DT_NEEDED]
    glibc = [lib for lib in needed if lib.endswith(".so.6") or "glibc" in lib]
    ok_interp = "musl" in interp_str or "ohos" in interp_str.lower() or interp is None
    report(
        ok_interp and not glibc,
        "B3 OHOS-native runtime linkage",
        f"interpreter={interp_str}, DT_NEEDED={needed or '<static>'}"
        + (f", glibc-like entries={glibc}" if glibc else ""),
    )

    if FAILED:
        print(f"OHOS-specific checks failed: {', '.join(FAILED)}")
        return 1
    print("OHOS-specific checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
