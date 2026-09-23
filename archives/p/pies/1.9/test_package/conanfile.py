#!/usr/bin/env python3
"""Conan test_package for GNU Pies 1.9 — functional test of the supervisor.

Runs test.sh, which asserts 8 checks against the installed binary: presence of
the binary, the version banner (exit code + version string), the configuration
parser (--lint, both a valid and a deliberately broken configuration) and the
dependency-map dump (--dump-depmap).

The supervisor itself cannot be started on OHOS (no AF_UNIX sockets -> no
control socket), which is why the consumer test exercises the behaviours that
are available on the platform instead.
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

# 8 checks in test.sh: binary present, --version exit code, version banner,
# --lint accepts a valid configuration, --lint rejects a broken one (exit code
# and diagnostic), --dump-depmap exit code and dependency-map output.
CONSUMER_CHECKS = 8


class PiesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def configure(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _script_path(self):
        for candidate in (os.path.join(self.recipe_folder, "test.sh"),
                          os.path.join(os.getcwd(), "test.sh")):
            if os.path.isfile(candidate):
                return candidate
        raise ConanException("test.sh not found next to the test_package recipe")

    def _read(self, path):
        if not os.path.isfile(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        # Keep every file the consumer script creates outside the recipe/archive
        # tree: in conan's local flow the test_package build folder can resolve
        # to the archive directory itself, and test leftovers must never end up
        # in the delivered package.
        workdir = self.build_folder or os.getcwd()
        recipe_root = os.path.abspath(self.recipe_folder)
        if not workdir or os.path.abspath(workdir).startswith(recipe_root):
            workdir = os.path.join(os.path.expanduser("~"), "tmp", "pies-consumer-test")
        workdir = os.path.join(workdir, "consumer-test")
        os.makedirs(workdir, exist_ok=True)
        test_pkg = {
            "executed": False,
            "passed": False,
            "command": "bash test.sh <bindir> <workdir>",
            "discovered": CONSUMER_CHECKS,
            "passedCount": 0,
        }
        if not can_run(self):
            test_pkg["passed"] = False
            test_pkg["command"] = "cannot run on build host (cross-build): package layout only"
            test_pkg["skipped"] = "cannot run on build host (cross-build)"
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        out_file = os.path.join(workdir, "test-console.log")
        script = self._script_path()
        passed = True
        try:
            inner = "bash {} {} {} > {} 2>&1".format(shlex.quote(script), shlex.quote(bindir),
                                                     shlex.quote(workdir), shlex.quote(out_file))
            self.run(f"{bash} -c {shlex.quote(inner)}", env="conanrun")
        except Exception:
            passed = False
        output = self._read(out_file)
        self.output.info(output)
        reported = re.search(r"test\.sh: (\d+) checks passed", output)
        if reported:
            test_pkg["discovered"] = int(reported.group(1))
        test_pkg["executed"] = True
        test_pkg["passed"] = passed
        test_pkg["passedCount"] = test_pkg["discovered"] if passed else 0
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        if not passed:
            raise ConanException("consumer test failed:\n" + output[-2000:])
