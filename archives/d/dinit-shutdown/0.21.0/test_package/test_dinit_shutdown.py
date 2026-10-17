#!/usr/bin/env python3
"""Behavioural consumer test program for the dinit-shutdown package (application type).

Run from the conanrun environment (`test_package/conanfile.py` test()), where PATH contains
the installed `bin/` directory. It exercises the five packaged executables as real processes
and exits non-zero if any check fails.

Two groups of checks:

* the CLI behaviour of the five installed names (usage banner echoes its own argv[0],
  default action, option parser, control-socket connect path);
* an **OHOS platform contract** section that pins the properties this port depends on and
  that only hold on HarmonyOS PC: the artifact is an AArch64 PIE, it keeps the OHOS
  `.codesign` section and its symbol table (stripped builds fail to load on this platform
  with exit code 126, verified on device), and the compiled-in control socket path and
  `dinit-` command prefix are the ones this package was configured with.

No check may ever issue a shutdown: the `--system`, `-r`, `-h`, `-p`, `-s` and `-k` actions
are never passed, and the bare invocation is guarded by a control-socket check.
"""

import os
import shutil
import struct
import subprocess
import sys

BINARIES = ["dinit-shutdown", "dinit-halt", "dinit-poweroff", "dinit-reboot",
            "dinit-soft-reboot"]

# Control socket compiled into the utility (upstream default on non-Linux platforms;
# Linux would compile in /run/dinitctl).
CONTROL_SOCKET = "/var/run/dinitctl"

# OHOS / AArch64 ELF constants used by the platform contract checks below.
EM_AARCH64 = 183
ET_DYN = 3

RESULTS = []


def check(condition, message):
    RESULTS.append((bool(condition), message))
    print("  %-4s %s" % ("ok" if condition else "FAIL", message))


def resolve(binary):
    """Return the absolute path of a packaged executable, or None."""
    return shutil.which(binary)


def run(binary, args=()):
    """Run the packaged executable for real and return (exit_code, merged output).

    The absolute path from shutil.which() is always used: PATH lookup inside
    subprocess is not portable on OHOS (the CI python bundle spawns through
    os.posix_spawn with the bare name and raises FileNotFoundError even though
    which() resolved it), so the executable is never passed as a bare name.
    """
    exe = resolve(binary)
    if exe is None:
        raise RuntimeError("packaged executable not found in PATH: %s" % binary)
    proc = subprocess.run([exe] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    return proc.returncode, proc.stdout or ""


def ohos_platform_contract():
    """Pin the HarmonyOS-specific properties of the delivered executable."""
    path = resolve("dinit-shutdown")
    if path is None:
        check(False, "OHOS: dinit-shutdown not found in PATH, platform contract not verifiable")
        return
    with open(path, "rb") as handle:
        data = handle.read()

    e_ident = data[:16]
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    check(e_ident[:4] == b"\x7fELF" and e_ident[4] == 2 and e_ident[5] == 1,
          "OHOS: artifact is a 64-bit little-endian ELF")
    check(e_machine == EM_AARCH64,
          "OHOS: artifact targets AArch64 (e_machine=%d, expected %d)"
          % (e_machine, EM_AARCH64))
    check(e_type == ET_DYN,
          "OHOS: artifact is position independent (e_type=%d, expected ET_DYN)"
          % e_type)
    check(b".codesign" in data,
          "OHOS: .codesign section kept (hnp toolchain signature; re-signing or "
          "stripping breaks loading on this platform)")
    check(b".symtab" in data,
          "OHOS: symbol table kept, binary not stripped (stripped builds exit 126 here)")
    # Anchor on the NUL-terminated C literals: a plain substring check would also
    # accept a longer path that merely contains the expected text.
    check(CONTROL_SOCKET.encode() + b"\x00" in data,
          "OHOS: compiled-in control socket literal %s\\0 present (upstream non-Linux default)"
          % CONTROL_SOCKET)
    for literal in (b"dinit-reboot", b"dinit-soft-reboot"):
        check(literal + b"\x00" in data,
              "OHOS: compiled-in command prefix literal %rNUL present (--shutdown-prefix)"
              % literal.decode())

    # The four alias names are copies of the same build output; a packaging mistake
    # (e.g. only one file copied, or a stale alias) is caught here.
    aliases = [b for b in BINARIES if b != "dinit-shutdown"]
    identical = [a for a in aliases if resolve(a) and open(resolve(a), "rb").read() == data]
    check(len(identical) == len(aliases),
          "OHOS: all %d alias executables are byte-identical to bin/dinit-shutdown" % len(aliases))


def main():
    for binary in BINARIES:
        check(resolve(binary) is not None, "%s: installed and found in PATH" % binary)
        if resolve(binary) is None:
            continue

        rc, out = run(binary, ["--help"])
        first_line = out.splitlines()[0] if out.splitlines() else ""
        check(rc == 1, "%s --help: exit code 1 (usage exit)" % binary)
        check(first_line.startswith("%s :" % binary),
              "%s: usage banner echoes its own argv[0] (%r)" % (binary, first_line))
        check("shutdown the system" in first_line, "%s: banner text intact" % binary)
        check("power down (default)" in out, "%s: default action is power down" % binary)
        check("soft-reboot (restart dinit with same boot-time arguments)" in out,
              "%s: -s soft-reboot option documented" % binary)
        check("show this help" in out, "%s: --help documented" % binary)

    rc, out = run("dinit-shutdown", ["-Z"])
    check(rc == 1, "dinit-shutdown -Z: exit code 1")
    check("Unrecognized command-line parameter: -Z" in out,
          "dinit-shutdown -Z: unknown option rejected by the parser")

    if os.path.exists(CONTROL_SOCKET):
        # Guarded skip, reported explicitly: never send a shutdown to a live daemon.
        print("  SKIP %s exists (service manager listening): no-daemon connect "
              "check not executed" % CONTROL_SOCKET)
    else:
        rc, out = run("dinit-shutdown")
        check(rc == 1, "dinit-shutdown (no daemon): exit code 1")
        check("connect:" in out and "No such file or directory" in out,
              "dinit-shutdown (no daemon): control-socket connect path reached")

    ohos_platform_contract()

    failed = [m for ok, m in RESULTS if not ok]
    print("\nRESULT: %d checks, %d passed, %d failed"
          % (len(RESULTS), len(RESULTS) - len(failed), len(failed)))
    for message in failed:
        print("  failed: %s" % message)
    print("PASSED %d/%d" % (len(RESULTS) - len(failed), len(RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
