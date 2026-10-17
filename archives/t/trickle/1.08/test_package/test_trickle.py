#!/usr/bin/env python3
"""Consumer test driver for trickle 1.08.

Executes the real packaged binaries' argument-parsing entry points only:

- case 1: `trickle -V`  -> "version 1.08" printed (exit code 1, upstream
           errx() behavior)
- case 2: `trickle -h`  -> usage text with -d/-u/-s options (exit 1)
- case 3: `trickle` no args -> usage (exit 1)
- case 4: `trickled -h` -> usage (exit 1)
- case 5: `tricklectl -h` -> usage (exit 1)

Safety boundaries:
- No daemon start (trickled is only asked for -h; it never binds its
  unix socket).
- No LD_PRELOAD launch: shaping behavior (trickle -s <cmd>) requires
  dlopen/dlsym of the musl libc on the OHOS target and is validated in
  the on-device shadow CI phase, not here.
- No network traffic, no root, no writes outside TMPDIR.
"""

import subprocess
import sys

case_count = 0
assertion_count = 0
passed = 0
failed = 0


def check(cond, desc):
    global assertion_count, passed, failed
    assertion_count += 1
    if cond:
        passed += 1
        print(f"  [PASS] {desc}")
    else:
        failed += 1
        print(f"  [FAIL] {desc}")


def run_cmd(cmd, timeout=30):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def check_usage(binpath, label, must_contain):
    global case_count
    case_count += 1
    print(f"[case] {label} -h")
    rc, out, err = run_cmd([binpath, "-h"])
    text = (out + err).strip()
    check(rc == 1, f"{label} -h exits 1 (rc={rc})")
    check("Usage" in text or "usage" in text.lower(),
          f"{label} -h prints usage (got: {text[:80]!r})")
    for token in must_contain:
        check(token in text, f"{label} -h mentions {token!r}")


def main():
    if len(sys.argv) != 4:
        print("usage: test_trickle.py <trickle-bin> <trickled-bin> <tricklectl-bin>")
        return 2
    trickle, trickled, tricklectl = sys.argv[1], sys.argv[2], sys.argv[3]

    # case 1: version entry point (upstream: errx(1, "version " VERSION))
    global case_count
    case_count += 1
    print("[case] trickle -V")
    rc, out, err = run_cmd([trickle, "-V"])
    check("version 1.08" in (out + err),
          f"trickle -V prints 'version 1.08' (got: {(out + err).strip()!r})")
    check(rc == 1, f"trickle -V exit code 1 per upstream errx (rc={rc})")

    # case 2: trickle usage
    check_usage(trickle, "trickle", ["-d <rate>", "-u <rate>", "-s"])

    # case 3: no args -> usage
    case_count += 1
    print("[case] trickle (no args)")
    rc, out, err = run_cmd([trickle])
    check(rc == 1, f"trickle with no args exits 1 (rc={rc})")
    check("Usage" in (out + err), "no-args prints usage")

    # case 4/5: trickled / tricklectl usage
    check_usage(trickled, "trickled", [])
    # tricklectl 的 usage() 上游即空实现（仅 exit(1)，无任何输出）
    case_count += 1
    print("[case] tricklectl -h")
    rc, out, err = run_cmd([tricklectl, "-h"])
    check(rc == 1, f"tricklectl -h exits 1 (rc={rc})")
    check((out + err).strip() == "",
          f"tricklectl -h prints nothing per upstream usage() (got: {(out + err).strip()!r})")

    print()
    print(f"RESULT: passed={passed} failed={failed} total={assertion_count} "
          f"(case_count={case_count}, assertion_count={assertion_count})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
