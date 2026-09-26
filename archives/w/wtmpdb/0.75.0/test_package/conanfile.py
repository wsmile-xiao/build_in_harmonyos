#!/usr/bin/env python3
"""test_package for wtmpdb 0.75.0 — real consumer test: links libwtmpdb and
exercises the exported public API (login/logout/read_all/get_id) against a
temporary sqlite database, asserting observable behavior end to end."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class WtmpdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_wtmpdb")
        self.run(exe, env="conanrun")
