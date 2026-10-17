#!/usr/bin/env python3
"""Conan test_package for jna 5.19.0.

Tests that libjnidispatch.so is a valid JNI bridge library by:
1. Verifying the .so file exists in the package
2. Checking it's a valid ELF shared object (DYN type)
3. Verifying JNI symbols (Java_com_sun_jna_*) are exported
"""
import os

from conan import ConanFile


class JnaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        jna_pkg = self.dependencies["jna"]
        lib_path = os.path.join(jna_pkg.package_folder, "lib", "libjnidispatch.so")

        test_script = os.path.join(self.source_folder, "test_jna.sh")
        self.run(f"bash {test_script} {lib_path}", env="conanrun")
