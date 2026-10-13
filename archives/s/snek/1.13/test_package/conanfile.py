#!/usr/bin/env python3
"""Conan test_package for snek 1.13 (consumer view, Conan L1 test).

Runs the packaged ``snek`` binary on ``test_snek.py`` (6 CHECK-OK
assertions covering arithmetic, strings, lists, dicts, loops/functions
and the math builtin) plus a ``snek --version`` smoke check, for 7
consumer checks total. Counts come from two deterministic files: the
expected CHECK-OK total is asserted against the script source itself,
and the achieved total is counted from the redirected run log — never
from grepping stdout. The real upstream result carried in the package
``res/`` is re-emitted so cache-hit runs still provide evidence.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


# test_snek.py contains exactly this many check() calls, each printing
# one "CHECK-OK: <name>" line on success.
CONSUMER_SCRIPT_CHECKS = 6


class SnekTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _count_prefix_lines(self, path, prefix):
        count = 0
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith(prefix):
                    count += 1
        return count

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer compiled fine, skip run")
            return
        script = os.path.join(self.source_folder, "test_snek.py")
        calls = self._count_prefix_lines(script, "check(")
        if calls != CONSUMER_SCRIPT_CHECKS:
            raise ConanException(
                "consumer script drift: %d check() calls, expected %d"
                % (calls, CONSUMER_SCRIPT_CHECKS))
        discovered = CONSUMER_SCRIPT_CHECKS + 1  # +1 for the --version smoke check

        log = os.path.join(self.build_folder, "test_snek.log")
        self.run('snek test_snek.py > "%s" 2>&1' % log,
                 env="conanrun", cwd=self.source_folder)
        passed_count = self._count_prefix_lines(log, "CHECK-OK: ")

        version_log = os.path.join(self.build_folder, "snek_version.log")
        self.run('snek --version > "%s" 2>&1' % version_log, env="conanrun")
        with open(version_log, "r", encoding="utf-8", errors="replace") as handle:
            version_out = handle.read()
        if "1.13" not in version_out:
            raise ConanException("snek --version has no 1.13: %r" % version_out[:200])
        passed_count += 1

        ok = (passed_count == discovered)
        marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            {"executed": True, "passed": ok,
             "command": "snek test_snek.py && snek --version",
             "discovered": discovered, "passedCount": passed_count},
            separators=(",", ":"))
        print(marker, flush=True)
        self.output.info(marker)
        self._reemit_upstream()
        if not ok:
            raise ConanException(
                "consumer checks failed: %d/%d passed" % (passed_count, discovered))

    def _reemit_upstream(self):
        try:
            dep = self.dependencies["snek"]
            cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                    payload, separators=(",", ":"))
                print(line, flush=True)
                self.output.info(line)
            else:
                self.output.warning(
                    "hmbs_upstream.json absent from package res/; "
                    "upstream marker left to the main build (cache-miss rounds)")
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
