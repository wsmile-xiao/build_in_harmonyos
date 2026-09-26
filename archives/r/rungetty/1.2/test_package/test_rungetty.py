#!/usr/bin/env python3
"""Consumer tests for the packaged rungetty binary (HarmonyOS PC / OHOS aarch64).

rungetty has no upstream test suite (the archive ships 8 files and the Makefile
has no `check` target — see ../MANIFEST.yml), so the behaviour of the built
binary is asserted here.  Every check exercises the installed executable; if the
package artifacts are removed the first check already fails, which is what CI
gate L1e verifies destructively (R34).

argv: <path to bin/rungetty> <path to package folder>
"""
import os
import subprocess
import sys

exe = sys.argv[1]
package_folder = sys.argv[2]
failures = []


def run(args):
    return subprocess.run(
        [exe] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def check(name, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + name
          + ("" if condition else "  ::  " + str(detail)))
    if not condition:
        failures.append(name)


# T0 — the packaged executable must be there and runnable (L1e negative hook).
check("T0 packaged binary exists and is executable",
      os.path.isfile(exe) and os.access(exe, os.X_OK), exe)

no_args = run([])
help_opt = run(["--help"])
tty1 = run(["tty1", "/bin/true"])
bogus = run(["nosuchtty123", "/bin/true"])
opts = run(["-d", "0", "-n", "0", "tty1", "/bin/true"])

# T1 — unknown option reaches getopt and the usage path exits 1.
check("T1 `--help` exits 1 through the usage path",
      help_opt.returncode == 1, help_opt.returncode)

# T2 — the failure really comes from argument parsing inside the binary:
# musl getopt_long reports the rejected option on stderr.
check("T2 getopt reports the rejected option on stderr",
      "unrecognized option" in help_opt.stderr, repr(help_opt.stderr))

# T3 — no tty argument: usage() is the documented failure path.
check("T3 missing tty argument exits 1 (usage path)",
      no_args.returncode == 1, no_args.returncode)

# T4 — no run may die from a signal (a negative return code would mean e.g.
# SIGSYS from a refused syscall or SIGSEGV); rungetty must always terminate by
# calling exit().
check("T4 every invocation terminates normally (no signal death)",
      all(r.returncode >= 0 for r in (no_args, help_opt, tty1, bogus, opts)),
      [r.returncode for r in (no_args, help_opt, tty1, bogus, opts)])

# T5 — the ELF is accepted by the dynamic loader on the device: 126/127 would
# mean "cannot execute" (missing interpreter / rejected signature).
check("T5 binary is loadable (rc is not 126/127)",
      all(r.returncode not in (126, 127) for r in (no_args, help_opt, tty1)),
      [r.returncode for r in (no_args, help_opt, tty1)])

# T6 — OHOS specific: /dev/tty1 does not exist on this platform (measured with
# the probe recorded in ../notes.md 附录 A/B: open("/dev/tty1") -> ENOENT), so
# rungetty must fail instead of pretending the line was acquired.
check("T6 `tty1` fails on OHOS as probed (ENOENT device, rc 1)",
      tty1.returncode == 1, tty1.returncode)

# T7 — a non existent tty line must not be reported as success either.
check("T7 unknown tty line exits 1", bogus.returncode == 1, bogus.returncode)

# T8 — the documented short options are still parsed (they must not be taken
# for the tty operand, i.e. rc stays 1 and getopt stays quiet about them).
check("T8 -d/-n options are accepted by the parser",
      "unrecognized option" not in opts.stderr and opts.returncode == 1,
      (opts.returncode, repr(opts.stderr)))

# T9 — packaging contract: FHS manual page location (upstream installs to the
# non-FHS $(ROOT)/usr/man/man8) and the man page content survived.
man = os.path.join(package_folder, "share", "man", "man8", "rungetty.8")
man_ok = os.path.isfile(man)
title = ""
if man_ok:
    with open(man, encoding="utf-8", errors="replace") as handle:
        title = handle.readline().strip()
check("T9 man8 page installed at share/man/man8/rungetty.8",
      man_ok and title.upper().startswith(".TH RUNGETTY"), (man, title))

# T10 — no stray library is packaged: rungetty is a static-free single tool
# whose only dependency is libc, so nothing may appear under lib/.
libdir = os.path.join(package_folder, "lib")
check("T10 no libraries shipped (application package)",
      not os.path.isdir(libdir) or not os.listdir(libdir), libdir)

for name in failures:
    print("FAILED: " + name)
sys.exit(1 if failures else 0)
