#!/usr/bin/env python3
"""cssmin consumer test (R34): real API — cssmin.cssmin() compression checks."""

import subprocess
import sys


CHECKS = [
    ("version", "__version__ == '0.2.0'", None),
    ("basic", "body { color: red; }", "body{color:red}"),
    ("comment+zero-unit", "/* comment */ body { margin: 0px; }", "body{margin:0}"),
    ("rgb-to-hex", "p { color: rgb(51, 102, 153); }", "p{color:#369}"),
    ("hex-condense", "a { color: #AABBCC; }", "a{color:#ABC}"),
    ("float-condense", "p { margin: 0.6em; }", "p{margin:.6em}"),
]


def main():
    import cssmin

    if cssmin.__version__ != "0.2.0":
        print("FAIL: version %r" % (cssmin.__version__,), file=sys.stderr)
        return 1
    print("PASS[1/6]: version 0.2.0")
    for idx, (name, src, expect) in enumerate(CHECKS[1:], start=2):
        out = cssmin.cssmin(src)
        if not out:
            print("FAIL: %s produced empty output" % name, file=sys.stderr)
            return 1
        if out != expect:
            print("FAIL: %s: got %r want %r" % (name, out, expect), file=sys.stderr)
            return 1
        print("PASS[%d/6]: %s -> %r" % (idx, name, out))
    # CLI entry point: cssmin.main() reads stdin, writes stdout.
    r = subprocess.run(
        [sys.executable, "-c", "import cssmin; cssmin.main()"],
        input="body { color: red; }",
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0 or r.stdout.strip() != "body{color:red}":
        print("FAIL: cli main(): rc=%d out=%r err=%r" % (r.returncode, r.stdout, r.stderr), file=sys.stderr)
        return 1
    print("PASS[6/6]: cli main() stdin->stdout")
    print("OK: cssmin 0.2.0 (6/6 checks passed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
