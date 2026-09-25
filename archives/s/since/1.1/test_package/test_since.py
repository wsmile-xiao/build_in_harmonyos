#!/usr/bin/env python3
"""Functional test suite for the packaged `since` binary.

Two layers:
  1. artifact checks  — the binary exists and is an aarch64 ELF image;
  2. runtime checks   — real functional assertions ported from the Debian
     autopkgtest suite (debian/tests/simple), executed against the binary.

Skipping the runtime layer is deliberately hard to trigger:
  * on an aarch64 host (the CI worker) the binary MUST run — a failed launch
    is reported as a failure, never as a skip;
  * on a foreign-architecture host the launch failure must carry an explicit
    "cannot execute this image" marker (missing musl loader, exec format
    error, qemu signal). A binary that starts and then misbehaves is always
    judged by the functional assertions below.
"""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time

EM_AARCH64 = 0xB7

# Markers proving the image itself could not be loaded/executed by this host.
# Anything outside this list means the process did start → assertions decide.
NOT_EXECUTABLE_MARKERS = (
    "Could not open '/lib/ld-musl",       # binfmt/qemu: target loader absent
    "Exec format error",                  # kernel refused the image
    "cannot execute binary file",
    "uncaught target signal",             # qemu-user cannot run the loader
    "qemu: could not open",
)

AARCH64_HOST_NAMES = ("aarch64", "arm64", "armv8", "armv8l")


def find_binary(bindir):
    """Locate `since` inside the tested package only.

    Deliberately no PATH fallback: a same-named binary elsewhere on PATH would
    let this suite pass without the package under test, defeating both R34 and
    the CI destructive reverse check.
    """
    if not bindir:
        return None
    candidate = os.path.join(bindir, "since")
    return candidate if os.path.isfile(candidate) else None


def artifact_checks(binary):
    """Validate the packaged file is an executable aarch64 ELF."""
    with open(binary, "rb") as handle:
        header = handle.read(20)
    if header[:4] != b"\x7fELF":
        print(f"[fail] not an ELF image: {binary}")
        return False
    machine = int.from_bytes(header[18:20], "little")
    if machine != EM_AARCH64:
        print(f"[fail] unexpected ELF machine 0x{machine:x} (want 0x{EM_AARCH64:x})")
        return False
    if not os.access(binary, os.X_OK):
        print(f"[fail] not executable: {binary}")
        return False
    print(f"[ok] artifact: {binary} (aarch64 ELF, executable)")
    return True


def run_since(binary, args, workdir):
    env = dict(os.environ)
    env["HOME"] = workdir
    env.pop("SINCE", None)
    return subprocess.run([binary] + args, cwd=workdir, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=60)


def probe_runnable(binary, workdir):
    """Decide whether this host can execute the image at all.

    The verdict must not depend on the binary's exit status: a program that
    launches and then fails is a real test failure, not a skip condition.
    """
    try:
        proc = run_since(binary, ["-V"], workdir)
    except OSError as exc:
        return False, f"OSError: {exc}"
    combined = f"{proc.stdout}{proc.stderr}"
    for marker in NOT_EXECUTABLE_MARKERS:
        if marker in combined:
            return False, combined.strip().splitlines()[:2]
    return True, (proc.stdout.strip() or proc.stderr.strip()
                  or f"exit status {proc.returncode}")


def follow_check(binary, workdir):
    """`-f` follow mode — the inotify/poll path enabled by the Makefile patch.

    Returns (ok, detail). A line appended after the process started must reach
    stdout within the timeout window.
    """
    path = os.path.join(workdir, "follow.log")
    with open(path, "w") as handle:
        handle.write("seed\n")
    run_since(binary, ["-z", "follow.log"], workdir)  # establish the baseline

    env = dict(os.environ)
    env["HOME"] = workdir
    env.pop("SINCE", None)
    proc = subprocess.Popen([binary, "-f", "follow.log"], cwd=workdir, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True)
    captured = []

    def reader():
        line = proc.stdout.readline()
        if line:
            captured.append(line)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        time.sleep(1)
        with open(path, "a") as handle:
            handle.write("live-line\n")
        thread.join(timeout=15)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    if not captured:
        return False, "no output within 15s"
    return captured[0].strip() == "live-line", repr(captured[0])


def runtime_checks(binary, workdir):
    """Functional assertions ported from Debian's autopkgtest `simple`,
    plus a follow-mode assertion covering the patched inotify probe."""
    results = []

    def check(name, condition, detail=""):
        results.append((name, condition))
        print(f"[{'ok' if condition else 'fail'}] {name}" + (f" — {detail}" if detail and not condition else ""))

    first = os.path.join(workdir, "example.txt")
    second = os.path.join(workdir, "example2.txt")
    with open(first, "w") as handle:
        handle.write("foo\n")
    with open(second, "w") as handle:
        handle.write("bar\n")

    # A silent do-nothing binary must not pass these: besides the empty stdout
    # we require a clean exit status and the state file `since` keeps in $HOME.
    state = os.path.join(workdir, ".since")
    proc = run_since(binary, ["-z", "example.txt"], workdir)
    check("-z discards existing content and records state (single file)",
          proc.stdout == "" and proc.returncode == 0 and os.path.isfile(state),
          f"rc={proc.returncode} out={proc.stdout!r} state_file={os.path.isfile(state)}")
    proc = run_since(binary, ["-z", "example2.txt"], workdir)
    check("-z discards existing content and records state (second file)",
          proc.stdout == "" and proc.returncode == 0 and os.path.isfile(state),
          f"rc={proc.returncode} out={proc.stdout!r} state_file={os.path.isfile(state)}")

    with open(first, "a") as handle:
        handle.write("bar\n")
    proc = run_since(binary, ["example.txt"], workdir)
    check("default action prints appended line", proc.stdout == "bar\n", repr(proc.stdout))

    with open(first, "w") as handle:
        handle.write("fnord\n")
    proc = run_since(binary, ["example.txt"], workdir)
    check("truncation is detected and reported",
          proc.stdout == "fnord\n" and "truncated" in proc.stderr,
          repr(proc.stdout) + repr(proc.stderr))

    with open(first, "a") as handle:
        handle.write("hurz\n")
    with open(second, "a") as handle:
        handle.write("bla\n")
    proc = run_since(binary, ["-z", "example.txt", "example2.txt"], workdir)
    check("-z emits discard headers for multiple files",
          proc.stdout == "==> example.txt [discarded] <==\n==> example2.txt [discarded] <==\n",
          repr(proc.stdout))

    with open(first, "a") as handle:
        handle.write("flarp\n")
    with open(second, "a") as handle:
        handle.write("gnarz\n")
    proc = run_since(binary, ["example.txt", "example2.txt"], workdir)
    check("multi-file output carries per-file headers",
          proc.stdout == "==> example.txt <==\nflarp\n==> example2.txt <==\ngnarz\n",
          repr(proc.stdout))

    follow_ok, follow_detail = follow_check(binary, workdir)
    check("-f follow mode streams a line appended after start "
          "(inotify/poll path)", follow_ok, follow_detail)

    passed = sum(1 for _, ok in results if ok)
    print(f"[summary] runtime checks: {passed}/{len(results)} passed")
    return passed == len(results)


def main():
    bindir = sys.argv[1] if len(sys.argv) > 1 else ""
    binary = find_binary(bindir)
    if not binary:
        print(f"[fail] since binary not found (bindir={bindir!r})")
        return 1

    if not artifact_checks(binary):
        return 1

    # E002: /tmp is read-only on OHOS — honour TMPDIR / HOME.
    base = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
    os.makedirs(base, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="since-test-", dir=base)
    try:
        runnable, detail = probe_runnable(binary, workdir)
        if not runnable:
            host = platform.machine()
            if host in AARCH64_HOST_NAMES:
                # Native host: the image must run. Refusing to launch here is a
                # genuine failure and must never be downgraded to a skip.
                print(f"[fail] runtime checks: {binary} did not start on an "
                      f"aarch64 host ({host})")
                print(f"       probe output: {detail}")
                return 1
            print(f"[skip] runtime checks: {host} host cannot execute {binary}")
            print(f"       probe output: {detail}")
            print("       artifact checks passed; the functional assertions run "
                  "on the aarch64 worker")
            return 0
        print(f"[ok] binary runs: {detail}")
        return 0 if runtime_checks(binary, workdir) else 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
