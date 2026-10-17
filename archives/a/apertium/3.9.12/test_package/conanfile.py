#!/usr/bin/env python3
"""Conan test_package for apertium 3.9.12.

Consumer-view verification (layer 2): runs the installed CLI binaries via
test_apertium.sh (3 real assertions: version, deshtml markup, round-trip) and
emits the HMBS evidence markers parsed from the script's real output.
Also re-emits the upstream result persisted by the main recipe (HMBS gate
reads the final conan-create log).
"""
import json
import os
import re

from conan import ConanFile


class ApertiumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # No can_run() guard — the binaries must execute (native OHOS
        # build; L1e negative test enforces a genuine dependency).
        # L0d requires a real self.run() call: the script runs authoritatively
        # via self.run() (failure fails the build) and tees its PASS summary
        # to a result file, from which the marker numbers are READ — never
        # hardcoded.
        dep = self.dependencies["apertium"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_apertium.sh")
        result_file = os.path.join(self.build_folder, "apertium_smoke_result.txt")

        # Falsification: recipe script itself must be a real test.
        with open(script, "r", encoding="utf-8", errors="replace") as f:
            body = f.read()
        if len(body) < 500 or body.count("FAIL") < 3:
            raise RuntimeError("test_apertium.sh looks like a stub; refusing to pass")

        self.run('bash "{}" "{}" "{}"'.format(script, bin_dir, result_file),
                 env="conanrun")

        # Numbers come from the script's real result file, not constants.
        discovered = 0
        passed_count = 0
        try:
            with open(result_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            raise RuntimeError("smoke result file missing: {}".format(exc))
        m = re.search(r"PASS_COUNT=(\d+)/(\d+)", content)
        if m:
            passed_count, discovered = int(m.group(1)), int(m.group(2))
        if discovered <= 0 or passed_count != discovered:
            raise RuntimeError(
                "test_package evidence invalid (content={!r})".format(content[-500:]))

        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "bash test_apertium.sh <package bin>",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))

        # Re-emit the upstream result persisted in the package res/.
        emitted = False
        for cand in (os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
                     os.path.join(dep.package_folder, "upstream_test_result.json")):
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as f:
                    up = json.load(f)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up, ensure_ascii=False))
                if (up.get("status") != "passed"
                        or int(up.get("discovered", 0)) <= 0
                        or int(up.get("executed", 0)) < int(up.get("discovered", 0))
                        or int(up.get("passed", 0)) != int(up.get("executed", 0))
                        or int(up.get("failed", 0)) != 0):
                    raise RuntimeError("upstream result invalid: {}".format(up))
                emitted = True
                break
        if not emitted:
            raise RuntimeError("upstream_test_result.json not found in package; "
                               "main-recipe upstream tests did not run")
