#!/usr/bin/env python3
"""Conan test_package for pika (PikaPython) 1.14.0 — Conan L1 official test.

Tests the core data-layer API of libpika-core (arg_newInt, arg_newStr,
Stack, strsCopy, pika_platform_malloc/free) to verify the library is
correctly built and consumable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PikaTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_pika'", env="conanrun")
