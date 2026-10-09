#!/usr/bin/env python3
"""Conan test_package — mgen 5.02.c5.1.1 (network traffic CLI tools).

test_mgen.sh really executes the packaged bin/mgen (`help` usage path and
an unknown-command no-hang probe) and checks the co-packaged bin/mpmgr
exists; it emits HMBS_TEST_PACKAGE_RESULT as machine evidence.

HMBS_UPSTREAM_TEST_RESULT (status=no_tests) is re-emitted here on every run
because test_package build() is skipped on cache hits while test() always
runs — the same split cvechecker/4 uses.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class MgenTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _emit_upstream_no_tests(self):
        data = {
            "status": "no_tests",
            "framework": "make",
            "command": "make -f Makefile.linux (no check/test target upstream)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("mgen V5.1.1 has no automated test suite: no tests/ "
                       "directory, no check/test Makefile target, no "
                       "TESTS/check_PROGRAMS, no ctest/gtest/pytest wiring; "
                       "full audit in test_package/MANIFEST.yml"),
        }
        msg = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(data)}"
        print(msg, flush=True)
        try:
            self.output.info(msg)
        except Exception:
            pass

    def test(self):
        package_folder = self.dependencies["mgen"].package_folder
        mgen_bin = os.path.join(package_folder, "bin", "mgen")
        mpmgr_bin = os.path.join(package_folder, "bin", "mpmgr")
        assert os.path.isfile(mgen_bin), f"mgen binary not found: {mgen_bin}"
        assert os.path.isfile(mpmgr_bin), f"mpmgr binary not found: {mpmgr_bin}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test_mgen.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{mgen_bin}" "{mpmgr_bin}"', cwd=cwd)
            # HMBS_TEST_PACKAGE_RESULT emitted by test_mgen.sh.
            self._emit_upstream_no_tests()
        else:
            for path in (mgen_bin, mpmgr_bin):
                with open(path, "rb") as binary:
                    magic = binary.read(4)
                assert magic == b"\x7fELF", f"{path} is not an ELF binary: {magic!r}"
                self.output.info(f"binary exists and has ELF magic: {path}")
            self._emit_upstream_no_tests()
