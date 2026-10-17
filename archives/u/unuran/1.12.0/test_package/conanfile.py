#!/usr/bin/env python3
"""Conan test_package for unuran 1.12.0 (HarmonyOS PC / aarch64).

Builds one C consumer linked against the packaged unuran and runs it, which
exercises the installed layout (`include/unuran.h` plus the four auxiliary
public headers the upstream install rule adds, and `lib/libunuran.a`) and the
public API end to end: the string parser, the distr -> par -> init object
API, seeding determinism, sampling statistics, and — the HarmonyOS-specific
part — the LP64/IEEE-754 ABI assumptions and driving four independent
generators from four threads.

$TMPDIR is pointed at the test build folder for the same reason libxdg's
test_package does it: HarmonyOS keeps /tmp read-only and the workers' user
storage is HMDFS, so anything that reaches for a system temp directory has to
be given a writable one.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class UnuranTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        env.define("TMPDIR", self.build_folder)  # /tmp is read-only on OHOS
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_unuran"))
