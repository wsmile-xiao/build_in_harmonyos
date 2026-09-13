#!/usr/bin/env python3
"""Conan test_package for udunits 2.2.28.1.

The test binary links against libudunits2 and runs real unit-conversion
assertions through the public C API (R34: no empty-shell tests).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UdunitsTestConan(ConanFile):
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
        # UDUNITS2_XML_PATH is exported by the udunits package_info
        # (runenv_info); run with env="conanrun" so ut_read_xml(NULL)
        # finds the packaged unit database.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_udunits"),
            env="conanrun",
        )
