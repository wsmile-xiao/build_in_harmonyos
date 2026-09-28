#!/usr/bin/env python3
"""Consumer test for crossguid/0.2.2 — compile, link and run a real consumer."""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CrossguidTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            for exe_name in ("test_crossguid", "test_ohos_crossguid"):
                exe = os.path.join(self.cpp.build.bindir, exe_name)
                if not os.path.isfile(exe):
                    hits = glob.glob(os.path.join(self.build_folder, "**",
                                                  exe_name), recursive=True)
                    if hits:
                        exe = hits[0]
                self.run(exe, env="conanrun")
