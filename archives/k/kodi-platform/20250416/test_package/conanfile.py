#!/usr/bin/env python3
"""Conan test_package for kodi-platform 20250416 — L1 consumer-side test."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KodiPlatformTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # XMLUtils.h directly includes <tinyxml.h> and
        # <p8-platform/util/StringUtils.h>; declare the transitive deps
        # explicitly so CMakeDeps generates their find modules and include
        # paths for the consumer too.
        self.requires("tinyxml/2.6.2")
        self.requires("p8-platform/2.1.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built kodi-platform consumer cannot run on this host")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_kodi_platform")
        self.run(test_bin, env="conanrun")
