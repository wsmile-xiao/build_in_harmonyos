#!/usr/bin/env python3
"""Conan test_package for libxdg 1.2.3 (HarmonyOS PC / aarch64).

Builds one C consumer linked against the packaged libxdg-basedir and runs it,
which exercises the installed layout (a single `include/` root holding
`basedir.h` and `basedir_fs.h`, plus `lib/libxdg-basedir.a`) and the public
API end to end.

$TMPDIR is pointed at the test build folder: HarmonyOS keeps /tmp read-only
and the workers' user storage is HMDFS, so the filesystem assertions in the
consumer test (mkdir/stat/access through xdgMakePath and the finders) must
run against a directory the CI knows is writable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibxdgTestConan(ConanFile):
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
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_libxdg"))
