#!/usr/bin/env python3
"""Conan test_package for tut 2.0.1.

Consumer smoke test runs the packaged `tut` binary via test.sh
(`tut --help` / `tut --version` / `tut example-config`). The upstream
2.0.1 tarball contains zero tests (96 files, no *_test.go, no Test funcs),
so this phase emits the no_tests upstream marker with an explicit audit.

Emits HMBS evidence markers:
  - HMBS_TEST_PACKAGE_RESULT: consumer smoke test (3 fixed checks)
  - HMBS_UPSTREAM_TEST_RESULT: upstream suite (no_tests, 0/0)
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TutTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("tut test_package must run on the host")
        script = os.path.join(self.recipe_folder, "test.sh")
        if not os.path.isfile(script):
            raise ConanException("test script not found: %s" % script)
        self.run("sh %s" % script, env="conanrun")
        # Three fixed consumer checks in test.sh (help / version /
        # example-config). Counts are the test plan itself, not a stdout
        # string count: each check has an explicit failure exit path.
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test.sh (tut --help / tut --version / tut example-config)",
            "discovered": 3,
            "passedCount": 3,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": "none (no upstream test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Upstream tut 2.0.1 tarball (96 files, sha256 afa8c490...) "
                      "contains no *_test.go and no Go Test functions; GitHub API "
                      "tree for tag 2.0.1 confirms zero _test.go blobs; "
                      "`go test ./...` has nothing to run. "
                      "See test_package/MANIFEST.yml upstream_test_audit.",
        }))
