#!/usr/bin/env python3
"""Functional tests for the packaged multisort 1.1 executable.

Upstream ships no test suite (the tarball holds multisort.c, months.gperf,
Makefile and README; the Makefile's only target is `multisort`, see
MANIFEST.yml for the R51 census), so this script checks the packaged binary
against what multisort.c does: open every file named on the command line,
repeatedly print the buffered line with the smallest Common Log Format
timestamp, exit 0 once every input is drained.

Artifact checks (every host):
  A1  ELF64 little-endian image for EM_AARCH64
  A2  position-independent executable (ET_DYN)
  A3  PT_INTERP is the OHOS musl loader /lib/ld-musl-aarch64.so.1

Functional checks (need a host that can execute the image):
  F1  single argument          usage text on stderr, exit 1, empty stdout
  F2  two logs, 1999 dates     lines interleaved by time, byte-exact
  F3  two logs, 2026 dates     same merge for current dates (patch: the upstream
                               900000000 sentinel fails from December 2018 on)
  F4  three logs, 13 lines     all twelve month names through the gperf table,
                               a year rollover and a three-way merge, byte-exact
  F5  3000-byte log line       passed through intact (patch: musl BUFSIZ is 1024
                               and fgets() used to split and garble the line);
                               1999 dates, so only the line-buffer fix is exercised
  F6  missing input file       "multisort: <file>: No such file or directory", exit 1
  F7  empty input file         "empty input file" on stderr, exit 1
Every run is bounded by a 30 s timeout. Days of month stay below 31 because
multisort ranks months as 30-day blocks (31 Jan and 1 Feb compare equal).

On an aarch64 host (the OHOS CI worker) every functional check is mandatory.
On a foreign-architecture host the functional layer is reported as SKIPPED -
never as passed - and only when launching the image fails with an explicit
loader/format marker; an image that starts is always judged by the checks.

usage: test_multisort.py <path/to/bin/multisort> <writable work directory>
"""
import errno
import os
import platform
import struct
import subprocess
import sys
import tempfile

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
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

ARTIFACT = {
    "A1": "ELF64 little-endian EM_AARCH64 image",
    "A2": "position-independent executable (ET_DYN)",
    "A3": f"PT_INTERP is {OHOS_LOADER}",
}


def clf(host: str, stamp: str, path: str, tail: str = "") -> str:
    """One Common Log Format line (with newline) for the given timestamp."""
    return f'{host} - - [{stamp} -0800] "GET {path} HTTP/1.0" 200 {len(path)}{tail}\n'


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

    results["A3"] = "no PT_INTERP program header"
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
    """Run binary with args; return (exit status, stdout bytes, stderr text)."""
    proc = subprocess.run([binary, *args], stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=TIMEOUT, check=False)
    return proc.returncode, proc.stdout, proc.stderr.decode(errors="replace")


def cannot_execute_here(binary: str) -> bool:
    """True only on a foreign host whose launch fails with a loader/format marker."""
    if platform.machine().lower() in AARCH64_HOSTS:
        return False
    try:
        status, _, err = _run(binary, [])
    except OSError as exc:
        return exc.errno == errno.ENOEXEC
    except subprocess.TimeoutExpired:
        return False
    return status != 0 and any(marker in err for marker in NOT_EXECUTABLE_MARKERS)


def write_logs(workdir: str, logs: dict) -> dict:
    """Write {name: [lines]} under workdir; return {name: path}."""
    paths = {}
    for name, lines in logs.items():
        paths[name] = os.path.join(workdir, name)
        with open(paths[name], "w", encoding="ascii", newline="\n") as f:
            f.writelines(lines)
    return paths


def build_cases(workdir: str) -> list:
    """Return [(id, label, argv, want_status, want_stdout or None, stderr substring or None)]."""
    cases = []

    one = write_logs(workdir, {"one.log": [clf("10.0.0.1", "14/Jan/1999:10:00:01", "/a")]})
    cases.append(("F1", "single argument -> usage", [one["one.log"]],
                  1, b"", "usage: multisort LOGFILE1 LOGFILE2"))

    for check_id, year in (("F2", "1999"), ("F3", "2026")):
        a = [clf("10.0.0.1", f"14/Jan/{year}:10:00:01", "/a"),
             clf("10.0.0.1", f"14/Jan/{year}:10:00:05", "/c"),
             clf("10.0.0.1", f"02/Mar/{year}:00:00:00", "/e")]
        b = [clf("10.0.0.2", f"14/Jan/{year}:10:00:03", "/b"),
             clf("10.0.0.2", f"14/Jan/{year}:10:00:07", "/d"),
             clf("10.0.0.2", f"28/Oct/{year}:12:04:00", "/f")]
        p = write_logs(workdir, {f"{year}-a.log": a, f"{year}-b.log": b})
        want = [a[0], b[0], a[1], b[1], a[2], b[2]]
        cases.append((check_id, f"merge two logs dated {year}",
                      [p[f"{year}-a.log"], p[f"{year}-b.log"]],
                      0, "".join(want).encode(), None))

    months = [clf(f"10.0.1.{i % 3 + 1}", f"15/{m}/2025:12:00:00", f"/m{i + 1:02d}")
              for i, m in enumerate(MONTHS)]
    rollover = clf("10.0.1.3", "15/Jan/2026:12:00:00", "/m13")
    p = write_logs(workdir, {"q1.log": months[0::3],
                             "q2.log": months[1::3],
                             "q3.log": months[2::3] + [rollover]})
    cases.append(("F4", "three-way merge, Jan-Dec 2025 + Jan 2026",
                  [p["q1.log"], p["q2.log"], p["q3.log"]],
                  0, "".join(months + [rollover]).encode(), None))

    long_line = clf("10.0.2.1", "28/Oct/1999:10:00:01", "/long?q=" + "x" * 2900,
                    ' "-" "Mozilla/5.0 [FBAN/FBIOS;FBAV/1.0]"')
    after = clf("10.0.2.1", "28/Oct/1999:10:00:05", "/after")
    short = clf("10.0.2.2", "28/Oct/1999:10:00:03", "/short")
    p = write_logs(workdir, {"long.log": [long_line, after], "short.log": [short]})
    cases.append(("F5", f"{len(long_line)}-byte line passes intact",
                  [p["long.log"], p["short.log"]],
                  0, (long_line + short + after).encode(), None))

    missing = os.path.join(workdir, "does-not-exist.log")
    cases.append(("F6", "missing input file", [one["one.log"], missing],
                  1, b"", f"multisort: {missing}: No such file or directory"))

    empty = write_logs(workdir, {"empty.log": []})
    cases.append(("F7", "empty input file", [one["one.log"], empty["empty.log"]],
                  1, b"", "empty input file"))
    return cases


def functional_check(binary: str, argv: list, want_status: int,
                     want_out, want_err) -> str:
    """Return a failure message, or None when the run matches."""
    try:
        status, out, err = _run(binary, argv)
    except subprocess.TimeoutExpired:
        return f"still running after {TIMEOUT} s"
    except OSError as exc:
        return f"cannot launch: {exc}"
    problems = []
    if status != want_status:
        problems.append(f"exit status {status}, want {want_status}")
    if want_out is not None and out != want_out:
        problems.append(f"stdout {len(out)} bytes differs from the expected {len(want_out)} bytes "
                        f"(got {out[:120]!r})")
    if want_err is not None and want_err not in err:
        problems.append(f"stderr lacks {want_err!r} (got {err[:160]!r})")
    return "; ".join(problems) or None


def main(argv: list) -> int:
    if len(argv) != 3:
        print("usage: test_multisort.py <path/to/bin/multisort> <writable work directory>",
              file=sys.stderr)
        return 2
    binary, workroot = argv[1], argv[2]

    artifact_failed = 0
    for check_id, problem in artifact_checks(binary).items():
        _report("fail" if problem else "ok", check_id, problem or ARTIFACT[check_id])
        artifact_failed += problem is not None
    artifact_passed = len(ARTIFACT) - artifact_failed

    host = platform.machine().lower()
    os.makedirs(workroot, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="multisort-test-", dir=workroot) as workdir:
        cases = build_cases(workdir)
        if cannot_execute_here(binary):
            _report("skip", f"F1-F{len(cases)}", f"not run: this {host} host cannot execute the "
                    "aarch64 OHOS image (functional checks are mandatory on the aarch64 CI worker)")
            print(f"RESULT: artifact checks {artifact_passed}/{len(ARTIFACT)} passed, "
                  f"functional checks 0/{len(cases)} run (SKIPPED)")
            return 1 if artifact_failed else 0

        functional_failed = 0
        for check_id, label, args, want_status, want_out, want_err in cases:
            problem = functional_check(binary, args, want_status, want_out, want_err)
            _report("fail" if problem else "ok", check_id, f"{label}: {problem}" if problem else label)
            functional_failed += problem is not None
    functional_passed = len(cases) - functional_failed

    print(f"RESULT: artifact checks {artifact_passed}/{len(ARTIFACT)} passed, "
          f"functional checks {functional_passed}/{len(cases)} passed on {host}")
    return 1 if artifact_failed or functional_failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
