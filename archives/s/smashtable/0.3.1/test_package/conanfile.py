#!/usr/bin/env python3
"""Conan test_package for smashtable 0.3.1 — consumer API validation.

Builds a consumer that instantiates three container families through the
packaged headers and asserts real behaviour: upsert/overwrite, lookup with
copy-out, miss callback, committed and rolled-back transactions, erase_range
and clear. The partitioned store exercises the atomic epoch vocabulary from
the patched shared.hpp at runtime.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SmashTableTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip consumer runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_smashtable"), env="conanrun")
