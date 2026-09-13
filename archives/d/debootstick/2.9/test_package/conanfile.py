#!/usr/bin/env python3
"""Conan test_package for debootstick 2.9 (tool-type package).

Verifies the packaged launcher is installed and actually executes through
its headless CLI paths (no root, no image build):
- `debootstick --version` prints exactly `debootstick 2.9`
- `debootstick --help` exits 0 with usage text
- `debootstick --help-os-support` exits 0
- unknown option and missing-args paths fail closed (non-zero)
- scripts/ + disk-layouts/ data files are present beside the package
"""
import os
import shutil

from conan import ConanFile


class DebootstickTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _ensure_writable_tmp(self):
        cands = [
            os.environ.get("HMBS_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
        ]
        chosen = None
        for c in cands:
            if c and os.path.isdir(c):
                chosen = c
                break
        if chosen is None:
            fallback_base = getattr(self, "build_folder", None) or os.getcwd()
            chosen = os.path.join(fallback_base, "hmbs-tmp")
            try:
                os.makedirs(chosen, exist_ok=True)
            except OSError:
                pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = chosen
        self.output.info(f"[HMBS tmp] test TMPDIR={chosen} HMBS_TMPDIR={os.environ.get('HMBS_TMPDIR')}")
        return chosen

    def test(self):
        # R32: Platform check - only run on Linux/OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            return

        tmpdir = self._ensure_writable_tmp()

        pkg = self.dependencies["debootstick"].package_folder
        debootstick_bin = os.path.join(pkg, "bin", "debootstick")
        assert os.path.isfile(debootstick_bin), \
            f"debootstick binary not found at {debootstick_bin}"

        script = os.path.join(self.source_folder, "test.sh")
        assert os.path.isfile(script), f"test.sh not found at {script}"

        # HMBS [shell_getcwd]: prefer injected SHELL (/bin/sh, POSIX)
        # over hnp bash which has HMDFS getcwd issues (DRAFT-6487).
        # test.sh is POSIX sh (no pipefail/bashisms).
        shell = (os.environ.get("SHELL")
                 or os.environ.get("CONFIG_SHELL")
                 or shutil.which("sh")
                 or shutil.which("bash")
                 or "/bin/sh")
        self.output.info(f"[HMBS shell] test shell={shell} script={script}")
        # HMBS [readonly_tmp]: forward the writable TMPDIR explicitly on the
        # command line so the child shell sees it even if conanrun env
        # composition drops os.environ entries; test.sh re-exports it.
        self.run(
            f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}" '
            f'HMBS_TMPDIR="{tmpdir}" '
            f'DEBOOTSTICK_BIN="{debootstick_bin}" '
            f'DBSTCK_PKG="{pkg}" "{shell}" "{script}"',
            env="conanrun",
        )
        # HMBS_TEST_PACKAGE_RESULT is printed by test.sh after real asserts.
        # Upstream ships no test suite (see test_package/MANIFEST.yml
        # upstream_test_audit); emit the no_tests marker here so the
        # preflight gate sees it in the test_package phase stdout.
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"none (upstream 2.9 has no test/check target; Makefile all/clean empty, no tests/ dir, no debian/tests)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"debootstick 2.9 upstream ships no automated tests: Makefile defines only empty all/clean plus install/uninstall, source tree has no tests/test/check/pytest/ctest/bats, Debian packaging adds no debian/tests autopkgtest"}')
