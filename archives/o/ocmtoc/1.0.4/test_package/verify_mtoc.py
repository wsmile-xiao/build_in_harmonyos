"""Functional checks for the ocmtoc (mtoc) package.

Each check really executes the packaged `mtoc` binary and asserts on its
observable behavior (exit code + output content); nothing here is a stub.
Discovered/passed counts are reported by this script and mirrored into the
HMBS_TEST_PACKAGE_RESULT marker by the test conanfile.
"""
import subprocess
import sys
import os
import tempfile

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


# Absolute path of the packaged mtoc binary under test. Passed as argv[1]
# by the test conanfile (resolved from the dependency package_folder);
# env MTOC_BIN is honored as a fallback, bare-name PATH lookup only last.
MTOC_BIN = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.environ.get("MTOC_BIN", "mtoc")
)


def run_mtoc(*args, input_data=None):
    return subprocess.run(
        [MTOC_BIN, *args],
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@check("version prints 1.0.4 and exits 0")
def t_version():
    p = run_mtoc("--version")
    assert p.returncode == 0, "rc=%d stderr=%s" % (p.returncode, p.stderr)
    assert p.stdout.strip() == "1.0.4", "stdout=%r" % p.stdout


@check("fullversion prints upstream identity and exits 0")
def t_fullversion():
    p = run_mtoc("--fullversion")
    assert p.returncode == 0, "rc=%d stderr=%s" % (p.returncode, p.stderr)
    assert "Acidanthera ocmtoc 1.0.4" in p.stdout, "stdout=%r" % p.stdout


@check("garbage input fails with an error diagnostic")
def t_bad_input():
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "bad.bin")
        out = os.path.join(d, "bad.pe")
        with open(bad, "wb") as f:
            f.write(b"not-a-macho-binary")
        p = run_mtoc(bad, out)
        assert p.returncode != 0, "mtoc accepted a garbage input file"
        assert "error" in p.stderr.lower(), "stderr=%r" % p.stderr
        assert not os.path.exists(out), "output must not be created on failure"


def main():
    passed = 0
    for name, fn in CHECKS:
        try:
            fn()
        except Exception as e:
            print("FAIL: %s: %s" % (name, e))
        else:
            print("PASS: %s" % name)
            passed += 1
    print("mtoc verify: %d/%d passed" % (passed, len(CHECKS)))
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
