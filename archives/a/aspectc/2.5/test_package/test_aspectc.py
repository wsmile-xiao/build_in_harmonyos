#!/usr/bin/env python3
"""Smoke test for aspectc 2.5: verify ac++/ag++ report the expected version.

Usage: test_aspectc.py <acxx> <agxx>
The woven-helloworld end-to-end check (weave -> strip .codesign -> sign ->
run) lives in conanfile.py's test() so it runs inside `conan test`.
"""

import subprocess
import sys


def main() -> None:
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} <acxx> <agxx>", file=sys.stderr)
        return 2

    acxx, agxx = sys.argv[1], sys.argv[2]

    ac_out = subprocess.run([acxx, "--version"], capture_output=True, text=True)
    assert ac_out.returncode == 0, ac_out
    assert "2.5" in (ac_out.stdout + ac_out.stderr), ac_out

    ag_out = subprocess.run([agxx, "--version"], capture_output=True, text=True)
    assert ag_out.returncode == 0, ag_out
    assert "2.5" in (ag_out.stdout + ag_out.stderr), ag_out

    print("aspectc 2.5 smoke test: ac++/ag++ version assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
