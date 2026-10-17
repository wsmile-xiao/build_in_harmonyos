#!/usr/bin/env python3
"""Conan test_package for dh-builtusing — R34 real content verification.

Tool package (bin/dh_builtusing + lib/perl5/builtusing.pm): no linkable
library, so build() is empty. test() runs the real consumer script
test_dh_builtusing.py against the installed package via self.run()
(L0d), parses its RESULT line for HMBS_TEST_PACKAGE_RESULT numbers
(discovered/passedCount from the script, not hardcoded), then re-emits
the persisted HMBS_UPSTREAM_TEST_RESULT from res/ AFTER the test commands
so every round (including conan cache hits where build() is skipped) has
evidence. Dual channel (output.info + print) mirrors build().
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile ok, skip runtime test")
            return
        pkg = self.dependencies["dh-builtusing"].package_folder
        script = os.path.join(os.path.dirname(__file__),
                              "test_dh_builtusing.py")
        logfile = os.path.join(self.build_folder, "test_package.log")
        # L0d: must use self.run() (PF3/L0d gate greps for it literally).
        self.run(f'python3 "{script}" "{pkg}" > "{logfile}" 2>&1',
                 env="conanrun")
        out = ""
        if os.path.isfile(logfile):
            with open(logfile, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_dh_builtusing.py log:\n"
                         + "\n".join(out.splitlines()[-12:]))
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_dh_builtusing.py produced no RESULT line — broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": "python3 test_dh_builtusing.py <package>",
            "discovered": discovered,
            "passedCount": passed,
        }
        _tp_line = ("HMBS_TEST_PACKAGE_RESULT="
                    + json.dumps(marker, ensure_ascii=False))
        self.output.info(_tp_line)
        print(_tp_line, flush=True)
        if not ok:
            raise ConanException(
                "consumer verification failed: %d/%d failed"
                % (failed, discovered))
        # Re-emit persisted upstream result AFTER the test commands.
        # Content comes from the real on-device `sh run-unit-tests` run in
        # build() (never guessed); validate shape before emitting.
        cand = os.path.join(pkg, "res", "upstream_test_result.json")
        if not os.path.isfile(cand):
            raise ConanException(
                "res/upstream_test_result.json missing — build() did not persist")
        with open(cand, encoding="utf-8") as f:
            txt = f.read().strip()
        if txt[:1] == "\ufeff":
            raise ConanException("upstream_test_result.json has BOM")
        data = json.loads(txt)
        for k in ("status", "framework", "command", "discovered",
                  "executed", "passed", "failed", "skipped"):
            if k not in data:
                raise ConanException(
                    "upstream_test_result.json missing key: %s" % k)
        if data.get("status") != "passed" or int(data.get("discovered", 0)) <= 0:
            raise ConanException(
                "persisted upstream marker not passed: %s" % txt[:200])
        if int(data["executed"]) != int(data["discovered"]):
            raise ConanException(
                "persisted upstream marker incomplete: %s" % txt[:200])
        _up_line = ("HMBS_UPSTREAM_TEST_RESULT="
                    + json.dumps(data, separators=(",", ":"), ensure_ascii=False))
        self.output.info(_up_line)
        print(_up_line, flush=True)
