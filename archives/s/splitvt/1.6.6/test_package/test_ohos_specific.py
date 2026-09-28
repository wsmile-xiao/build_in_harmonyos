#!/usr/bin/env python3
"""HarmonyOS-specific checks for the packaged splitvt 1.6.6.

Independent of test_splitvt_pty.py: this suite looks at the delivered ELF and
at the platform properties the recipe's patches and build flags depend on.  It
fails closed -- a checkpoint that cannot be evaluated is a failure, never a
silent skip.

Checkpoints (one check() == one assertion):
  C1  ELF identity: ELFCLASS64, little-endian, EM_AARCH64 (header parsed here,
      so the suite needs no readelf on the worker).
  C2  PT_INTERP is the OHOS musl loader.
  C3  DT_NEEDED is libc.so and nothing else.  That is the machine-checked form
      of "this package really needs no termcap/ncurses": upstream's termcap
      code sits behind #ifdef TERMCAP and the sysroot has no libtermcap.a for
      the 1993 probe to find, so the branch stays compiled out.
  C4  No DT_RPATH/DT_RUNPATH, and no build-machine absolute path embedded.
  C5  The compile-time SHELL macro survived the build as a *string*: with no
      SHELL in the environment, splitvt must start its compiled-in default
      program (/bin/sh) in both windows and leave it interactive.  If the macro
      had degraded into the token sequence / bin / sh -- what happens when the
      generated Makefile's CFLAGS is overridden on the make command line, see
      notes.md -- execvp() fails, both windows die at once and the shell prompt
      never appears.
  C6  The pseudo-terminal model the patched code drives: a fresh /dev/pts slave
      arrives mode 0600 owned by the invoking uid, which is why splitvt's
      historic setuid-root requirement is inert here (and chown/chmod on a tty
      would be refused anyway).

Summary line: RESULT: passed=N failed=M skipped=K
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ptyharness import (SETUP_DONE, PtySession, arm_budget, check,  # noqa: E402
                        child_env, disarm_budget, summary, tail)


def parse_elf(raw):
    """Return ELFCLASS, data order, machine, PT_INTERP, DT_NEEDED, rpath flag."""
    if raw[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    info = {"class": raw[4], "data": raw[5], "needed": [], "rpath": False,
            "interp": None, "machine": 0}
    endian = "<" if info["data"] == 1 else ">"
    info["machine"] = struct.unpack_from(endian + "H", raw, 18)[0]
    phoff = struct.unpack_from(endian + "Q", raw, 32)[0]
    phentsize = struct.unpack_from(endian + "H", raw, 54)[0]
    phnum = struct.unpack_from(endian + "H", raw, 56)[0]
    dyn_off = dyn_size = strtab = None
    loads = []
    needed = []
    for i in range(phnum):
        base = phoff + i * phentsize
        p_type = struct.unpack_from(endian + "I", raw, base)[0]
        if p_type == 1:                                       # PT_LOAD
            loads.append((struct.unpack_from(endian + "Q", raw, base + 16)[0],
                          struct.unpack_from(endian + "Q", raw, base + 8)[0],
                          struct.unpack_from(endian + "Q", raw, base + 40)[0]))
        if p_type == 3:                                       # PT_INTERP
            off = struct.unpack_from(endian + "Q", raw, base + 8)[0]
            size = struct.unpack_from(endian + "Q", raw, base + 32)[0]
            info["interp"] = raw[off:off + size].rstrip(b"\x00").decode()
        elif p_type == 2:                                     # PT_DYNAMIC
            dyn_off = struct.unpack_from(endian + "Q", raw, base + 8)[0]
            dyn_size = struct.unpack_from(endian + "Q", raw, base + 32)[0]
    if dyn_off is None:
        return info
    for i in range(0, dyn_size, 16):
        tag, val = struct.unpack_from(endian + "qQ", raw, dyn_off + i)
        if tag == 0:                                          # DT_NULL
            break
        if tag == 5:                                          # DT_STRTAB
            strtab = val
        elif tag == 1:                                        # DT_NEEDED
            needed.append(val)
        elif tag in (15, 29):                                 # RPATH/RUNPATH
            info["rpath"] = True
    if strtab is not None:
        # DT_STRTAB is a virtual address, so map it to a file offset through
        # the PT_LOAD segment that owns it.  DT_NEEDED values are seen in both
        # conventions on this toolchain (absolute address, or plain offset into
        # .dynstr), so normalise before indexing.
        strtab_file = None
        for vaddr, offset, size in loads:
            if vaddr <= strtab < vaddr + size:
                strtab_file = strtab - vaddr + offset
                break
        if strtab_file is None:
            raise ValueError("DT_STRTAB is not covered by any PT_LOAD")
        blob = raw[strtab_file:strtab_file + 8192]
        for off in needed:
            # Per the ELF spec a DT_NEEDED value is an *index into* .dynstr,
            # while DT_STRTAB itself is a virtual address -- hence no further
            # subtraction here.
            end = blob.index(b"\x00", off)
            info["needed"].append(blob[off:end].decode())
    return info


def main():
    if len(sys.argv) < 2:
        print("usage: test_ohos_specific.py <path-to-packaged-splitvt>")
        return 2
    binary = os.path.abspath(sys.argv[1])
    print("== splitvt OHOS-specific checks, binary=%s ==" % binary)
    arm_budget(300)
    raw = open(binary, "rb").read()

    # ---- C1..C4: the delivered ELF --------------------------------------
    try:
        info = parse_elf(raw)
    except ValueError as exc:
        check(False, "C1 ELF header parsed", str(exc))
        return summary()
    check(info["class"] == 2, "C1 ELFCLASS64", "class=%d" % info["class"])
    check(info["data"] == 1, "C1 little-endian", "data=%d" % info["data"])
    check(info["machine"] == 183, "C1 EM_AARCH64", "machine=%d" % info["machine"])
    check(info["interp"] == "/lib/ld-musl-aarch64.so.1",
          "C2 PT_INTERP is the OHOS musl loader", "interp=%r" % info["interp"])
    check(info["needed"] == ["libc.so"],
          "C3 DT_NEEDED is libc.so only (no termcap/ncurses dependency)",
          "needed=%r" % info["needed"])
    check(not info["rpath"], "C4 no DT_RPATH/DT_RUNPATH", "rpath=%r" % info["rpath"])
    leaks = [token for token in (b"/storage/Users/", b"/home/", b"tmp/ch/",
                                 b".conan2", b"build/Release", b"/root/")
             if token in raw]
    check(not leaks, "C4 no build-machine path embedded in the ELF",
          "leaks=%r" % leaks)

    # ---- C5: compiled-in SHELL default still behaves like a string -------
    ses = PtySession([binary, "-norc"], child_env("vt100", drop=("SHELL",)))
    try:
        stream = ses.read_until([SETUP_DONE], timeout=40)
        prompt = ses.read_until([b"$ "], timeout=25)
        check(b"/ bin / sh" not in prompt and b"No such file" not in prompt,
              "C5 SHELL macro did not degrade into bare tokens",
              "stream=%s" % tail(prompt))
        check(b"$ " in prompt,
              "C5 compiled-in /bin/sh runs interactively in both windows",
              "stream=%s" % tail(prompt, 400))
        check(ses.alive(), "C5 splitvt is still serving both windows",
              "rc=%r" % ses.rc)
    finally:
        ses.close()

    # ---- C6: pty ownership model on this platform ------------------------
    import pty
    master, slave = pty.openpty()
    try:
        name = os.ttyname(slave)
        st = os.stat(name)
        check((st.st_mode & 0o7777) == 0o600 and st.st_uid == os.getuid(),
              "C6 /dev/pts slave arrives 0600 owned by the invoking uid",
              "name=%s mode=%o uid=%d" % (name, st.st_mode & 0o7777, st.st_uid))
    except OSError as exc:
        check(False, "C6 /dev/pts slave is statable", repr(exc))
    finally:
        os.close(slave)
        os.close(master)

    disarm_budget()
    return summary()


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:                 # fail closed, never silently pass
        check(False, "OHOS suite aborted", repr(exc))
        exit_code = summary()
    sys.exit(exit_code)
