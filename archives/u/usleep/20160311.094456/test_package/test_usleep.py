#!/usr/bin/env python3
"""Functional tests for the packaged usleep 20160311.094456 executable.

Upstream ships no test suite (its Makefile only has the usleep/install/clean
targets; see MANIFEST.yml for the R51 census), so this script checks the
packaged binary against what usleep.c does:

    if (argc < 2) return 0;
    unsigned int usecs = atoi(argv[1]);
    usleep(usecs);
    return 0;

Artifact checks (every host):
  A1  ELF64 little-endian image for EM_AARCH64
  A2  position-independent executable (ET_DYN)
  A3  PT_INTERP is the OHOS musl loader /lib/ld-musl-aarch64.so.1

Functional checks (need a host that can execute the image):
  F1  usleep                 no argument: exit 0, no output
  F2  usleep 0               exit 0, no output
  F3  usleep 300000          exit 0, no output, took >= 0.3 s
  F4  usleep 1200000         exit 0, no output, took >= 1.2 s (a request of
                             1 s or more is honoured, not rejected with EINVAL)
  F5  usleep abc             atoi() yields 0: exit 0, no output
  F6  usleep 250000 extra    extra arguments ignored: exit 0, took >= 0.25 s
Every run is bounded by a 30 s timeout, which also catches a unit mix-up
(300000 read as milliseconds would sleep 5 minutes). Negative arguments are
not tested: atoi() into unsigned int turns -1 into ~71 minutes by design.

On an aarch64 host (the OHOS CI worker) every functional check is mandatory.
On a foreign-architecture host the functional layer is reported as SKIPPED -
never as passed - and only when launching the image fails with an explicit
loader/format marker; an image that starts is always judged by the checks.

usage: test_usleep.py <path/to/bin/usleep>
"""
import errno
import platform
import struct
import subprocess
import sys
import time

EM_AARCH64 = 183
ET_DYN = 3
PT_INTERP = 3
OHOS_LOADER = "/lib/ld-musl-aarch64.so.1"
AARCH64_HOSTS = ("aarch64", "arm64", "armv8", "armv8l")
NOT_EXECUTABLE_MARKERS = (
    "Could not open '/lib/ld-musl",   # qemu-user via binfmt_misc: target loader absent
    "Exec format error",              # kernel refused the image
)
TIMEOUT = 30
SLACK = 0.005  # clock granularity allowance on the lower time bounds

ARTIFACT = {
    "A1": "ELF64 little-endian EM_AARCH64 image",
    "A2": "position-independent executable (ET_DYN)",
    "A3": f"PT_INTERP is {OHOS_LOADER}",
}
FUNCTIONAL = (
    ("F1", "no argument", [], 0.0),
    ("F2", "0 microseconds", ["0"], 0.0),
    ("F3", "300000 microseconds", ["300000"], 0.3),
    ("F4", "1200000 microseconds (>= 1 s)", ["1200000"], 1.2),
    ("F5", "non-numeric argument, atoi() -> 0", ["abc"], 0.0),
    ("F6", "extra argument ignored", ["250000", "extra"], 0.25),
)


def _report(status: str, check_id: str, text: str) -> None:
    print(f"[{status}] {check_id} {text}", flush=True)


def artifact_checks(path: str) -> dict:
    """Return {check id: failure message or None} for A1-A3."""
    results = dict.fromkeys(ARTIFACT)
    try:
        with open(path, "rb") as f:
            image = f.read()
    except OSError as exc:
        return {key: f"cannot read {path}: {exc}" for key in results}
    if len(image) < 64 or image[:4] != b"\x7fELF" or image[4] != 2 or image[5] != 1:
        return {key: "not an ELF64 little-endian image" for key in results}

    e_type, e_machine = struct.unpack_from("<HH", image, 16)
    if e_machine != EM_AARCH64:
        results["A1"] = f"e_machine={e_machine}, want EM_AARCH64 ({EM_AARCH64})"
    if e_type != ET_DYN:
        results["A2"] = f"e_type={e_type}, want ET_DYN ({ET_DYN})"

    results["A3"] = f"no PT_INTERP, want {OHOS_LOADER!r}"
    try:
        e_phoff = struct.unpack_from("<Q", image, 32)[0]
        e_phentsize, e_phnum = struct.unpack_from("<HH", image, 54)
        for i in range(e_phnum):
            base = e_phoff + i * e_phentsize
            if struct.unpack_from("<I", image, base)[0] != PT_INTERP:
                continue
            p_offset = struct.unpack_from("<Q", image, base + 8)[0]
            p_filesz = struct.unpack_from("<Q", image, base + 32)[0]
            interp = image[p_offset:p_offset + p_filesz].rstrip(b"\0").decode(errors="replace")
            results["A3"] = None if interp == OHOS_LOADER else f"PT_INTERP={interp!r}, want {OHOS_LOADER!r}"
            break
    except struct.error:
        results["A3"] = "truncated program header table"
    return results


def _run(binary: str, args: list) -> tuple:
    """Run binary with args; return (exit status, stdout, stderr, seconds)."""
    start = time.monotonic()
    proc = subprocess.run([binary, *args], stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=TIMEOUT, check=False)
    return proc.returncode, proc.stdout, proc.stderr, time.monotonic() - start


def cannot_execute_here(binary: str) -> bool:
    """True only on a foreign host whose launch fails with a loader/format marker."""
    if platform.machine().lower() in AARCH64_HOSTS:
        return False
    try:
        status, _, err, _ = _run(binary, [])
    except OSError as exc:
        return exc.errno == errno.ENOEXEC
    except subprocess.TimeoutExpired:
        return False
    text = err.decode(errors="replace")
    return status != 0 and any(marker in text for marker in NOT_EXECUTABLE_MARKERS)


def functional_check(binary: str, args: list, min_seconds: float) -> tuple:
    """Return (failure message or None, seconds) for one usleep run."""
    try:
        status, out, err, seconds = _run(binary, args)
    except subprocess.TimeoutExpired:
        return f"still running after {TIMEOUT} s", float(TIMEOUT)
    except OSError as exc:
        return f"cannot launch: {exc}", 0.0
    problems = []
    if status != 0:
        problems.append(f"exit status {status}, want 0")
    if out or err:
        problems.append(f"unexpected output stdout={out[:80]!r} stderr={err[:80]!r}")
    if seconds < min_seconds - SLACK:
        problems.append(f"returned after {seconds:.3f} s, want >= {min_seconds} s")
    return "; ".join(problems) or None, seconds


def main(argv: list) -> int:
    if len(argv) != 2:
        print("usage: test_usleep.py <path/to/bin/usleep>", file=sys.stderr)
        return 2
    binary = argv[1]

    artifact_failed = 0
    for check_id, problem in artifact_checks(binary).items():
        _report("fail" if problem else "ok", check_id, problem or ARTIFACT[check_id])
        artifact_failed += problem is not None
    artifact_passed = len(ARTIFACT) - artifact_failed

    host = platform.machine().lower()
    if cannot_execute_here(binary):
        _report("skip", "F1-F6", f"not run: this {host} host cannot execute the "
                "aarch64 OHOS image (functional checks are mandatory on the aarch64 CI worker)")
        print(f"RESULT: artifact checks {artifact_passed}/{len(ARTIFACT)} passed, "
              f"functional checks 0/{len(FUNCTIONAL)} run (SKIPPED)")
        return 1 if artifact_failed else 0

    functional_failed = 0
    for check_id, label, args, min_seconds in FUNCTIONAL:
        problem, seconds = functional_check(binary, args, min_seconds)
        detail = f"usleep {' '.join(args)}".rstrip() + f" [{label}] in {seconds:.3f} s"
        _report("fail" if problem else "ok", check_id, f"{detail}: {problem}" if problem else detail)
        functional_failed += problem is not None
    functional_passed = len(FUNCTIONAL) - functional_failed

    print(f"RESULT: artifact checks {artifact_passed}/{len(ARTIFACT)} passed, "
          f"functional checks {functional_passed}/{len(FUNCTIONAL)} passed on {host}")
    return 1 if artifact_failed or functional_failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
