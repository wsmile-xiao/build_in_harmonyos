#!/usr/bin/env python3
"""Consumer test for the installed dcled package.

Runs the *installed* dcled / cpuload binaries in device-free mode (`-n`, no
message board attached) and asserts on what they actually print, so the package
is verified through its public surface rather than by a smoke print.

The binaries are spawned through subprocess with an explicitly assembled
LD_LIBRARY_PATH (they also carry an rpath into the libusb package): the
platform's conan runner segfaults when it launches the target binary itself.

usage: test_dcled.py <dcled> <cpuload> <fontdir> [<libdir> ...]
exit:  0 = all assertions passed, 1 = at least one failed, 2 = bad usage
"""

import os
import subprocess
import sys

TIMEOUT = 20
# -t / --test / cpuload run forever by design; they get a short window instead.
ENDLESS_TIMEOUT = 8

DCLED = ""
CPULOAD = ""
FONTDIR = ""
LIBDIRS = []

results = []


def scratch_dir():
    """A writable scratch directory.

    /tmp is read-only on this platform (error E002), so TMPDIR and the current
    directory are probed instead of relying on the tempfile defaults.
    """
    for base in (os.environ.get("TMPDIR"), os.getcwd(), os.path.expanduser("~")):
        if not base:
            continue
        candidate = os.path.join(base, "dcled-consumer-test")
        try:
            os.makedirs(candidate, exist_ok=True)
            probe = os.path.join(candidate, ".probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("")
            os.remove(probe)
            return candidate
        except OSError:
            continue
    raise RuntimeError("no writable scratch directory found")


def run(argv, stdin=None, timeout=TIMEOUT):
    """Run argv; return (returncode, output). returncode is None on timeout."""
    env = dict(os.environ)
    path = [d for d in LIBDIRS if d]
    if env.get("LD_LIBRARY_PATH"):
        path.append(env["LD_LIBRARY_PATH"])
    if path:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(path)
    kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": env}
    if stdin is not None:
        kwargs["input"] = stdin.encode()
    try:
        proc = subprocess.run(argv, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as exc:
        return None, (exc.stdout or b"").decode("utf-8", "replace")
    except OSError as exc:
        return -1, f"exec error: {exc}"
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def record(ok, name, detail):
    results.append((bool(ok), name, detail))
    return bool(ok)


def check(name, argv, expect=None, stdin=None, timeout=TIMEOUT, endless=False):
    """Assert on one run of a packaged binary.

    endless=True marks the modes that never return on their own: there the
    assertion is that the process printed `expect` and did not die (no SIGSEGV
    or non-zero exit) while the window elapsed.
    """
    rc, out = run(argv, stdin=stdin, timeout=timeout)
    if endless:
        ok = rc in (None, 0) and (expect is None or expect in out)
        detail = "still running when the window elapsed" if rc is None else f"exited rc={rc}"
    else:
        ok = rc == 0 and (expect is None or expect in out)
        detail = f"rc={rc}"
        if rc in (139, -11):
            detail += " SIGSEGV"
    if expect is not None and expect not in out:
        detail += f", missing {expect!r}"
    if not ok:
        detail += f", out={out[:120]!r}"
    record(ok, name, detail)
    return out


def run_checks():
    # ── packaged binaries (the upstream `all` target produces both) ──────────
    for path in (DCLED, CPULOAD):
        record(os.path.isfile(path) and os.access(path, os.X_OK),
               f"packaged binary {os.path.basename(path)}", path)

    # ── usage banner ────────────────────────────────────────────────────────
    check("dcled -h prints the usage banner", [DCLED, "-h"], expect="Usage")

    # ── message on the command line ─────────────────────────────────────────
    # Also the SIGSEGV regression guard: the unpatched upstream binary exits
    # 139 right here on the device-free path.
    check("dcled -m echoes the message (SIGSEGV regression guard)",
          [DCLED, "-n", "-e", "-m", "OHOS dcled"], expect="OHOS dcled")

    # ── message on stdin ────────────────────────────────────────────────────
    check("dcled reads the message from stdin",
          [DCLED, "-n", "-e"], stdin="piped-payload\n", expect="piped-payload")

    # ── messages read from named files ──────────────────────────────────────
    work = scratch_dir()
    f1 = os.path.join(work, "f1")
    f2 = os.path.join(work, "f2")
    with open(f1, "w", encoding="utf-8") as handle:
        handle.write("first-file\n")
    with open(f2, "w", encoding="utf-8") as handle:
        handle.write("second-file\n")
    out = check("dcled echoes messages read from files",
                [DCLED, "-n", "-e", f1, f2], expect="second-file")
    record("first-file" in out and out.find("first-file") < out.find("second-file"),
           "file arguments keep the order they were given",
           "first-file printed before second-file")

    # ── preamble selected by name and by number ─────────────────────────────
    check("dcled -p static -m ...", [DCLED, "-n", "-e", "-p", "static", "-m", "pre-name"],
          expect="pre-name")
    check("dcled -p 2 -m ...", [DCLED, "-n", "-e", "-p", "2", "-m", "pre-number"],
          expect="pre-number")

    # ── font data shipped by the package ────────────────────────────────────
    dlf = sorted(f for f in os.listdir(FONTDIR) if f.endswith(".dlf")) \
        if os.path.isdir(FONTDIR) else []
    record(len(dlf) >= 2, "font data packaged",
           f"{len(dlf)} .dlf file(s) in {FONTDIR}")

    # ── FONTDIR baked into the binary at package time ───────────────────────
    # Upstream defaults to /usr/local/share/dcled; the recipe points it inside
    # the package, which is what makes the installed binary self-contained.
    out = check("dcled reports the packaged font directory",
                [DCLED, "-n", "-e", "-t"], expect="font directory is",
                timeout=ENDLESS_TIMEOUT, endless=True)
    record(FONTDIR in out, "FONTDIR points inside the package", FONTDIR)

    # ── cpuload, the second binary from the same makefile target ────────────
    out = check("cpuload keeps producing load samples",
                [CPULOAD, "0.2"], timeout=ENDLESS_TIMEOUT, endless=True)
    values = [line.strip() for line in out.splitlines() if line.strip().isdigit()]
    record(bool(values), "cpuload emits numeric samples", f"{len(values)} sample(s)")
    # Upstream computes each sample against the previous /proc/stat reading,
    # but the first one is compared against zeroed counters, so it reports the
    # load accumulated since boot and its `100 * t / (t + idle)` arithmetic is
    # computed in int, which overflows on long-uptime hosts.  Only the periodic
    # samples (everything after #1) are the percentages the program documents.
    periodic = values[1:]
    bad = [v for v in periodic if not 0 <= int(v) <= 100]
    record(bool(periodic) and not bad,
           "cpuload periodic samples are percentages",
           f"{len(periodic)} sample(s), out of range: {bad[:4]}" if bad
           else f"0..100 over {len(periodic)} sample(s)")


def main(argv):
    global DCLED, CPULOAD, FONTDIR, LIBDIRS
    if len(argv) < 4:
        sys.stderr.write(__doc__)
        return 2
    DCLED, CPULOAD, FONTDIR = argv[1], argv[2], argv[3]
    LIBDIRS = argv[4:]

    run_checks()

    passed = sum(1 for ok, _, _ in results if ok)
    print("consumer test results:")
    for ok, name, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"CONSUMER TEST RESULT: {passed}/{len(results)} assertions passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
