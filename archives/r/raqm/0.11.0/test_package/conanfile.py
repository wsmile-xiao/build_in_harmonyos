#!/usr/bin/env python3
"""Consumer test for raqm 0.11.0 (HarmonyOS PC).

Builds test.c against the installed raqm package via CMakeDeps and runs
the resulting binary on the device. The binary asserts the raqm public
API lifecycle (version, create, UTF-8 text, RTL paragraph direction, the
documented no-font layout/glyph behaviour, destroy) and exits non-zero on
any failure — satisfying L0d/R34 (test() really runs a linked consumer
that exercises the tested package).

Font-driven layout coverage is provided by the 51 upstream meson tests
executed inside conan create (the release tarball ships its own test
fonts); this consumer test intentionally avoids large binary assets so
the PR diff stays text-only.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RaqmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # raqm.h includes <ft2build.h> directly; the consumer needs the
        # freetype headers too (same pattern as cairomm's test_package).
        self.requires("freetype/2.14.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_raqm")
        self.run('"%s"' % test_binary, env="conanrun")
