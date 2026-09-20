#!/usr/bin/env python3
"""Test package for xf86-video-dummy 0.4.1.

Verifies that the built package contains a valid dummy_drv.so shared module
for the X.Org server.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Xf86VideoDummyTestConan(ConanFile):
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
        import os
        # Verify dummy_drv.so exists in the package
        pkg = self.dependencies["xf86-video-dummy"]
        so_dir = os.path.join(pkg.package_folder, "lib", "xorg", "modules", "drivers")
        so_path = os.path.join(so_dir, "dummy_drv.so")
        if not os.path.isfile(so_path):
            raise Exception(f"dummy_drv.so not found at {so_path}")
        self.output.info(f"Found dummy_drv.so: {so_path}")

        # Verify it's a valid ELF shared object (check magic bytes)
        with open(so_path, "rb") as f:
            magic = f.read(4)
        if magic != b"\x7fELF":
            raise Exception("dummy_drv.so is not a valid ELF file")
        self.output.info("ELF magic verified")

        # Run the test binary with the .so path
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_xf86_video_dummy")
        if not os.path.isfile(test_bin):
            raise Exception(f"Test binary not found at {test_bin}")
        os.environ["DUMMY_DRV_PATH"] = so_path
        self.run(test_bin, env=["conanrun"])
