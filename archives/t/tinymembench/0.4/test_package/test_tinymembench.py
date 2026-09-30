#!/usr/bin/env python3
"""Conan test_package for tinymembench 0.4.

tinymembench ships no unit-test suite, so this test exercises the *installed*
package from a consumer's perspective: it runs the packaged benchmark binary
end-to-end (full bandwidth + latency run, several minutes) and asserts on the
structure and content of its output:

  * the version banner "tinymembench v0.4",
  * the memory-bandwidth section header,
  * at least 10 measured bandwidth lines ("... :  NNN.N MB/s") — the C set
    alone has 13 entries,
  * the latency section header "block size : single random read",
  * at least one latency data row, and
  * a clean exit (return code 0, no signal).

Running the packaged bin/tinymembench (not the source tree) proves the
installed artifact is present, executable and functional.
"""
import re
import signal
import subprocess
import sys

BANNER = "tinymembench v0.4"
BANDWIDTH_HEADER = "Memory bandwidth tests"
LATENCY_HEADER = "block size : single random read"
MBPS_LINE = re.compile(r":\s+[0-9]+\.[0-9]+ MB/s")
# Full run: adaptive repeats per test, 64 MiB latency buffers, hugepage and
# non-hugepage variants. Several minutes on real hardware — allow 20 min.
TIMEOUT = 1200


def main(exe):
    if not exe.endswith("tinymembench"):
        # allow either path to bin/ or the binary itself
        import os
        exe = os.path.join(exe, "tinymembench")
    try:
        result = subprocess.run(
            [exe],
            timeout=TIMEOUT,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        print("FAIL: tinymembench timed out after %ss" % TIMEOUT, file=sys.stderr)
        return 1
    except OSError as exc:
        print("FAIL: could not execute tinymembench: %s" % exc, file=sys.stderr)
        return 1

    if result.returncode < 0:
        sig = signal.Signals(-result.returncode).name
        print("FAIL: terminated by signal %s" % sig, file=sys.stderr)
        return 1
    if result.returncode != 0:
        print("FAIL: exited with %d" % result.returncode, file=sys.stderr)
        print(result.stdout[-2000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        return 1

    out = result.stdout
    failures = []

    if BANNER not in out:
        failures.append("missing banner %r" % BANNER)
    if BANDWIDTH_HEADER not in out:
        failures.append("missing bandwidth section header")
    mbps = MBPS_LINE.findall(out)
    if len(mbps) < 10:
        failures.append("only %d bandwidth lines (<10): %s" % (len(mbps), mbps))
    if LATENCY_HEADER not in out:
        failures.append("missing latency section header")
    # latency data rows look like "      1024 :   12.3 ns          /   45.6 ns"
    if not re.search(r"^\s+\d+ :\s+[0-9]+\.[0-9]+ ns", out, re.M):
        failures.append("no latency data rows")

    if failures:
        for f in failures:
            print("FAIL: %s" % f, file=sys.stderr)
        print("---- stdout tail ----", file=sys.stderr)
        print(out[-3000:], file=sys.stderr)
        return 1

    print("OK: banner, bandwidth (%d lines), latency sections all present, exit 0"
          % len(mbps))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
