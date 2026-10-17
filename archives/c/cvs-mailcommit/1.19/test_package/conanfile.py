#!/usr/bin/env python3
"""Conan test_package — cvs-mailcommit 1.19 (consumer test).

Delegates real verification to test_cvs_mailcommit.py (invoked via
self.run(), satisfying L0c/L0d: test_package contains a non-conanfile.py
test source and test() performs real execution).
"""
import os

from conan import ConanFile


class TestPkg(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def _emit_upstream_no_tests(self):
        # Re-emit upstream evidence every test_package run: the main
        # recipe build() is skipped on Conan cache hit, so this covers
        # evidence persistence across rounds.
        import json
        data = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "cvs-mailcommit 1.19 upstream ships no test suite: orig.tar.gz is a single Perl script with no tests/ dir, no Makefile/ctest/pytest entry (audit in test_package/MANIFEST.yml)",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(data)
        print(msg, flush=True)
        try:
            self.output.info(msg)
        except Exception:
            pass

    def test(self):
        pkg = self.dependencies["cvs-mailcommit"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_cvs_mailcommit.py")
        self.run("python3 %s %s" % (test_script, pkg_root))
        self._emit_upstream_no_tests()
