#!/usr/bin/env python3
"""Conan test_package for io_lib 1.14.9.

R34: real consumer test — test_io_lib_ztr.c exercises the ZTR codec
API (new_ztr/ztr_add_text/fwrite_ztr/fread_ztr/ztr_find_chunks) that
srf/0.1's SRF_Ztr.cc consumes, verifying the library links and runs
on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class IoLibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0],
                                  "test_io_lib_ztr"))
