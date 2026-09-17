#!/usr/bin/env python3
"""Conan test_package for cdebconf-entropy 0.6.

Runs the real plugin checks in test_cdebconf_entropy.py against the
packaged tree and the cdebconf hard dep, then emits HMBS
machine-evidence markers.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class CdebconfEntropyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Device /tmp is read-only: give the test process a writable
        # TMPDIR without touching what the test verifies.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.vars(self, scope="run").save_script("hmbs_test_tmp")

    def test(self):
        pkg_folder = self.dependencies["cdebconf-entropy"].package_folder
        cdebconf_pkg = self.dependencies["cdebconf"].package_folder
        discovered = 3
        passed = 0
        try:
            self.run('python3 test_cdebconf_entropy.py "%s" "%s"'
                     % (pkg_folder, cdebconf_pkg), env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test_cdebconf_entropy.py failed: %s" % exc)

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "python3 test_cdebconf_entropy.py "
                       "<package_folder> <cdebconf_package_folder>",
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))

        ut_result = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cdebconf-entropy_0.60.tar.xz audited (sha256 "
                "1ebb46487004500cc7959783a6f61b48d52dfbb6917d191ccf44677c8f5f9b68): "
                "top-level files are HACKING, Makefile.in, autogen.sh, "
                "configure.ac, gtk-plugin-entropy.c, newt-plugin-entropy.c, "
                "text-plugin-entropy.c plus debian/; no tests/ or test/ "
                "directory, no TEST/TEST_F (gtest) or def test_ (pytest) "
                "hits, no TESTS/check_PROGRAMS/check-local targets, so make "
                "check is automake's default empty target executing zero "
                "test cases"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(ut_result))

        if passed != discovered:
            raise ConanException("cdebconf-entropy test_package checks failed")
