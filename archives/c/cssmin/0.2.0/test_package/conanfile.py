#!/usr/bin/env python3
"""Conan test_package — cssmin 0.2.0.

R34: runs the packaged cssmin module through real cssmin.cssmin()
compression checks plus the stdin/stdout CLI entry point.
Emits HMBS machine-evidence markers.
"""

import json
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CssminTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        pkg = self.dependencies["cssmin"].package_folder
        py_ver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        assert os.path.isfile(os.path.join(site, "cssmin.py")), "cssmin module missing: %s" % site
        test_script = os.path.join(self.recipe_folder, "test_cssmin.py")
        actual_command = "%s \"%s\"" % (sys.executable, test_script)
        discovered = 6
        passed = 0
        try:
            self.run(
                "PYTHONPATH=\"%s\" %s \"%s\"" % (site, sys.executable, test_script),
                env="conanrun",
            )
            passed = discovered
        except Exception as exc:
            self.output.error("test_cssmin.py failed: %s" % exc)

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": actual_command,
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))

        ut_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "python3 -m pytest (no suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cssmin-0.2.0.tar.gz audited (sha256 "
                "e012f0cc8401efcf2620332339011564738ae32be8c84b2e43ce8beaec1067b6): "
                "sdist contains only setup.py/setup.cfg/MANIFEST.in/PKG-INFO/src/cssmin.py "
                "plus egg-info, no tests/ or test/ directory, no test_*.py, no TEST/TEST_F "
                "(gtest), no def test_ (pytest), no Makefile check target, no CTest; "
                "upstream GitHub zacharyvoase/cssmin file list (src/.gitignore/LICENSE/"
                "MANIFEST.in/README.md/setup.py) has no test entry. Functional verification "
                "runs 6 real cssmin() compression checks via test_cssmin.py."
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(ut_result))

        if passed != discovered:
            raise ConanException("cssmin test_package assertions failed")
