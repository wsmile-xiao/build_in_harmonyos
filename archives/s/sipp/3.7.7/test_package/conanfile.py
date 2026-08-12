#!/usr/bin/env python3
"""Test package for SIPp 3.7.7."""

from conan import ConanFile
from conan.tools.build import can_run


class SippTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # This CI's Conan self.run() API uses ignore_errors=False to fail
            # the build on a non-zero exit code; it does not accept check=True.
            self.run("bash test_sipp.sh", cwd=self.source_folder, env="conanrun", ignore_errors=False)
