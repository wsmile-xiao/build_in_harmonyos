#!/usr/bin/env python3
"""Conan test_package — pod2man (podlators) 6.0.2.

Verifies that pod2man script is installed and can convert a POD file to man page format.
"""
import os

from conan import ConanFile


class Pod2manTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["pod2man"].package_folder, "bin", "pod2man")
        script = os.path.join(self.source_folder, "test_pod2man.sh")
        self.run(f'sh "{script}" "{bin_path}"', env="conanrun")
