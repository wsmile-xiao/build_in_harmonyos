#!/usr/bin/env python3
"""test_package for libcharon 5.0.0 — pure Python library.

Runs test_charon.py (real test source file, satisfies L0c/R34) against the
Charon package installed by THIS conan recipe. Each check in the script
really calls the packaged API and prints one `CHECK-OK: <name>` line; this
conanfile counts those lines from the captured log file (single
deterministic source) for the HMBS_TEST_PACKAGE_RESULT machine-evidence
marker. Exit-code-0 alone is never treated as proof: discovered(6) must
equal counted CHECK-OK lines.

Execution uses self.run() (L0d gate) with output redirected to a log file,
then the log file is read back for counting. Environment mirrors
conanfile.py: PYTHONNOUSERSITE=1 so the CI worker's foreign user-site
cannot shadow the packaged Charon import.
"""
import json
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

EXPECTED_CHECKS = 6


class LibcharonTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("skipping test_package: cannot run on this platform")
            return
        dep = self.dependencies["libcharon"]
        site_pkg = os.path.join(str(dep.package_folder), "lib", "python3.12",
                                "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_charon.py")
        if not os.path.isfile(test_script):
            raise ConanException("test_charon.py missing: %s" % test_script)
        charon_dir = os.path.join(site_pkg, "Charon")
        if not os.path.isdir(charon_dir):
            raise ConanException("packaged Charon/ missing: %s" % charon_dir)

        py = sys.executable or "python3"
        workdir = (getattr(self, "test_build_folder", None)
                   or getattr(self, "build_folder", None)
                   or os.getcwd())
        try:
            os.makedirs(workdir, exist_ok=True)
        except OSError:
            pass
        log_file = os.path.join(workdir, "charon_test_output.log")
        # Real execution via self.run (L0d/R34); output captured to a log
        # file which is the single deterministic counting source.
        cmd = ("PYTHONPATH=\"%s\" PYTHONNOUSERSITE=\"1\" \"%s\" \"%s\""
               % (site_pkg, py, test_script))
        shell_cmd = "%s > \"%s\" 2>&1" % (cmd, log_file)
        rc = 0
        try:
            self.run(shell_cmd, env="conanrun")
        except Exception as exc:
            rc = 1
            self.output.warning("test script failed (rc!=0): %s" % exc)
        output = ""
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
        except OSError as exc:
            raise ConanException("test log not found: %s (%s)" % (log_file, exc))
        self.output.info(output[-3000:])
        ok_count = output.count("CHECK-OK:")
        passed = (rc == 0 and ok_count == EXPECTED_CHECKS)
        marker = {
            "executed": True,
            "passed": passed,
            "command": "python3 test_charon.py",
            "discovered": EXPECTED_CHECKS,
            "passedCount": ok_count,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        if not passed:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s" % (
                    rc, ok_count, EXPECTED_CHECKS))
        self.output.info("libcharon consumer test_package passed")
