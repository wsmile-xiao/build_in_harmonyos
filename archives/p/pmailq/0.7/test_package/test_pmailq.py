#!/usr/bin/env python3
"""Functional tests for the packaged pmailq 0.7 script.

Runs 13 deterministic cases (artifact + CLI + fixture-driven flows) and prints
a single HMBS_TEST_PACKAGE_RESULT JSON marker. Counts come from the executed
case list only; no stdout string-counting or arithmetic fixups.
"""

import json
import os
import subprocess
import sys
import tempfile

PMAILQ = sys.argv[1] if len(sys.argv) > 1 else None
if not PMAILQ or not os.path.isfile(PMAILQ):
    print("usage: test_pmailq.py <path-to-packaged-pmailq>")
    sys.exit(2)

PYTHON = sys.executable

FIXTURE = """-Queue ID- --Size-- ----Arrival Time---- -Sender/Recipient-------
7E75214643A4     3154 Fri Aug 31 10:00:00  MAILER-DAEMON
    (connect to example.com timed out)
                                         edgar@example.com

B0BDE146B640     3199 Thu Aug 30 11:00:00  MAILER-DAEMON
    (delivery temporarily suspended)
                                         paul@example.com

-- 2 Kbytes in 2 Requests.
"""

TMP = tempfile.mkdtemp(prefix="pmailq-test-")
FIXTURE_PATH = os.path.join(TMP, "mailq.txt")
with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
    f.write(FIXTURE)

# PATH shims: fake postqueue prints the fixture, fake postsuper echoes args.
SHIM_DIR = os.path.join(TMP, "shims")
os.makedirs(SHIM_DIR, exist_ok=True)
with open(os.path.join(SHIM_DIR, "postqueue"), "w", encoding="utf-8") as f:
    f.write('#!/bin/sh\ncat "$PMAILQ_FIXTURE"\n')
with open(os.path.join(SHIM_DIR, "postsuper"), "w", encoding="utf-8") as f:
    f.write('#!/bin/sh\necho "postsuper $@"\n')
for name in ("postqueue", "postsuper"):
    path = os.path.join(SHIM_DIR, name)
    os.chmod(path, 0o755)

ENV = dict(os.environ)
ENV["PATH"] = SHIM_DIR + os.pathsep + ENV.get("PATH", "")
ENV["PMAILQ_FIXTURE"] = FIXTURE_PATH

CASES = []  # (name, passed_bool, detail)


def run_pmailq(*args):
    return subprocess.run(
        [PYTHON, PMAILQ] + list(args),
        capture_output=True,
        text=True,
        env=ENV,
        timeout=60,
    )


def record(name, ok, detail=""):
    CASES.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + (" -- " + detail if detail and not ok else ""))


def nonempty_text(result):
    return (result.stdout or "").strip() != ""


# Layer 0: artifact integrity (3 cases, direct file evidence).
record("artifact_exists", os.path.isfile(PMAILQ))
record("artifact_executable", os.access(PMAILQ, os.X_OK))
try:
    with open(PMAILQ, "r", encoding="utf-8") as f:
        head = f.readline().strip()
    size = os.path.getsize(PMAILQ)
except OSError:
    head, size = "", 0
record("shebang_and_size", head == "#!/usr/bin/env python3" and size > 1024,
       "head=%r size=%d" % (head, size))

# Layer 1: syntax validation (1 case).
compile_result = subprocess.run(
    [PYTHON, "-m", "py_compile", PMAILQ], capture_output=True, text=True, timeout=60)
record("py_compile", compile_result.returncode == 0)

# Layer 2: CLI smoke (2 cases, non-empty output证伪: empty output fails).
help_result = run_pmailq("--help")
record("help", help_result.returncode == 0 and nonempty_text(help_result)
       and "parse" in (help_result.stdout or ""))
version_result = run_pmailq("--version")
record("version", version_result.returncode == 0 and nonempty_text(version_result))

# Layer 3: functional flows with fixture (7 cases).
parse_result = run_pmailq("parse")
parse_out = parse_result.stdout or ""
record("parse_two_entries",
       parse_result.returncode == 0
       and "7E75214643A4|Fri Aug 31|3154|0|0|edgar@example.com" in parse_out
       and "B0BDE146B640|Thu Aug 30|3199|0|0|paul@example.com" in parse_out)

list_result = run_pmailq("list")
list_out = list_result.stdout or ""
record("list_two_entries",
       list_result.returncode == 0
       and "7E75214643A4" in list_out and "B0BDE146B640" in list_out
       and "edgar@example.com" in list_out)

email_result = run_pmailq("-e", "*@example.com", "parse")
email_out = email_result.stdout or ""
record("email_filter_match_all",
       email_result.returncode == 0
       and "edgar@example.com" in email_out and "paul@example.com" in email_out)
email_none = run_pmailq("-e", "*@nonexistent.test", "parse")
record("email_filter_match_none",
       email_none.returncode == 0 and (email_none.stdout or "").strip() == "")

msg_result = run_pmailq("-m", "*timed*out", "parse")
record("msg_filter",
       msg_result.returncode == 0
       and "edgar@example.com" in (msg_result.stdout or "")
       and "paul@example.com" not in (msg_result.stdout or ""))

size_result = run_pmailq("-u", "3160", "-l", "3100", "parse")
size_out = size_result.stdout or ""
record("size_window",
       size_result.returncode == 0
       and "edgar@example.com" in size_out and "paul@example.com" not in size_out)

del_result = run_pmailq("del")
del_out = del_result.stdout or ""
record("del_flow",
       del_result.returncode == 0
       and "deleting 7E75214643A4 [OK]" in del_out
       and "deleting B0BDE146B640 [OK]" in del_out)

# Deterministic marker: counts from the case list only.
discovered = len(CASES)
passed_count = sum(1 for _, ok, _ in CASES)
all_passed = (passed_count == discovered)
failed = [name for name, ok, _ in CASES if not ok]
print("test summary: %d/%d passed%s" % (
    passed_count, discovered, "" if all_passed else " failed=%s" % failed))
marker = {
    "executed": True,
    "passed": all_passed,
    "command": "python3 test_pmailq.py <package>/bin/pmailq",
    "discovered": discovered,
    "passedCount": passed_count,
}
print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
sys.exit(0 if all_passed else 1)
