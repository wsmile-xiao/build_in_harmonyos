#!/usr/bin/env python3
"""OHOS adaptation gate test for the packaged klevernotes 1.3.1.

New OHOS-specific test (build_in_harmonyos port, not an upstream case): it
asserts, directly on the packaged ELF, that the platform adaptations this
port introduces actually took effect in the shipped artifact:

  1. The binary is an AArch64 ELF for the OHOS target (musl libc marker).
  2. The KLEVER_WITH_WEBENGINE=OFF degradation is real: the binary records
     NO dynamic dependency on QtWebEngine, QtWebChannel, QtPrintSupport or
     Qt6Pdf (the WebEngine preview / PDF printing pipeline is gone).
  3. The QML application closure is linked: libQt6Qml/libQt6Quick are in
     NEEDED, and the KF6 storage helper closure (libKF6KIOCore, used by
     KleverUtility::KIO::encodeFileName) survived linking.

Pure stdlib: a minimal ELF64 parser extracts the PT_DYNAMIC DT_NEEDED
strings, so the gate does not depend on readelf being on the CI PATH
(kio 6.14.0 precedent: readelf can be absent).

Usage: test_ohos_gate.py <path-to-packaged-klevernotes-binary>
Exit code 0 = gate passed, 1 = gate failed.
"""
import struct
import sys

DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
PT_LOAD = 1
PT_DYNAMIC = 2
EM_AARCH64 = 183

DENY_SUBSTRINGS = ("WebEngine", "WebChannel", "PrintSupport", "Qt6Pdf")
REQUIRED_NEEDED = (
    "libQt6Core.so.6",
    "libQt6Qml.so.6",
    "libQt6Quick.so.6",
    "libKF6KIOCore.so.6",
    "libc.so",
)


class GateError(Exception):
    pass


def parse_elf_needed(data):
    if data[:4] != b"\x7fELF":
        raise GateError("not an ELF file")
    if data[4] != 2:
        raise GateError("expected ELFCLASS64")
    if data[5] != 1:
        raise GateError("expected little-endian ELF")

    e_type, e_machine = struct.unpack_from("<HH", data, 0x10)
    (e_phoff,) = struct.unpack_from("<Q", data, 0x20)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
    if e_machine != EM_AARCH64:
        raise GateError(f"expected EM_AARCH64 (183), got {e_machine}")

    loads = []
    dynamic = None
    for i in range(e_phnum):
        base = e_phoff + i * e_phentsize
        p_type, p_flags = struct.unpack_from("<II", data, base)
        p_offset, p_vaddr = struct.unpack_from("<QQ", data, base + 0x08)
        p_filesz = struct.unpack_from("<Q", data, base + 0x20)[0]
        if p_type == PT_LOAD:
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == PT_DYNAMIC:
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        raise GateError("no PT_DYNAMIC segment")

    def vaddr_to_offset(vaddr):
        for p_vaddr, p_offset, p_filesz in loads:
            if p_vaddr <= vaddr < p_vaddr + p_filesz:
                return vaddr - p_vaddr + p_offset
        raise GateError(f"vaddr {vaddr:#x} not covered by PT_LOAD")

    d_offset, d_size = dynamic
    needed_indices = []
    strtab_vaddr = None
    strsz = None
    for entry in range(d_offset, d_offset + d_size, 16):
        d_tag, d_un = struct.unpack_from("<qQ", data, entry)
        if d_tag == 0:
            break
        if d_tag == DT_NEEDED:
            needed_indices.append(d_un)
        elif d_tag == DT_STRTAB:
            strtab_vaddr = d_un
        elif d_tag == DT_STRSZ:
            strsz = d_un
    if strtab_vaddr is None or strsz is None:
        raise GateError("DT_STRTAB/DT_STRSZ missing")

    strtab = data[vaddr_to_offset(strtab_vaddr): vaddr_to_offset(strtab_vaddr) + strsz]
    return e_type, [strtab[i: strtab.index(b"\x00", i)].decode("utf-8", "replace") for i in needed_indices]


def main(argv):
    if len(argv) != 2:
        print("usage: test_ohos_gate.py <klevernotes-binary>")
        return 2
    with open(argv[1], "rb") as fh:
        data = fh.read()

    failures = []
    warnings = []

    try:
        e_type, needed = parse_elf_needed(data)
    except GateError as exc:
        print(f"OHOS_GATE_FAIL: ELF parse error: {exc}")
        return 1

    print(f"info: ELF type={e_type} (2=EXEC, 3=DYN/PIE), {len(needed)} DT_NEEDED entries")

    if e_type not in (2, 3):
        failures.append(f"unexpected ELF type {e_type}")
    if e_type == 2:
        warnings.append("binary is ET_EXEC (not PIE); OHOS apps are normally ET_DYN")

    if b".codesign" not in data:
        warnings.append("no .codesign section found (packaging should have re-signed the ELF)")

    for entry in needed:
        for deny in DENY_SUBSTRINGS:
            if deny in entry:
                failures.append(
                    f"WebEngine-gate leak: NEEDED '{entry}' matches '{deny}' "
                    "(KLEVER_WITH_WEBENGINE=OFF must drop the WebEngine/Pdf/WebChannel/"
                    "PrintSupport pipeline)"
                )
    for required in REQUIRED_NEEDED:
        if not any(entry == required for entry in needed):
            failures.append(f"missing required NEEDED '{required}'")

    print("info: NEEDED entries:")
    for entry in sorted(needed):
        print(f"      {entry}")

    for warning in warnings:
        print(f"OHOS_GATE_WARN: {warning}")
    if failures:
        for failure in failures:
            print(f"OHOS_GATE_FAIL: {failure}")
        return 1
    print(
        "OHOS_GATE_PASS: AArch64 OHOS ELF; WebEngine/Pdf/WebChannel/PrintSupport "
        "pipeline absent; QML + KIO closure linked"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
