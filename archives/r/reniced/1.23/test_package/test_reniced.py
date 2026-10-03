#!/usr/bin/env python3
"""Consumer verification for the packaged reniced 1.23 Conan package.

Runs the packaged Perl interpreter against the packaged script:
  1. layout check of packaged artifacts
  2. `reniced -h` help output and version (packaged file, verbatim)
  3. upstream-equivalent no-op mode run of the packaged script with the
     ps command substituted through the packaged RENICED_PS_CMD override
     (the device forbids exec'ing newly created mock files, so the mock
     runs through an explicit interpreter)
"""
import os
import stat
import subprocess
import sys
import tempfile


EXPECTED_NOOP = [
    "would set priority of 201 to 5",
    "would set priority of 2445 to 5",
    "would set IO priority for pid 19966 to class 3",
    "would set priority of 1234567 to 3",
    "would adjust OOM setting of pid 1234567 to -10",
]

MOCK_PS = r'''shift @ARGV if @ARGV && $ARGV[0] eq 'ps';
my $argstring = join ':', '', @ARGV;
my $uid = $<;
if ($argstring eq ":H:-o:lwp,comm:--user:$uid") {
    print "     LWP COMMAND\n";
    print "     201 foo --quick\n";
    print "    2445 foo --slow\n";
    print "   19966 bar\n";
    print "   30176 bar --really --slow\n";
    print " 1234567 long-pid\n";
} else {
    print STDERR "ps called with unexpected parameters: ps$argstring\n";
    exit 1;
}
'''

TEST_CONF = (
    "# mocked consumer test rules (mirrors upstream test/test.conf)\n"
    "5\t^foo\n"
    "o-10n3\tlong-pid\n"
    "i\tbar$\n"
)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    package_folder = sys.argv[1]
    perl = sys.argv[2]

    reniced = os.path.join(package_folder, "bin", "reniced")
    conf = os.path.join(package_folder, "share", "reniced", "reniced.conf")
    license_file = os.path.join(package_folder, "licenses", "COPYRIGHT")
    doc = os.path.join(package_folder, "share", "doc", "reniced", "README.md")

    for path in (reniced, conf, license_file, doc):
        if not os.path.isfile(path):
            fail(f"missing packaged reniced artifact: {path}")
    print("PASS: packaged artifacts present (bin/reniced, conf, doc, license)")

    # packaged script must contain the documented RENICED_PS_CMD override
    with open(reniced, "r", encoding="utf-8") as fh:
        packaged = fh.read()
    if "RENICED_PS_CMD" not in packaged:
        fail("packaged reniced lacks the RENICED_PS_CMD override")
    print("PASS: packaged script contains RENICED_PS_CMD override")

    # help output, packaged file verbatim (no ps involved)
    proc = subprocess.run([perl, reniced, "-h"], capture_output=True, text=True)
    if proc.returncode != 0:
        fail(f"reniced -h exited {proc.returncode}: {proc.stderr}")
    if "Usage:" not in proc.stdout:
        fail("reniced -h output missing Usage block")
    print("PASS: reniced -h prints usage")
    if "reniced 1.23" not in proc.stdout:
        fail("reniced -h output missing version 1.23")
    print("PASS: reniced -h reports version 1.23")

    # upstream-equivalent no-op run of the packaged script with mocked ps
    with tempfile.TemporaryDirectory(prefix="reniced-consumer-") as tmp:
        mock_ps = os.path.join(tmp, "mock-ps.pl")
        with open(mock_ps, "w") as fh:
            fh.write(MOCK_PS)
        test_conf = os.path.join(tmp, "test.conf")
        with open(test_conf, "w") as fh:
            fh.write(TEST_CONF)

        env = dict(os.environ)
        env["RENICED_PS_CMD"] = f'"{perl}" "{mock_ps}"'

        proc = subprocess.run(
            [perl, reniced, "-n", test_conf],
            capture_output=True,
            text=True,
            env=env,
        )
        if proc.returncode != 0:
            fail(f"reniced -n exited {proc.returncode}: {proc.stdout}{proc.stderr}")
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        if lines != EXPECTED_NOOP:
            fail(f"no-op output differs from upstream expectation:\n{proc.stdout}\n{proc.stderr}")
        print("PASS: no-op run of packaged script matches upstream expected output")

    print("all reniced consumer checks passed")


if __name__ == "__main__":
    main()
