#!/usr/bin/env python3
"""Conan test_package for cdrkit — verifies installed binaries work.

Tests:
  1. genisoimage --version (verifies the binary runs and reports version)
  2. isoinfo --version (verifies isoinfo binary works)
  3. genisoimage creates a minimal ISO image and isoinfo reads it back
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CdrkitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the actual cdrkit binaries to verify they work
        bindir = self.dependencies["cdrkit"].cpp_info.bindirs[0] if self.dependencies["cdrkit"].cpp_info.bindirs else None

        # Fallback: look in the package install prefix
        if not bindir:
            pkg = self.dependencies["cdrkit"]
            bindir = os.path.join(pkg.package_folder, "bin")

        genisoimage = os.path.join(bindir, "genisoimage")
        isoinfo = os.path.join(bindir, "isoinfo")

        # Test 1: genisoimage --version
        self.run(f'"{genisoimage}" --version', env="conanrun")

        # Test 2: isoinfo --version
        self.run(f'"{isoinfo}" --version', env="conanrun")

        # Test 2b: wodim --version (verify wodim binary with capget/capset patches)
        wodim = os.path.join(bindir, "wodim")
        if os.path.exists(wodim):
            self.run(f'"{wodim}" --version', env="conanrun")

        # Test 3: Create a minimal ISO and read it back
        testdir = os.path.join(self.build_folder, "testdir")
        os.makedirs(testdir, exist_ok=True)
        with open(os.path.join(testdir, "hello.txt"), "w") as f:
            f.write("hello from cdrkit test\n")

        iso_path = os.path.join(self.build_folder, "test.iso")
        self.run(f'"{genisoimage}" -o "{iso_path}" "{testdir}"', env="conanrun")

        if not os.path.exists(iso_path):
            raise Exception("genisoimage did not create the ISO file")

        # Test 4: Read the ISO back with isoinfo
        self.run(f'"{isoinfo}" -l -i "{iso_path}"', env="conanrun")

        # Also run the CMake-built test binary
        cmake = CMake(self)
        cmake.test()
