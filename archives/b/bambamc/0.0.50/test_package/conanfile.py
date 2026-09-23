#!/usr/bin/env python3
"""Conan test_package for bambamc — real consumer round-trip (CI test level L1).

Builds a small C consumer against the packaged library and runs it. The
consumer writes a BAM file through the public writer API, decodes it back
through the public decoder API and compares every field, so a broken package
fails the test instead of merely printing something.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BambamcTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_bambamc")
        # /tmp is read-only on the OHOS device: keep the fixture inside the
        # test_package build tree instead.
        bam = os.path.join(self.build_folder, "consumer_roundtrip.bam")
        self.run('"%s" "%s"' % (exe, bam), env="conanrun")
