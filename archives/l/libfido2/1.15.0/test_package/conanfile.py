#!/usr/bin/env python3
"""Conan test_package for libfido2 1.15.0.

Builds a consumer executable against the packaged libfido2 and runs it
on the device (native OHOS aarch64 host). The test exercises:
fido_init, fido_new/fido_dev_free, es256_pk_new/from_ptr/free,
rs256_pk_new/free, eddsa_pk_new/free, fido_strerr, version macros.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class Libfido2TestConan(ConanFile):
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
        # R34: 实质运行被测二进制（本机即 OHOS aarch64，非交叉）
        if cross_building(self):
            self.output.info("cross-building: compile+link verification only")
            return
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_libfido2"), env="conanrun")
