#!/usr/bin/env python3
"""Conan test_package — bird2 2.17.4

Verifies that the bird daemon binary is installed and can report its version.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class Bird2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run CMake test (ctest) which executes test.c → system("bird --version")
        cmake = CMake(self)
        cmake.test()

        # Also directly verify bird --version (R34)
        dep = self.dependencies["bird2"]
        bin_path = None
        for bindir in dep.cpp_info.bindirs:
            candidate = os.path.join(dep.package_folder, bindir, "bird")
            if os.path.exists(candidate):
                bin_path = candidate
                break

        if bin_path:
            ret = self.run(f'"{bin_path}" --version', env="conanrun")
            assert ret == 0, f"bird --version failed with exit code {ret}"
        else:
            ret = self.run("bird --version", env="conanrun")
            assert ret == 0, f"bird --version failed with exit code {ret}"
