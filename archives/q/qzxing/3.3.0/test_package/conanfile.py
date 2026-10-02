#!/usr/bin/env python3
"""Conan test_package for qzxing/3.3.0 — consumer view of the library."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class QzxingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("qzxing_probe executable directory was not produced")
        cmd = os.path.join(bindirs[0], "qzxing_probe")
        if not can_run(self):
            return
        lib_paths = []
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                lib_paths.append(os.path.join(dependency.package_folder, libdir))
        qt_prefix = self.dependencies["qt5-qtbase"].package_folder
        if qt_prefix:
            lib_paths.insert(0, os.path.join(qt_prefix, "lib"))
        self.run(
            "QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH={paths}:$LD_LIBRARY_PATH {exe}".format(
                paths=shlex.quote(os.pathsep.join(lib_paths)),
                exe=shlex.quote(cmd)),
            env="conanrun")
