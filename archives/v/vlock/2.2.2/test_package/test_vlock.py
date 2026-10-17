#!/usr/bin/env python3
"""Consumer-side tests for the vlock/2.2.2 Conan package.

Invoked by test_package/conanfile.py as:

    python3 test_vlock.py <package_folder>

Cases marked [OHOS] assert HarmonyOS platform properties (architecture, musl
loader, on-device execution); they are the HarmonyOS-specific test cases of
this package.
"""
import os
import shutil
import struct
import subprocess
import sys

PT_INTERP = 3
SHT_STRTAB = 3
SHT_DYNAMIC = 6
DT_NEEDED = 1
EM_AARCH64 = 183

CASES = []


def case(name, ok, detail=""):
    CASES.append((name, bool(ok), detail))
    print(f"  Test: {name} ...{'passed' if ok else 'FAILED'}")
    if not ok:
        print(f"     detail: {detail}")


def read_elf(path):
    """Minimal ELF64 reader -> (class, encoding, machine, interp, needed)."""
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    elf_class, data = blob[4], blob[5]
    endian = "<" if data == 1 else ">"
    (_, _e_type, machine, _version, _entry, phoff, shoff, _flags,
     _ehsize, phentsize, phnum, shentsize, shnum, shstrndx) = struct.unpack_from(
        endian + "16sHHIQQQIHHHHHH", blob, 0)

    interp = None
    for index in range(phnum):
        off = phoff + index * phentsize
        p_type = struct.unpack_from(endian + "I", blob, off)[0]
        if p_type == PT_INTERP:
            p_offset, p_filesz = struct.unpack_from(endian + "QQ", blob, off + 8)
            interp = blob[p_offset:p_offset + p_filesz].split(b"\0")[0].decode()

    sections = []
    for index in range(shnum):
        off = shoff + index * shentsize
        sections.append(struct.unpack_from(endian + "IIQQQQIIQQ", blob, off))

    needed = []
    for section in sections:
        if section[1] != SHT_DYNAMIC:
            continue
        str_index = section[6]                      # sh_link -> string table
        if str_index >= len(sections) or sections[str_index][1] != SHT_STRTAB:
            continue
        str_off = sections[str_index][4]
        entry = section[4]
        while entry < section[4] + section[5]:
            tag, val = struct.unpack_from(endian + "qQ", blob, entry)
            if tag == 0:
                break
            if tag == DT_NEEDED:
                end = blob.index(b"\0", str_off + val)
                needed.append(blob[str_off + val:end].decode())
            entry += 16
    return elf_class, data, machine, interp, needed


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True)


def main():
    pkg = sys.argv[1]
    bindir = os.path.join(pkg, "bin")
    sbindir = os.path.join(pkg, "sbin")
    moduledir = os.path.join(pkg, "lib", "vlock", "modules")
    sh = shutil.which("sh") or "/bin/sh"
    vlock = os.path.join(bindir, "vlock")
    vlock_main = os.path.join(sbindir, "vlock-main")

    # ── TC-01 packaging layout ────────────────────────────────────────────
    expected = [vlock, vlock_main,
                os.path.join(pkg, "share", "man", "man8", "vlock-main.8")]
    missing = [p for p in expected if not os.path.isfile(p)]
    case("TC-01-packaging-layout", not missing, f"missing artifacts: {missing}")

    # ── TC-02 --version ───────────────────────────────────────────────────
    result = run([sh, vlock, "--version"])
    out = result.stdout + result.stderr
    case("TC-02-version",
         result.returncode == 0 and "vlock version 2.2.2" in out,
         f"rc={result.returncode} out={out!r}")

    # ── TC-03 --help ──────────────────────────────────────────────────────
    result = run([sh, vlock, "--help"])
    out = result.stdout + result.stderr
    case("TC-03-help",
         result.returncode == 0 and "Usage: vlock" in out and "--current" in out,
         f"rc={result.returncode} out={out[:200]!r}")

    # ── TC-04 invalid option rejected ────────────────────────────────────
    result = run([sh, vlock, "--definitely-not-an-option"])
    out = result.stdout + result.stderr
    case("TC-04-invalid-option-rejected",
         result.returncode != 0 and "Usage: vlock" in out,
         f"rc={result.returncode} out={out[:200]!r}")

    # ── TC-05 plugin modules built ────────────────────────────────────────
    modules = ["all.so", "new.so", "nosysrq.so"]
    present = [m for m in modules if os.path.isfile(os.path.join(moduledir, m))]
    case("TC-05-plugin-modules", present == modules,
         f"expected {modules}, found {present}")

    # ── TC-06 [OHOS] ELF target of vlock-main ────────────────────────────
    try:
        elf_class, data, machine, interp, needed = read_elf(vlock_main)
        ok = (elf_class == 2 and data == 1 and machine == EM_AARCH64
              and interp == "/lib/ld-musl-aarch64.so.1")
        detail = (f"class={elf_class} data={data} machine={machine} "
                  f"interp={interp!r} needed={needed}")
    except Exception as exc:                                   # noqa: BLE001
        needed, ok, detail = [], False, f"ELF parse failed: {exc!r}"
    case("TC-06-ohos-elf-abi", ok, detail)

    # ── TC-07 [OHOS] PAM dependency chain resolution ─────────────────────
    libpath = [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
    resolved = [lib for lib in needed
                if any(os.path.isfile(os.path.join(d, lib)) for d in libpath)]
    case("TC-07-ohos-pam-closure",
         "libpam.so.0" in needed and "libpam.so.0" in resolved,
         f"needed={needed} resolved={resolved} LD_LIBRARY_PATH={libpath}")

    # ── TC-08 [OHOS] on-device execution ─────────────────────────────────
    sysname = os.uname().sysname
    result = run([sh, vlock, "-v"])
    case("TC-08-ohos-on-device-run",
         "HarmonyOS" in sysname and result.returncode == 0,
         f"sysname={sysname!r} rc={result.returncode} "
         f"out={(result.stdout + result.stderr)!r}")

    passed = sum(1 for _n, ok, _d in CASES if ok)
    failed = len(CASES) - passed
    print(f" CASE SUMMARY: total={len(CASES)} passed={passed} failed={failed} skipped=0")
    print(" RESULT: " + ("PASS" if failed == 0 else "FAIL"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
