#!/usr/bin/env python3
"""Conan consumer test for the xmppc command-line application."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class XmppcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["xmppc"]
        executable = os.path.join(package.package_folder, "bin", "xmppc")
        assert os.path.isfile(executable), f"xmppc executable not found: {executable}"

        if not can_run(self):
            with open(executable, "rb") as binary:
                assert binary.read(4) == b"\x7fELF", "xmppc is not an ELF executable"
            self.output.info("xmppc ELF executable is present; target cannot run here")
            return

        if str(self.settings.os) == "OHOS":
            assert str(self.settings.arch) == "armv8", (
                f"HarmonyOS runtime test requires AArch64, got {self.settings.arch}"
            )
            self.output.info("Running HarmonyOS AArch64 xmppc CLI test")

        test_script = os.path.join(self.recipe_folder, "test_cli.py")
        self.run(
            f'"{sys.executable}" "{test_script}" "{executable}"',
            env="conanrun",
        )

        if str(self.settings.os) == "OHOS":
            self.output.info("HarmonyOS AArch64 xmppc --help runtime test passed")
