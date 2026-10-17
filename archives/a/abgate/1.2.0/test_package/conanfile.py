#!/usr/bin/env python3
"""Conan test_package for abgate 1.2.0.

abgate is an LV2 noise gate plugin — the test verifies the plugin
bundle was installed correctly and the shared library loads.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class AbgateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abgate"]
        pkg_dir = dep.package_folder

        # Check LV2 bundle structure
        bundle_dir = os.path.join(pkg_dir, "lib", "lv2", "abGate.lv2")
        if not os.path.isdir(bundle_dir):
            raise ConanException(f"LV2 bundle not found: {bundle_dir}")

        # Run the shell test script (real assertions: bundle files + ELF magic).
        script = os.path.join(self.recipe_folder, "test_gate.sh")
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} {script} {bundle_dir}", env="conanrun")
        else:
            self.run(f"sh {script} {bundle_dir}", env="conanrun")