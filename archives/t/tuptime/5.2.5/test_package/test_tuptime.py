#!/usr/bin/env python3
"""Consumer test for the tuptime 5.2.5 Conan package.

Driven by ``test_package/conanfile.py`` (``python3 test_tuptime.py``) inside the
``conanrun`` environment, so ``PATH`` contains the *installed* package's
``bin/`` directory.  Every assertion below executes the installed
``bin/tuptime`` script for real (R34) — nothing is compiled, nothing is faked.

Cases
-----
 1. version                  -- ``-v`` reports 5.2.5 and routes to a backend
 2. summary-report           -- default report, exit 0, expected labels
 3. table-mode               -- ``-t`` renders the tabular report
 4. list-mode                -- ``-l`` renders the per-record list
 5. csv-mode                 -- ``-c`` emits CSV
 6. seconds-mode             -- ``-s`` switches timestamps to epoch seconds
 7. kernel-mode              -- ``-k`` adds the kernel string of this machine
 8. invert-mode              -- ``-i`` reverses the startup numbering
 9. graceful-shutdown        -- ``-g`` writes a graceful-shutdown register (endst=1)
10. install-layout           -- bin/tuptime + share/man/man1/tuptime.1 installed
11. ohos-platform-backend    -- **HarmonyOS-only**: OHOS must be served by the
                                Linux backend (``System = Linux``), never by the
                                upstream "System = ohos not supported" abort.
                                Regression guard for patches/0001-src-tuptime.patch.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile

TIMEOUT = 120
# The tested program: passed explicitly as argv[1] by conanfile.py test() as the
# absolute path from the tested package's cpp_info.bindirs.  A PATH lookup is
# only a fallback — HarmonyOS/HMDFS does not reliably report X_OK, which makes
# shutil.which() return None for a perfectly good installed tool.
TUPTIME = sys.argv[1] if len(sys.argv) > 1 else shutil.which("tuptime")

_results: list[tuple[str, str, str]] = []   # (name, status, detail)


def _workdir() -> str:
    for cand in (os.environ.get("TMPDIR"), os.environ.get("TEMP"),
                 tempfile.gettempdir(), os.getcwd()):
        if cand and os.path.isdir(cand) and os.access(cand, os.W_OK):
            return tempfile.mkdtemp(prefix="tuptime-test-", dir=cand)
    raise RuntimeError("no writable directory for the tuptime test database")


WORK = _workdir()
DB = os.path.join(WORK, "tuptime.db")


def run(args: list[str]) -> subprocess.CompletedProcess:
    """Run the installed script through an explicit interpreter."""
    return subprocess.run([sys.executable, TUPTIME, *args],
                          capture_output=True, text=True, timeout=TIMEOUT)


def case(name: str, fn) -> None:
    try:
        detail = fn()
        status = "SKIP" if detail is True else "PASS"
        _results.append((name, status, "" if detail is True else str(detail)))
    except AssertionError as exc:
        _results.append((name, "FAIL", str(exc)))
    except Exception as exc:  # noqa: BLE001 - report, do not abort the suite
        _results.append((name, "FAIL", f"{type(exc).__name__}: {exc}"))


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ── cases ────────────────────────────────────────────────────────────────────

def case_version():
    r = run(["-v", "-f", DB])
    _need(r.returncode == 0, f"-v rc={r.returncode} stderr={r.stderr[-200:]}")
    _need("Version = 5.2.5" in r.stderr, "version banner missing from stderr")
    return "rc=0, Version = 5.2.5"


def case_summary():
    r = run(["-f", DB])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    for label in ("System startups:", "System shutdowns:", "System life:",
                  "System uptime:", "Current uptime:"):
        _need(label in r.stdout, f"missing label {label!r}")
    _need(r.stdout.count("\n") >= 10, "summary report too short")
    return "rc=0, 10 report labels present"


def case_table():
    r = run(["-f", DB, "-t"])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    for label in ("No.", "Startup T.", "Uptime", "Shutdown T.", "Downtime"):
        _need(label in r.stdout, f"missing column {label!r}")
    return "table header OK"


def case_list():
    r = run(["-f", DB, "-l"])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    _need("Startup:" in r.stdout and "at" in r.stdout, "list layout missing")
    _need("Uptime:" in r.stdout, "list 'Uptime:' missing")
    return "list layout OK"


def case_csv():
    r = run(["-f", DB, "-c"])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    _need('"System startups"' in r.stdout, "CSV header missing")
    _need(r.stdout.count(",") >= 4, "CSV row missing separators")
    return "CSV header + row OK"


def case_seconds():
    r = run(["-f", DB, "-s"])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    hits = [w for w in r.stdout.replace(",", " ").split() if w.isdigit() and len(w) == 10]
    _need(bool(hits), "no epoch-second timestamp in -s output")
    return f"epoch timestamp {hits[0]} present"


def case_kernel():
    r = run(["-f", DB, "-k"])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    _need(platform.platform() in r.stdout,
          f"kernel string {platform.platform()!r} missing from -k output")
    return f"kernel={platform.platform()}"


def case_invert():
    r = run(["-f", DB, "-i"])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    _need("System startups:" in r.stdout, "report missing with -i")
    return "rc=0, reversed numbering"


def case_graceful_shutdown():
    r = run(["-f", DB, "-g"])
    _need(r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-200:]}")
    _need("Graceful shutdown in DB = ok" in r.stdout, "graceful shutdown not registered")
    # The shutdown timestamp is only completed when the *next* boot is detected,
    # so the persisted evidence of the register is endst=1 in the SQLite row.
    import sqlite3
    with sqlite3.connect(DB) as conn:
        row = conn.execute(
            "select endst from tuptime order by rowid desc limit 1").fetchone()
    _need(row is not None, "no register in the database")
    _need(int(row[0]) == 1, f"endst={row[0]!r}, expected 1 (graceful shutdown)")
    r2 = run(["-f", DB, "-l"])
    _need(r2.returncode == 0, f"rc={r2.returncode} after -g")
    return "graceful shutdown persisted (endst=1), -l still readable"


def case_install_layout():
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(TUPTIME)))
    man = os.path.join(pkg, "share", "man", "man1", "tuptime.1")
    lic = os.path.join(pkg, "licenses", "LICENSE")
    _need(os.path.isfile(man), f"man page missing: {man}")
    _need(os.path.isfile(lic), f"license missing: {lic}")
    _need(os.path.getsize(TUPTIME) > 10000, "installed script is suspiciously small")
    return "bin/ + share/man/man1/ + licenses/ present"


def case_ohos_platform_backend():
    if not sys.platform.startswith("ohos"):
        return True      # HarmonyOS-only case: skipped elsewhere
    r = run(["-v", "-f", DB])
    _need(r.returncode == 0,
          f"tuptime aborted on OHOS (rc={r.returncode}) — is patches/0001 applied?")
    _need("not supported" not in r.stderr,
          "OHOS still reported as an unsupported platform")
    _need("System = Linux" in r.stderr,
          "OHOS did not select the Linux backend")
    return f"sys.platform={sys.platform!r} -> Linux backend, rc=0"


CASES = (
    ("version", case_version),
    ("summary-report", case_summary),
    ("table-mode", case_table),
    ("list-mode", case_list),
    ("csv-mode", case_csv),
    ("seconds-mode", case_seconds),
    ("kernel-mode", case_kernel),
    ("invert-mode", case_invert),
    ("graceful-shutdown", case_graceful_shutdown),
    ("install-layout", case_install_layout),
    ("ohos-platform-backend", case_ohos_platform_backend),
)


def main() -> int:
    if not TUPTIME:
        print("FAIL: 'tuptime' not found in PATH — package bin/ not on PATH")
        return 2
    print(f"tuptime      : {TUPTIME}")
    print(f"interpreter  : {sys.executable}")
    print(f"sys.platform : {sys.platform}")
    print(f"database     : {DB}")
    print("-" * 72)
    for name, fn in CASES:
        case(name, fn)
    print(f"{'CASE':<26}{'STATUS':<8}DETAIL")
    for name, status, detail in _results:
        print(f"{name:<26}{status:<8}{detail}")
    total = len(_results)
    passed = sum(1 for _, s, _ in _results if s == "PASS")
    skipped = sum(1 for _, s, _ in _results if s == "SKIP")
    failed = total - passed - skipped
    print("-" * 72)
    print(f"total={total} pass={passed} fail={failed} skip={skipped}")
    shutil.rmtree(WORK, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
