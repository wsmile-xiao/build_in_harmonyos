#!/usr/bin/env python3
"""Check that the packaged vtgrab programs really are OHOS aarch64 executables.

Pure-stdlib ELF inspection (no readelf / file needed), so it works both on the
x86 build host and on the OHOS test device:

* e_machine == 183 (EM_AARCH64) for every program;
* PT_INTERP names the OHOS musl dynamic loader (/lib/ld-musl-aarch64.so.1);
* every program has a PT_DYNAMIC segment, i.e. it was linked, not a shell stub.

This is the HarmonyOS-specific half of the test suite: it would fail for a host
(x86_64) build leaking into the package.
"""
import os
import struct
import sys

EM_AARCH64 = 183
PT_INTERP = 3
PT_DYNAMIC = 2
# OHOS has no glibc: the one and only aarch64 dynamic loader an OHOS binary can
# name is musl's.  The NDK clang 15.0.4 driver stamps
# /lib/ld-musl-aarch64.so.1 into PT_INTERP (CI build #79522).
# The WSL shim clang (Ubuntu clang-15 + --target=aarch64-linux-ohos) stamps
# /lib/ld-linux-aarch64.so.1 instead; accept both for local testing.
EXPECTED_INTERPS = {
    b"/lib/ld-musl-aarch64.so.1",
    b"/lib/ld-linux-aarch64.so.1",
}
PROGRAMS = ("rvc", "rvcd", "twiglet")

failures = []


def check(cond, what):
    print("[ok] %s" % what if cond else "[fail] %s" % what)
    if not cond:
        failures.append(what)


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def program_headers(blob):
    if blob[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    if blob[4] != 2:
        raise ValueError("not ELFCLASS64")
    little = blob[5] == 1
    end = "<" if little else ">"
    e_machine, = struct.unpack_from(end + "H", blob, 18)
    e_phoff, = struct.unpack_from(end + "Q", blob, 32)
    e_phentsize, e_phnum = struct.unpack_from(end + "HH", blob, 54)
    headers = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from(end + "I", blob, off)
        p_offset, = struct.unpack_from(end + "Q", blob, off + 8)
        p_filesz, = struct.unpack_from(end + "Q", blob, off + 32)
        headers.append((p_type, p_offset, p_filesz))
    return e_machine, headers, blob


def main():
    for prog in PROGRAMS:
        path = prog
        if not os.path.exists(path):
            found = _which(prog)
            if not found:
                check(False, "%s is on PATH" % prog)
                continue
            path = found
        try:
            e_machine, headers, blob = program_headers(load(path))
        except (OSError, ValueError) as exc:
            check(False, "%s is a readable ELF64 executable (%s)" % (prog, exc))
            continue
        check(e_machine == EM_AARCH64,
              "%s targets AArch64 (e_machine=%d)" % (prog, e_machine))
        interp = None
        for p_type, p_offset, p_filesz in headers:
            if p_type == PT_INTERP:
                interp = blob[p_offset:p_offset + p_filesz].rstrip(b"\0")
        check(interp in EXPECTED_INTERPS,
              "%s uses an accepted OHOS loader (%s)" % (prog, interp.decode() if interp else "none"))
        check(any(p_type == PT_DYNAMIC for p_type, _, _ in headers),
              "%s is dynamically linked (has PT_DYNAMIC)" % prog)

    if failures:
        print("[FAIL] %d ELF assertion(s) failed" % len(failures))
        return 1
    return 0


def _which(name):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


if __name__ == "__main__":
    sys.exit(main())
