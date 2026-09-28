#!/usr/bin/env python3
"""Native functional tests for schedtool 1.3.0, using only the Python stdlib.

All setters target the newly launched schedtool process (PID 0), or that
process before it execs a Python probe. No existing process is modified.
Missing native scheduling APIs are test failures, never successful skips.
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


PROBE_PREFIX = "SCHEDTOOL_PROBE:"


def process_state():
    return {
        "pid": os.getpid(),
        "policy": os.sched_getscheduler(0),
        "priority": os.sched_getparam(0).sched_priority,
        "nice": os.getpriority(os.PRIO_PROCESS, 0),
        "affinity": sorted(os.sched_getaffinity(0)),
    }


class TestFailure(Exception):
    pass


class Suite:
    def __init__(self, binary, timeout):
        self.binary = binary
        self.timeout = timeout
        self.results = []
        self.assertions = 0
        self.commands = []
        self.baseline = None
        self.probe = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), "--probe"]

    def require(self, condition, message):
        self.assertions += 1
        if not condition:
            raise TestFailure(message)

    def run(self, arguments):
        command = [self.binary] + list(arguments)
        environment = os.environ.copy()
        environment.update({"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "1"})
        start = time.monotonic()
        record = {"argv": command}
        self.commands.append(record)
        try:
            completed = subprocess.run(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                env=environment, timeout=self.timeout, check=False,
            )
        except subprocess.TimeoutExpired as error:
            def text(value):
                return value.decode("utf-8", "replace") if isinstance(value, bytes) else (value or "")
            record.update({"timed_out": True, "stdout": text(error.stdout), "stderr": text(error.stderr)})
            raise TestFailure("command exceeded %.1f seconds" % self.timeout) from error
        finally:
            record["duration_seconds"] = round(time.monotonic() - start, 6)
        record.update({"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
        return completed

    def successful(self, arguments):
        result = self.run(arguments)
        self.require(result.returncode == 0, "expected exit 0, got %d" % result.returncode)
        self.require("ERROR:" not in result.stdout + result.stderr, "schedtool reported an error despite exit 0")
        return result

    def rejected(self, arguments, message):
        result = self.run(arguments)
        self.require(result.returncode != 0, "invalid request unexpectedly returned exit 0")
        self.require(message in result.stdout + result.stderr, "missing rejection diagnostic: " + message)

    def execute_probe(self, options, expected_exit=0, arguments=(), nice=None, affinity=None):
        result = self.run(list(options) + ["-e"] + self.probe + [str(expected_exit)] + list(arguments))
        self.require(result.returncode == expected_exit, "exec exit status was not preserved")
        self.require("ERROR:" not in result.stdout + result.stderr, "schedtool reported an error before exec")
        lines = [line[len(PROBE_PREFIX):] for line in result.stdout.splitlines() if line.startswith(PROBE_PREFIX)]
        self.require(len(lines) == 1, "expected exactly one completed Python probe")
        state = json.loads(lines[0])
        self.require(state["pid"] > 0 and state["pid"] != os.getpid(), "probe did not run in a separate process")
        self.require(state["arguments"] == list(arguments), "exec changed command arguments")
        self.require(state["policy"] == os.SCHED_OTHER, "independent policy readback differs from SCHED_OTHER")
        self.require(state["priority"] == 0, "normal policy has unexpected static priority")
        self.require(state["nice"] == (self.baseline["nice"] if nice is None else nice), "independent nice readback differs")
        self.require(state["affinity"] == (self.baseline["affinity"] if affinity is None else affinity), "independent affinity readback differs")

    def prerequisites(self):
        self.require(Path(self.binary).is_absolute(), "--binary must be an absolute path")
        self.require(Path(self.binary).is_file(), "schedtool binary does not exist: " + self.binary)
        self.require(os.access(self.binary, os.X_OK), "schedtool binary is not executable")
        required = (
            "SCHED_OTHER", "PRIO_PROCESS", "sched_getscheduler", "sched_getparam",
            "sched_get_priority_min", "sched_get_priority_max", "getpriority", "sched_getaffinity",
        )
        missing = [name for name in required if not hasattr(os, name)]
        self.require(not missing, "Python/native platform lacks required readback APIs: " + ", ".join(missing))
        self.baseline = process_state()
        self.require(os.SCHED_OTHER == 0, "this schedtool version requires native SCHED_OTHER == 0")
        self.require(self.baseline["policy"] == os.SCHED_OTHER and self.baseline["priority"] == 0,
                     "run the suite from an ordinary SCHED_OTHER process, not a realtime process")
        self.require(bool(self.baseline["affinity"]), "native process has no allowed CPUs")
        self.require(all(0 <= cpu < 1024 for cpu in self.baseline["affinity"]),
                     "CPU IDs exceed schedtool 1.3.0's supported 1024-bit affinity set")
        self.require(-20 <= self.baseline["nice"] <= 19, "native nice range is incompatible with these tests")

    def help(self, option="-h"):
        result = self.successful([option])
        self.require("v1.3.0" in result.stdout and "USAGE:" in result.stdout, "help/version text missing")
        self.require("-e COMMAND" in result.stdout and "-a AFFINITY_MASK" in result.stdout, "documented command modes missing")

    def version(self, option):
        result = self.successful([option])
        self.require(result.stdout == "schedtool 1.3.0\n", "unexpected exact version output")

    def no_arguments(self):
        result = self.successful([])
        self.require("v1.3.0" in result.stdout and "USAGE:" in result.stdout, "no-argument usage missing")

    def policy_probe(self):
        result = self.successful(["-r"])
        labels = ("N: SCHED_NORMAL", "F: SCHED_FIFO", "R: SCHED_RR", "B: SCHED_BATCH", "I: SCHED_ISO", "D: SCHED_IDLEPRIO")
        for label in labels:
            self.require(re.search(r"^" + re.escape(label) + r"\s*:\s*(?:prio_min -?\d+, prio_max -?\d+|policy not implemented)$", result.stdout, re.MULTILINE),
                         "missing or malformed policy capability row: " + label)
        minimum = os.sched_get_priority_min(os.SCHED_OTHER)
        maximum = os.sched_get_priority_max(os.SCHED_OTHER)
        self.require(re.search(r"^N: SCHED_NORMAL\s*:\s*prio_min %d, prio_max %d$" % (minimum, maximum), result.stdout, re.MULTILINE),
                     "normal policy limits differ from independent native query")

    def query_self(self):
        result = self.successful(["0"])
        match = re.search(r"^PID\s+0: PRIO\s+(-?\d+), POLICY\s+N: SCHED_NORMAL\s*, NICE\s+(-?\d+), AFFINITY 0x([0-9a-fA-F]+)$", result.stdout, re.MULTILINE)
        self.require(match is not None, "query lacks real scheduling/affinity values; exit 0 alone is insufficient")
        self.require(int(match.group(1)) == self.baseline["priority"], "queried static priority differs")
        self.require(int(match.group(2)) == self.baseline["nice"], "queried nice differs")
        expected_mask = sum(1 << cpu for cpu in self.baseline["affinity"])
        self.require(int(match.group(3), 16) == expected_mask, "queried CPU mask differs from native affinity")

    def affinity_list(self):
        cpus = self.baseline["affinity"][:2]
        self.execute_probe(["-a", ",".join(str(cpu) for cpu in cpus)], affinity=cpus)

    def affinity_hex(self):
        cpus = self.baseline["affinity"][:2]
        mask = sum(1 << cpu for cpu in cpus)
        self.execute_probe(["-a", hex(mask)], affinity=cpus)

    def combined(self):
        cpus = [self.baseline["affinity"][0]]
        self.execute_probe(["-N", "-n", "19", "-a", str(cpus[0])], nice=19, affinity=cpus)

    def case(self, name, function):
        self.commands = []
        before = self.assertions
        start = time.monotonic()
        record = {"name": name}
        try:
            function()
            record["status"] = "passed"
        except Exception as error:
            record.update({"status": "failed", "error": "%s: %s" % (type(error).__name__, error)})
        record.update({"assertions": self.assertions - before, "commands": self.commands,
                       "duration_seconds": round(time.monotonic() - start, 6)})
        self.results.append(record)
        print("[%s] %s%s" % (record["status"].upper(), name, ": " + record["error"] if "error" in record else ""), flush=True)
        return record["status"] == "passed"

    def run_all(self):
        cases = [
            ("help", self.help),
            ("long_help", lambda: self.help("--help")),
            ("long_version", lambda: self.version("--version")),
            ("short_version", lambda: self.version("-V")),
            ("no_arguments", self.no_arguments),
            ("policy_probe_read_only", self.policy_probe),
            ("query_own_process", self.query_self),
            ("invalid_option", lambda: self.rejected(["-Z"], "USAGE:")),
            ("exec_requires_scheduling_parameters", lambda: self.rejected(["-e"], "Option -e needs scheduling-parameters")),
            ("normal_exec_arguments", lambda: self.execute_probe(["-N"], arguments=("value with spaces", "--literal-option", "\u53c2\u6570"))),
            ("exec_exit_status", lambda: self.execute_probe(["-N"], expected_exit=37)),
            ("nice_19_readback", lambda: self.execute_probe(["-n", "19"], nice=19)),
            ("affinity_list_readback", self.affinity_list),
            ("affinity_hex_readback", self.affinity_hex),
            ("combined_normal_nice_affinity", self.combined),
            ("invalid_raw_policy", lambda: self.rejected(["-M", "-1", "0"], "could not set PID 0 to raw policy #-1")),
            ("invalid_normal_priority", lambda: self.rejected(["-N", "-p", "1", "0"], "could not set PID 0 to N: SCHED_NORMAL")),
        ]
        if self.case("prerequisites", self.prerequisites):
            for name, function in cases:
                self.case(name, function)
        else:
            self.results.extend({"name": name, "status": "not_run", "reason": "required native prerequisite failed"} for name, _ in cases)
        counts = {status: sum(result["status"] == status for result in self.results) for status in ("passed", "failed", "not_run")}
        report = {
            "schema_version": 1,
            "package": "schedtool/1.3.0",
            "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "binary": self.binary,
            "validation_scope": "native execution on the recorded host only",
            "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "python": platform.python_version()},
            "baseline": self.baseline,
            "notes": ["nice 19 is a no-op when the inherited nice value is already 19"] if self.baseline and self.baseline["nice"] == 19 else [],
            "summary": dict(counts, total=len(self.results), assertions=self.assertions),
            "results": self.results,
        }
        report["status"] = "passed" if not counts["failed"] and not counts["not_run"] else "failed"
        return report


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--probe":
        state = process_state()
        state["arguments"] = sys.argv[3:]
        print(PROBE_PREFIX + json.dumps(state, sort_keys=True), flush=True)
        return int(sys.argv[2])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, help="absolute path to the schedtool binary under test")
    parser.add_argument("--report", type=Path, help="write detailed JSON results (parent directory must exist)")
    parser.add_argument("--timeout", type=float, default=15.0, help="timeout in seconds for each command (default: 15)")
    args = parser.parse_args()
    if not (0 < args.timeout < float("inf")):
        parser.error("--timeout must be finite and positive")
    report = Suite(args.binary, args.timeout).run_all()
    if args.report:
        try:
            args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as error:
            print("cannot write JSON report: %s" % error, file=sys.stderr)
            return 1
    summary = report["summary"]
    print("%s: %d passed, %d failed, %d not run; %d assertions" % (report["status"].upper(), summary["passed"], summary["failed"], summary["not_run"], summary["assertions"]))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
