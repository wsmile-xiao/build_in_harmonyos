#!/usr/bin/env python3
"""Conan test_package for complexity 1.13 (CLI tool).

Runs the packaged `complexity` binary through test_complexity.sh, which
performs 2 real assertions (version output + actual scoring run), then
emits the HMBS_TEST_PACKAGE_RESULT marker (discovered/passedCount = 2).
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class ComplexityTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["complexity"].package_folder
        bin_path = os.path.join(package_folder, "bin", "complexity")
        assert os.path.isfile(bin_path), f"complexity binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test_complexity.sh")
            # HMBS injects SHELL=/bin/sh; avoid hard-coded `bash`. Run from a
            # writable cwd (TMPDIR, injected by HMBS) instead of the
            # read-only package cache folder.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            actual_command = f'"{shell}" "{test_script}" "{bin_path}"'
            self.run(actual_command, env="conanrun", cwd=cwd)
            # test_complexity.sh runs 2 assertions (--version / scoring run);
            # self.run raises on a non-zero script exit, so the marker below
            # is only emitted when the packaged binary really works.
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": actual_command,
                "discovered": 2,
                "passedCount": 2,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            # Cache-hit survival: `conan create` skips build() when the
            # package binary is already cached, so the authoritative
            # `make check` marker never prints on re-run preflights
            # (observed: "Already installed!", upstream discovered=0).
            # Re-run the vendored upstream assertions
            # (test_upstream_check.sh mirrors tests/complexity.test against
            # the installed binary) for real here; self.run raises on a
            # non-zero exit, so the marker below only appears when the
            # upstream scoring table really matched on this machine.
            upstream_script = os.path.join(self.recipe_folder, "test_upstream_check.sh")
            upstream_command = f'"{shell}" "{upstream_script}" "{bin_path}"'
            self.run(upstream_command, env="conanrun", cwd=cwd)
            upstream_result = {
                "status": "passed",
                "framework": "automake",
                "command": upstream_command,
                "discovered": 1,
                "executed": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"complexity is not an ELF binary: {magic!r}"
            self.output.info(f"complexity binary exists and has ELF magic: {bin_path}")
