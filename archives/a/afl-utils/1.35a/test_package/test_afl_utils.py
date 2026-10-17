#!/usr/bin/env python3
"""Consumer smoke + functional test for the installed afl-utils package.

Usage:
    test_afl_utils.py <pkg>/bin <pkg>/lib/pythonX.Y/site-packages

Verifies, all through real subprocess execution (no mocks, no stubs):
  1. every console tool ships in bin/, runs and prints its usage (`-h`, exit 0);
  2. the `afl_utils` and `db_connectors` Python packages import;
  3. `afl-stats` parses a fuzzer_stats file and dumps a SQLite database
     containing an `aflutils_fuzzerstats` row (data-parsing + DbConnector path).

All temporary fixtures are created under a private temp directory (never in
the source tree) and removed before exit. Emits a machine-readable
``ASSERTIONS: passed=<n> failed=<m> total=<t>`` summary line; exits non-zero,
printing every failure, if any check does not hold.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

TOOLS = [
    "afl-collect", "afl-cron", "afl-minimize", "afl-multicore",
    "afl-multikill", "afl-stats", "afl-sync", "afl-vcrash",
]

FUZZER_STATS = """\
start_time        : 1475080845
last_update       : 1475081950
fuzzer_pid        : 9999999
cycles_done       : 0
execs_done        : 372033733
execs_per_sec     : 1546.82
paths_total       : 420
paths_favored     : 25
paths_found       : 0
paths_imported    : 83
max_depth         : 39
cur_path          : 650
pending_favs      : 0
pending_total     : 0
variable_paths    : 0
stability         : 100.00%
bitmap_cvg        : 18.37%
unique_crashes    : 0
unique_hangs      : 13
last_path         : 1475081940
last_crash        : 0
last_hang         : 0
execs_since_crash : 63393
exec_timeout      : 800
afl_banner        : target_000
afl_version       : 2.35b
command_line      : afl-fuzz -T target_000 -i ./in -o ./out -- ./target
"""


def run(cmd, env, cwd=None):
    return subprocess.run(
        cmd, env=env, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
    )


def main():
    bindir, site = sys.argv[1], sys.argv[2]
    env = dict(os.environ)
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    env["PYTHONPATH"] = site + os.pathsep + env.get("PYTHONPATH", "")
    failures = []
    passed = 0

    # Private scratch dir (keeps the source tree pristine).
    try:
        work = tempfile.mkdtemp(prefix="afl-utils-test-")
    except OSError:
        work = os.path.join(os.path.expanduser("~"), ".afl-utils-test-%d" % os.getpid())
        os.makedirs(work, exist_ok=True)

    try:
        # 1) console tools present and functional (usage banner).
        for tool in TOOLS:
            exe = os.path.join(bindir, tool)
            if not os.path.isfile(exe):
                failures.append(f"{tool}: not packaged at {exe}")
                continue
            res = run([exe, "-h"], env, cwd=work)
            out = res.stdout.decode("utf-8", "replace")
            if res.returncode != 0 or "usage" not in out.lower():
                failures.append(f"{tool} -h: exit={res.returncode} {out[:200]!r}")
            else:
                passed += 1
                print(f"PASS: {tool} -h -> usage banner (exit 0)")

        # 2) packages are importable from the packaged site-packages.
        for mod in ("afl_utils", "db_connectors"):
            res = run([sys.executable, "-c", f"import {mod}"], env, cwd=work)
            if res.returncode != 0:
                failures.append(f"import {mod} failed: "
                                + res.stdout.decode("utf-8", "replace")[:200])
            else:
                passed += 1
                print(f"PASS: import {mod}")

        # 3) functional: afl-stats parses fuzzer_stats and dumps SQLite.
        fuzzdir = os.path.join(work, "fuzzdir")
        os.makedirs(os.path.join(fuzzdir, "fuzz000"), exist_ok=True)
        with open(os.path.join(fuzzdir, "fuzz000", "fuzzer_stats"), "w") as fh:
            fh.write(FUZZER_STATS)
        conf = os.path.join(work, "afl-stats.conf")
        with open(conf, "w") as fh:
            fh.write('{"fuzz_dirs": ["%s"]}\n' % fuzzdir)
        db = os.path.join(work, "afl-stats.db")
        res = run([os.path.join(bindir, "afl-stats"), "-q", "-c", conf, "-d", db],
                  env, cwd=work)
        if res.returncode != 0:
            failures.append("afl-stats -d failed: "
                            + res.stdout.decode("utf-8", "replace")[:300])
        elif not os.path.isfile(db):
            failures.append("afl-stats did not create the SQLite database")
        else:
            con = sqlite3.connect(db)
            try:
                tables = [r[0] for r in con.execute(
                    "select name from sqlite_master where type='table'")]
                if "aflutils_fuzzerstats" not in tables:
                    failures.append(f"unexpected tables in stats db: {tables}")
                else:
                    rows = list(con.execute(
                        "select count(*) from aflutils_fuzzerstats"))
                    if not rows or rows[0][0] < 1:
                        failures.append("aflutils_fuzzerstats has no rows")
                    else:
                        passed += 1
                        print("PASS: afl-stats dumped %d row(s) to SQLite "
                              "(aflutils_fuzzerstats)" % rows[0][0])
            finally:
                con.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # Machine-readable summary (kept in sync with MANIFEST.yml assertion_count).
    print("\nASSERTIONS: passed=%d failed=%d total=%d"
          % (passed, len(failures), passed + len(failures)))
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print("\nALL AFL-UTILS CONSUMER TESTS PASSED")


if __name__ == "__main__":
    main()
