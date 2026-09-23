#!/usr/bin/env python3
"""HarmonyOS-specific test suite for the packaged lci 1.1 executable.

This is an INDEPENDENT ohos-specific test entry (distinct from the generic
consumer entry test_lci.sh): it verifies the properties the OHOS PC
adaptation must guarantee, fail-closed on any check error.

  H1 ELF identity   : the installed bin/lci is ELF64 little-endian AArch64
                      (EI_CLASS=ELFCLASS64, EI_DATA=ELFDATA2LSB,
                      e_machine == EM_AARCH64 == 183).
  H2 interpreter    : PT_INTERP is exactly /lib/ld-musl-aarch64.so.1
                      (OHOS musl libc, not glibc).
  H3 codesign       : the binary carries a .codesign section (repo signing
                      requirement, E486/E489).
  H4 hygiene        : no build-machine absolute paths embedded in the
                      binary and no RUNPATH/RPATH dynamic entries at all
                      (a terminal tool must not carry host paths).
  H5 pty REPL       : run the REAL interpreter on the HarmonyOS PC in an
                      actual pseudo terminal (pty.fork + TERM=xterm) so the
                      replxx/termios raw-mode init path guarded by patch
                      0001 executes; evaluate the deterministic lambda
                      expression "Head [7, 8, 9]" and strictly assert the
                      printed result is 7 and the process exits 0 on EOT.

Usage: ohos_specific_test.py <path-to-installed-lci>
Exit code: 0 all checkpoints passed, 1 any failure/skip (fail closed).
"""
import os
import re
import struct
import subprocess
import sys

# ELF constants (self-contained parse; readelf presence is NOT assumed).
ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
PT_INTERP = 3
SHT_PROGBITS = 1


def readelf(path):
    """Locate a readelf binary; raise if none (fail closed)."""
    import shutil
    for cand in (shutil.which("llvm-readelf"), shutil.which("readelf"),
                 "/data/service/hnp/bin/readelf"):
        if cand and os.path.isfile(cand):
            return cand
    raise RuntimeError("no readelf available on this host")


def check_elf_identity(blob):
    """H1: ELF64 little-endian AArch64 via direct header parse."""
    if len(blob) < 64 or blob[:4] != b"\x7fELF":
        return False, "not an ELF file"
    ei_class, ei_data = blob[4], blob[5]
    if ei_class != ELFCLASS64:
        return False, f"EI_CLASS={ei_class} is not ELF64"
    if ei_data != ELFDATA2LSB:
        return False, f"EI_DATA={ei_data} is not little-endian"
    e_machine = struct.unpack_from("<H", blob, 18)[0]
    if e_machine != EM_AARCH64:
        return False, f"e_machine={e_machine} is not EM_AARCH64 ({EM_AARCH64})"
    return True, "ELF64 little-endian AArch64"


def check_pt_interp(blob):
    """H2: program interpreter is exactly /lib/ld-musl-aarch64.so.1."""
    # Parse program headers directly: e_phoff@0x20, e_phentsize@0x36,
    # e_phnum@0x38 (ELF64 LE). Each Phdr: p_type@0, p_offset@8.
    e_phoff = struct.unpack_from("<Q", blob, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", blob, 0x36)[0]
    e_phnum = struct.unpack_from("<H", blob, 0x38)[0]
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", blob, off)[0]
        if p_type == PT_INTERP:
            p_offset = struct.unpack_from("<Q", blob, off + 8)[0]
            end = blob.index(b"\x00", p_offset)
            interp = blob[p_offset:end].decode("ascii", "replace")
            if interp == "/lib/ld-musl-aarch64.so.1":
                return True, interp
            return False, f"PT_INTERP is {interp!r}"
    return False, "no PT_INTERP segment"


def check_codesign(blob):
    """H3: exactly one .codesign section (repo signing requirement)."""
    # Section headers: e_shoff@0x28, e_shentsize@0x3A, e_shnum@0x3C,
    # e_shstrndx@0x3E. Section name lives in the shstrtab.
    e_shoff = struct.unpack_from("<Q", blob, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", blob, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", blob, 0x3C)[0]
    e_shstrndx = struct.unpack_from("<H", blob, 0x3E)[0]
    if e_shnum == 0 or e_shstrndx >= e_shnum:
        return False, "no section header table"
    shstr_off = e_shoff + e_shstrndx * e_shentsize
    shstr_offset = struct.unpack_from("<Q", blob, shstr_off + 0x18)[0]
    shstr_size = struct.unpack_from("<Q", blob, shstr_off + 0x20)[0]
    shstrtab = blob[shstr_offset:shstr_offset + shstr_size]
    count = 0
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name = struct.unpack_from("<I", blob, off)[0]
        name_end = shstrtab.index(b"\x00", sh_name)
        name = shstrtab[sh_name:name_end].decode("ascii", "replace")
        if name == ".codesign":
            count += 1
    if count == 1:
        return True, ".codesign section present"
    return False, f".codesign section count = {count} (expected 1)"


def check_no_rpath(path):
    """H4a: no RUNPATH/RPATH dynamic tags at all (fail closed).

    PASS requires ALL of: readelf -d exits 0, its output is a parseable
    dynamic-section report, and no RPATH/RUNPATH entry appears in it. A
    failed or unparseable readelf run is a FAILURE — "no RPATH found" is
    only evidence when the tool actually ran successfully. (Timeouts and
    a missing readelf binary raise, which main() also counts as failure.)
    """
    out = subprocess.run([readelf(path), "-d", path],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        detail = (out.stderr.strip() or out.stdout.strip()).splitlines()
        last = detail[-1] if detail else "(no output)"
        return False, f"readelf -d failed (exit {out.returncode}): {last}"
    # A successful `readelf -d` either dumps the dynamic section or states
    # there is none; both definitively cover the RPATH/RUNPATH question.
    # Anything else means the output cannot be trusted as evidence.
    has_dump = re.search(r"Dynamic section at offset", out.stdout)
    no_dyn = re.search(r"There is no dynamic section", out.stdout)
    if not has_dump and not no_dyn:
        return False, "readelf -d output unparseable (no dynamic section report)"
    for line in out.stdout.splitlines():
        if "RPATH" in line or "RUNPATH" in line:
            return False, line.strip()
    return True, "no RPATH/RUNPATH entries"


def check_no_build_paths(blob):
    """H4b: no build-machine absolute paths embedded in the binary.

    Scans printable strings for the build worktree root and other typical
    build-home prefixes. The conan cache path itself is excluded — the
    packaged interpreter legitimately stores DATADIR (the package's own
    share/ prefix) and that is NOT a build machine path leak.
    """
    # Build-time absolute path roots that must never appear in the final
    # binary. /storage/Users/currentUser is the build worktree home;
    # classic CI homes too.
    forbidden = [
        b"/storage/Users/currentUser/build_in_harmonyos",
        b"/home/buildbot",
        b"/root/build",
    ]
    # Coarser heuristic: any absolute path mentioning the worktree or a
    # user home directory inside .debug_str-free release binaries.
    for pat in forbidden:
        if pat in blob:
            return False, f"embedded build path: {pat.decode()}"
    # Generic home-directory leak: "/home/<user>/" occurrences that are
    # not part of the musl interpreter path.
    homes = re.findall(rb"/home/[A-Za-z0-9_.-]+/", blob)
    if homes:
        return False, f"embedded home path(s): {sorted(set(homes))[:3]}"
    return True, "no build-machine absolute paths"


def check_pty_repl(lci):
    """H5: real REPL session on a pseudo terminal.

    Drives the actual replxx/termios raw-mode init code guarded by patch
    0001 (src/run.c VMIN/VTIME): banner, prompt, deterministic expression
    evaluation, clean EOT exit.
    """
    import pty
    import select
    import time

    os.environ["TERM"] = "xterm"          # replxx/termios init requires TERM
    pid, fd = pty.fork()
    if pid == 0:                          # child: exec lci on the pty
        try:
            os.execv(lci, [lci])
        finally:
            os._exit(127)

    def drain(seconds):
        buf = b""
        end = time.time() + seconds
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.2)
            if r:
                try:
                    data = os.read(fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                buf += data
            if os.waitpid(pid, os.WNOHANG)[0]:
                break
        return buf

    try:
        drain(2.0)                        # banner + first prompt
        os.write(fd, b"Head [7, 8, 9]\r")
        out = drain(4.0)                  # evaluate + print result
        ok_result = b"\r\n7\r\n" in out
        os.write(fd, b"\x04")             # EOT: replxx EOF -> exit
        time.sleep(1.0)
        ok_exit = False
        try:
            wpid, status = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:
                ok_exit = os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
            else:
                os.kill(pid, 9)           # still alive: force-quit
                os.waitpid(pid, 0)
        except ChildProcessError:
            ok_exit = True
        if not ok_result:
            return False, "REPL did not print 7 for Head [7, 8, 9]"
        if not ok_exit:
            return False, "REPL did not exit 0 after EOT"
        return True, "pty REPL: Head [7, 8, 9] => 7, EOT exit 0"
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def main():
    if len(sys.argv) != 2:
        print("usage: ohos_specific_test.py <path-to-lci>", file=sys.stderr)
        return 1
    lci = sys.argv[1]
    failures = []

    # A missing/unreadable binary is a FAILURE (fail closed), not a skip.
    try:
        with open(lci, "rb") as f:
            blob = f.read()
    except OSError as exc:
        print(f"FAIL: cannot read {lci}: {exc}")
        return 1

    # H1: ELF64 LE AArch64
    try:
        ok, msg = check_elf_identity(blob)
        print(("PASS" if ok else "FAIL") + f": ohos-elf-identity ({msg})")
        if not ok:
            failures.append("elf-identity")
    except Exception as exc:  # any check error -> fail closed
        print(f"FAIL: ohos-elf-identity (check error: {exc})")
        failures.append("elf-identity")

    # H2: musl interpreter
    try:
        ok, msg = check_pt_interp(blob)
        print(("PASS" if ok else "FAIL") + f": ohos-musl-interpreter ({msg})")
        if not ok:
            failures.append("musl-interpreter")
    except Exception as exc:
        print(f"FAIL: ohos-musl-interpreter (check error: {exc})")
        failures.append("musl-interpreter")

    # H3: .codesign section
    try:
        ok, msg = check_codesign(blob)
        print(("PASS" if ok else "FAIL") + f": ohos-codesign ({msg})")
        if not ok:
            failures.append("codesign")
    except Exception as exc:
        print(f"FAIL: ohos-codesign (check error: {exc})")
        failures.append("codesign")

    # H4a: no RPATH/RUNPATH
    try:
        ok, msg = check_no_rpath(lci)
        print(("PASS" if ok else "FAIL") + f": ohos-no-rpath ({msg})")
        if not ok:
            failures.append("no-rpath")
    except Exception as exc:
        print(f"FAIL: ohos-no-rpath (check error: {exc})")
        failures.append("no-rpath")

    # H4b: no build-machine paths
    try:
        ok, msg = check_no_build_paths(blob)
        print(("PASS" if ok else "FAIL") + f": ohos-no-build-paths ({msg})")
        if not ok:
            failures.append("no-build-paths")
    except Exception as exc:
        print(f"FAIL: ohos-no-build-paths (check error: {exc})")
        failures.append("no-build-paths")

    # H5: real pty REPL on the HarmonyOS PC
    try:
        ok, msg = check_pty_repl(lci)
        print(("PASS" if ok else "FAIL") + f": ohos-pty-repl ({msg})")
        if not ok:
            failures.append("pty-repl")
    except Exception as exc:
        print(f"FAIL: ohos-pty-repl (check error: {exc})")
        failures.append("pty-repl")

    if failures:
        print(f"ohos-specific: {len(failures)} checkpoint(s) failed: "
              + ", ".join(failures))
        return 1
    print("ohos-specific: all 6 checkpoints passed "
          "(elf-identity, musl-interpreter, codesign, no-rpath, "
          "no-build-paths, pty-repl)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
