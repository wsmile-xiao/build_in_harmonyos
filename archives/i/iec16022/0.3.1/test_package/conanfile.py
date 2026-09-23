#!/usr/bin/env python3
"""Conan test_package for iec16022 0.3.1 — consumer-side (L1) verification.

Compiles test_iec16022.c against the *installed* package (public headers +
libiec16022) and runs it.  The test mirrors the upstream suite's reference
artefact, so a broken encoder, a mis-linked library or a bad installation all
fail here (R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Iec16022TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skipping test execution")
            return
        bindir = self.cpp.build.bindirs[0]
        binary = os.path.join(bindir, "test_iec16022")
        if not os.path.isfile(binary):
            raise Exception(f"test binary was not built: {binary}")
        self.run(f'"{binary}"', env="conanrun")
