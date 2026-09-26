#!/usr/bin/env python3
"""Consumer smoke + functional test for the installed undertime package.

Usage:
    test_undertime_pkg.py <pkg>/bin <pkg>/lib/pythonX.Y/site-packages

Verifies, all through real subprocess execution (no mocks, no stubs):
  1. the console script ships in bin/, is executable and carries a portable
     shebang (the upstream `#!/usr/bin/python3` does not exist here);
  2. `undertime --version` reports the packaged version (exercises the
     dist-info metadata lookup);
  3. `undertime` computes the real aligned timezone table for a fixed date;
  4. every vendored runtime dependency imports from the packaged
     site-packages.

Emits a machine-readable ``ASSERTIONS: passed=<n> failed=<m> total=<t>``
summary line and exits non-zero, printing every failure, if any check fails.
"""
import os
import subprocess
import sys
import tempfile

# Runtime closure vendored into the package (pure-Python set; the C-extension
# ones — dateparser's regex, ephem — are excluded because the OHOS CI sandbox
# cannot dlopen them), imported from the packaged site-packages only.
VENDORED_MODULES = [
    "pytz", "yaml", "termcolor", "tabulate", "tzlocal", "tzdata",
    "dateutil",
]

DATE = "2020-03-08 12:00:00+00:00"


def run(cmd, env, cwd=None, timeout=180):
    return subprocess.run(
        cmd, env=env, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
    )


def main():
    bindir, site = sys.argv[1], sys.argv[2]
    env = dict(os.environ)
    # The packaged scripts use `#!/usr/bin/env python3`: make sure that lookup
    # succeeds even in a bare test environment.
    env["PATH"] = os.pathsep.join(
        [os.path.dirname(sys.executable), bindir, env.get("PATH", "")])
    env["PYTHONPATH"] = os.pathsep.join([site, env.get("PYTHONPATH", "")])
    env["TZ"] = "UTC"

    failures = []
    passed = 0

    work = tempfile.mkdtemp(prefix="undertime-test-")

    def check(ok, label, detail=""):
        nonlocal passed
        if ok:
            passed += 1
            print(f"PASS: {label}")
        else:
            failures.append(f"{label}: {detail}")

    try:
        # 1) script packaged, executable, portable shebang.
        for name in ("undertime",):
            exe = os.path.join(bindir, name)
            if not os.path.isfile(exe):
                failures.append(f"{name}: not packaged at {exe}")
                continue
            check(os.access(exe, os.X_OK), f"{name} is executable")
            with open(exe, encoding="utf-8") as fh:
                first = fh.readline().rstrip("\n")
            check(first == "#!/usr/bin/env python3",
                  f"{name} has a portable shebang", repr(first))

        # 2) --version resolves through the packaged dist-info metadata.
        res = run([os.path.join(bindir, "undertime"), "--version"], env, cwd=work)
        out = res.stdout.decode("utf-8", "replace").strip()
        check(res.returncode == 0 and out.endswith("4.3.1"),
              "undertime --version reports 4.3.1",
              f"exit={res.returncode} out={out[:200]!r}")

        # 3) functional: real table for a fixed date across three zones.
        res = run([os.path.join(bindir, "undertime"),
                   "--config", "/dev/null", "--no-default",
                   "--date", DATE,
                   "--timezone", "UTC", "Europe/Paris", "America/New_York"],
                  env, cwd=work)
        out = res.stdout.decode("utf-8", "replace")
        check(res.returncode == 0 and "UTC" in out and "overlap" in out
              and "╔" in out,
              "undertime prints the aligned timezone table",
              f"exit={res.returncode} out={out[:300]!r}")

        # 4) vendored runtime dependencies import from the packaged site.
        for mod in VENDORED_MODULES:
            res = run([sys.executable, "-c",
                       f"import sys; sys.path.insert(0, {site!r}); import {mod}"],
                      env, cwd=work)
            check(res.returncode == 0, f"vendored import {mod}",
                  res.stdout.decode("utf-8", "replace")[:200])
    finally:
        try:
            os.rmdir(work)
        except OSError:
            pass

    print("\nASSERTIONS: passed=%d failed=%d total=%d"
          % (passed, len(failures), passed + len(failures)))
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print("\nALL UNDERTIME CONSUMER TESTS PASSED")


if __name__ == "__main__":
    main()
