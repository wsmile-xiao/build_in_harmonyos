#!/usr/bin/env python3
"""Conan test_package for liquidsfz — real SFZ render round-trip.

This is the L1 consumer test. CI runs it automatically via `conan create`.
The binary writes a PCM16 WAV fixture, references it from a generated SFZ
file, loads it through LiquidSFZ::Synth and asserts a non-silent render.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LiquidsfzTestConan(ConanFile):
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
        # Fail closed (libicns precedent): CI builds with host=build=OHOS so
        # can_run() is True there; a False here means a genuine cross build
        # where these binaries cannot execute — skip would be a false green.
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "liquidsfz test_package must run natively on the target"
            )
        bindir = self.cpp.build.bindirs[0]
        # Scratch directory for wav/sfz fixtures (writable build folder; the
        # test creates and cleans up its own subdirectory inside it).
        self.run("\"{0}\" \"{1}\"".format(os.path.join(bindir, "test_liquidsfz"),
                                          self.build_folder),
                 env="conanrun")
