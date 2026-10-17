#!/usr/bin/env python3
"""Conan test_package for alpine-baselayout 3.7.2 — real artifact verification.

The package is a pure configuration/data package (noarch): Alpine base
directory structure and init scripts. This test executes test_smoke.sh
against the packaged artifacts to verify:
  1. every upstream config file is installed under the expected package path,
  2. the shadow file generated from passwd matches the upstream awk output,
  3. file contents carry the expected identity (root entry, profile PATH),
  4. the GPL-2.0 license text is packaged under licenses/,
  5. shell scripts pass `sh -n` syntax checks.
"""
import os
import shutil

from conan import ConanFile


class AlpineBaselayoutTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        test_script = os.path.join(self.source_folder, "test_smoke.sh")
        if not os.path.isfile(test_script):
            raise Exception(f"test source not found: {test_script}")

        sh = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/system/bin/sh"

        self.run(
            f'"{sh}" "{test_script}" "{pkg_folder}" "{sh}"',
            env="conanrun",
        )
