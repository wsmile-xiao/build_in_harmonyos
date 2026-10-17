#!/usr/bin/env python3
"""libcapture-tiny-perl consumer test (R34): perl loads Capture::Tiny
(real module load — review P3 fix). perl may not be in PATH — use
absolute /data/service/hnp/bin/perl (CI env) with 'perl' fallback."""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    perl5 = os.path.join(sys.argv[1], "lib", "perl5")
    perl = "/data/service/hnp/bin/perl"
    if not os.path.isfile(perl):
        perl = "perl"
    cmd = [perl, "-I", perl5, "-MCapture::Tiny",
           "-e", "print 'ok'"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or "ok" not in r.stdout:
        print(f"FAIL: Capture::Tiny load: {r.stderr or r.stdout}",
              file=sys.stderr)
        return 1
    print("OK: Capture::Tiny loaded (perl -MCapture::Tiny)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
