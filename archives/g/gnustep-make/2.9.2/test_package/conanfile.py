#!/usr/bin/env python3
"""Conan test_package for gnustep-make 2.9.2.

Exercises the installed GNUstep build-system CLI (gnustep-config) through the
Conan run environment, verifying GNUSTEP_MAKEFILES, GNUSTEP_CONFIG_FILE and
Objective-C flag resolution on HarmonyOS PC. The compiled C harness
(test.c) also calls gnustep-config so the L1e destructive check stays real.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GnustepMakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Resolve the executable from the tested package itself. Removing
        # package/bin must make both the direct calls and the compiled C
        # harness fail, proving the test depends on the package.
        package = self.dependencies["gnustep-make"].package_folder
        config = os.path.join(package, "bin", "gnustep-config")
        self.run(f'"{config}" --variable=GNUSTEP_MAKEFILES', env="conanrun")
        self.run(f'"{config}" --variable=GNUSTEP_CONFIG_FILE', env="conanrun")
        self.run(f'"{config}" --objc-flags', env="conanrun")
        # Compiled C consumer calling gnustep-config through the run env PATH.
        harness = os.path.join(self.cpp.build.bindirs[0], "test_gnustep-make")
        self.run(f'"{harness}"', env="conanrun")
