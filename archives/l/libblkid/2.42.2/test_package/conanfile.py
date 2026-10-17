#!/usr/bin/env python3
"""Conan test package for libblkid 2.42.2 (util-linux)."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibBlkidTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _check_package_layout(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        checks = [
            ("blkid header", os.path.join(pkg, "include", "blkid", "blkid.h")),
            ("blkid static lib", os.path.join(pkg, "lib", "libblkid.a")),
            ("blkid pkgconfig", os.path.join(pkg, "lib", "pkgconfig", "blkid.pc")),
        ]
        missing = [name for name, path in checks if not os.path.exists(path)]
        if missing:
            raise ConanException("missing libblkid package artifacts: " + ", ".join(missing))

    def test(self):
        self._check_package_layout()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not can_run(self):
            return
        self.run(os.path.join(self.cpp.build.bindir, "test_blkid_api"), env="conanrun")
