#!/usr/bin/env python3
"""Conan test_package for xf86-video-fbdev — verifies the driver module.

This test compiles a C program that reads the ELF header of fbdev_drv.so
and verifies it is a valid AArch64 shared library. Since the driver is
an X.Org plugin with unresolved X server symbols (expected at runtime),
dlopen is not used. Instead, we parse the ELF header directly.
"""
import os
from conan import ConanFile
from conan.tools.files import copy


class Xf86VideoFbdevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy the driver module to the build directory
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "fbdev_drv.so",
             src=os.path.join(self.dependencies["xf86-video-fbdev"].package_folder, "lib"),
             dst=bin_dir)

        # Compile the test program from test.c
        cc = self.conf_info.get("tools.build:compiler_executables")
        cc_path = cc["c"] if cc else "clang"
        test_bin = os.path.join(bin_dir, "test_fbdev")
        test_src = os.path.join(os.path.dirname(__file__), "test.c")

        self.run(f"{cc_path} -o {test_bin} {test_src}", env="conanbuild")

    def test(self):
        so_path = os.path.join(self.build_folder, "bin", "fbdev_drv.so")
        test_bin = os.path.join(self.build_folder, "bin", "test_fbdev")

        # Run the test program against the built .so
        self.run(f"{test_bin} {so_path}", env="conanrun")
