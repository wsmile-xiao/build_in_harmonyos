#!/usr/bin/env python3
"""Test package for nethack 5.0.0 — Conan L1 smoke test.

Runs test.sh (bash) against the packaged binaries:
  1. `nethack --version` reports 5.0.0
  2. `nethack --showpaths` exits 0 (documented path self-check)

Emits HMBS machine-evidence markers for the preflight gate.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class NethackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        discovered = 2
        passed = 0
        try:
            # Binary is built with HACKDIR=/usr/share/nethack (compile-time
            # default). The conan package lays playground data (nhdat,
            # sysconf, dungeon files) under <pkg>/share/nethack, so point
            # the runtime there. --version exits before chdir, --showpaths
            # does chdirx(dir, TRUE) and fails without this override.
            pkg = self.dependencies["nethack"].package_folder
            share = os.path.join(pkg, "share", "nethack").replace("\\", "/")
            self.run(
                'NETHACKDIR="{}" "{}" test.sh'.format(share, bash),
                env="conanrun",
            )
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: {}".format(exc))

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "{} test.sh".format(bash),
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT={}".format(json.dumps(tp_result)))

        ut_result = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "nethack-500-src.tgz audited (sha256 "
                "2959b7886aac76185b90aea0c9f80d14343f604de0ae96b3dd2a760f7ab3bde9): "
                "test/ holds 9 Lua files for manual wizmode runs only "
                "(README: build without DLB, install, copy Lua files, start "
                "wizmode, wizloadlua each file; no harness, no exit-code "
                "signal); sys/libnh/test targets WANT_LIBNH/wasm only; no "
                "check/test/ctest target in top or sys/unix Makefiles "
                "(Makefile.check only verifies generated Makefiles are fresh); "
                "no TEST/TEST_F, def test_, TESTS/check_PROGRAMS, or ctest "
                "registration; `make -n check` has no rule, 0 cases executed"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(ut_result)))

        if passed != discovered:
            raise ConanException("test_package smoke tests failed")
