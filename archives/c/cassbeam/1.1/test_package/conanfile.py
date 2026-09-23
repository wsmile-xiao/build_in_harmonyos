#!/usr/bin/env python3
"""Conan test_package — cassbeam 1.1.

CLI tool (R34): runs the packaged `cassbeam` binary on the upstream VLA
example input and asserts real science outputs are produced and non-empty.
Emits HMBS machine-evidence markers (same channel as lzop/freeunit).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CassbeamTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        pkg = self.dependencies["cassbeam"].package_folder
        bin_path = os.path.join(pkg, "bin", "cassbeam")
        assert os.path.isfile(bin_path), f"cassbeam binary not found: {bin_path}"
        # HMBS injects SHELL=/bin/sh; avoid hard-coded `bash`. Run from a
        # writable cwd (TMPDIR, injected by HMBS) instead of the HMDFS
        # package folder. test.sh resolves its input via its own dir.
        shell = os.environ.get("SHELL", "/bin/sh")
        test_script = os.path.join(self.recipe_folder, "test.sh")
        cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP") or self.recipe_folder
        # Ensure the chosen cwd exists (HMBS-injected TMPDIR is writable;
        # recipe_folder fallback may sit on read-only HMDFS).
        try:
            os.makedirs(cwd, exist_ok=True)
        except Exception:
            cwd = self.recipe_folder
        actual_command = f'CASSBEAM="{bin_path}" "{shell}" "{test_script}"'
        discovered = 3
        passed = 0
        try:
            self.run(actual_command, env="conanrun", cwd=cwd)
            passed = discovered
        except Exception as exc:
            self.output.error(f"test.sh failed: {exc}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": actual_command,
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Upstream has no test suite (audited tarball, see MANIFEST.yml
        # upstream_tests_exist: false): Makefile has no `check` target, so
        # the honest result is no_tests/0.
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
                "cassbeam_1.1.orig.tar.gz audited (sha256 "
                "6731a091f9671720f54e48e5847803957b0cc41931aaeaaac658834798c39de9): "
                "no tests/ or test/ directory, no TEST/TEST_F (gtest) or "
                "def test_ (pytest) anywhere in the tree, Makefile.in defines "
                "only all/clean/distclean/install with no check/TESTS target, "
                "configure.in contains no test macros; `make -n check` is a "
                "no-op (no rule), so make check executes zero test cases. "
                "Functional verification runs the upstream example "
                "examples/vla/vla-1500MHz.in through the packaged binary."
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("cassbeam test_package assertions failed")
