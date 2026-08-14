#!/usr/bin/env python3
"""Conan test_package for libde265 1.0.18 (L1 official test).

Exercises the libde265 decoder C API: de265_new_decoder, de265_get_version,
de265_flush_data, de265_decode, de265_get_next_picture, de265_free_decoder.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libde265TestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # R5: OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly;
        # run the test binary via bash as a belt-and-braces check.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} -c "./test_libde265"', env="conanrun")
