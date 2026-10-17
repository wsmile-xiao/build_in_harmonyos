#!/usr/bin/env python3
"""Conan test_package for sharutils 4.15.2 (shar/unshar/uuencode/uudecode)."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class SharutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS CI")
            return
        bindir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin")
        for prog in ("shar", "unshar", "uuencode", "uudecode"):
            prog_path = os.path.join(bindir, prog)
            assert os.path.isfile(prog_path), \
                "packaged binary missing: %s" % prog_path
        # HMBS injects SHELL=/bin/sh; avoid a hard-coded `bash`. Run from a
        # writable cwd (TMPDIR, injected by HMBS) instead of the package
        # folder: unshar/uudecode create files in the working directory.
        shell = os.environ.get("SHELL", "/bin/sh")
        # 2026-09-19 preflight: build() redirects os.environ TMPDIR to a
        # build-local dir (<main-build>/tests/hmbs-tmp) for `make check`
        # and the mutated value leaks into this test() in the same conan
        # process, so TMPDIR may point at a dir that does not exist when
        # test_package runs (Errno 2 on self.run cwd). Never trust it
        # blindly: use it only when it is an existing dir, otherwise run
        # from this test package's own build folder (guaranteed writable),
        # creating cwd fail-closed. Assertions/markers below untouched.
        _cand = os.environ.get("TMPDIR") or os.environ.get("TMP") or ""
        if _cand and os.path.isdir(_cand):
            cwd = _cand
        else:
            cwd = self.build_folder or self.recipe_folder
        try:
            os.makedirs(cwd, exist_ok=True)
        except OSError:
            cwd = self.build_folder or self.recipe_folder
            os.makedirs(cwd, exist_ok=True)
        script = os.path.join(self.recipe_folder, "test_sharutils.sh")
        actual_command = '"%s" "%s" "%s"' % (shell, script, bindir)
        self.run(actual_command, env="conanrun", cwd=cwd)
        # test_sharutils.sh runs 2 roundtrip assertions (uuencode/uudecode
        # and shar/unshar, byte-compared against non-empty fixtures);
        # self.run raises on a non-zero script exit so the marker below is
        # only emitted when the packaged binaries really work.
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": actual_command,
            "discovered": 2,
            "passedCount": 2,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        # Experience 1 (textparser/1.9.0): re-emit upstream evidence persisted
        # in package res/. test_package runs on every preflight even when
        # conan skips a cached build() ("Already installed!"), so this is
        # the channel that guarantees HMBS_UPSTREAM_TEST_RESULT is present.
        # Fail-closed: missing or non-passed JSON raises, never fakes pass.
        _dep = self.dependencies[self.tested_reference_str]
        _cands = [
            os.path.join(_dep.package_folder, "res", "upstream_test_result.json"),
            os.path.join(_dep.package_folder, "upstream_test_result.json"),
        ]
        _up = None
        _up_path = None
        for _c in _cands:
            if os.path.isfile(_c):
                _up_path = _c
                with open(_c, "r", encoding="utf-8") as _f:
                    _up = json.load(_f)
                break
        if _up is None:
            raise ConanException(
                "upstream_test_result.json not found in package (%s) -- "
                "upstream tests did not run during build(); refusing to pass "
                "silently" % (_cands,))
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_up, ensure_ascii=False))
        try:
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_up, ensure_ascii=False), flush=True)
        except Exception:
            pass
        if (_up.get("status") != "passed"
                or int(_up.get("discovered", 0)) <= 0
                or int(_up.get("executed", 0)) != int(_up.get("discovered", 0))
                or int(_up.get("passed", 0)) != int(_up.get("discovered", 0))
                or int(_up.get("failed", 0)) != 0):
            raise ConanException("upstream result invalid: %s" % (_up,))
