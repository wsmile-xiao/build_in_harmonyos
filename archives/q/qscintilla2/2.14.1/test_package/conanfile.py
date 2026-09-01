#!/usr/bin/env python3
"""Conan test_package - consumer view of the qscintilla2 library."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QScintilla2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qscintilla = self.dependencies["qscintilla2"]
        qt = self.dependencies["qtbase"]
        tc.variables["QSCINTILLA_INCLUDE_DIR"] = os.path.join(
            qscintilla.package_folder, "include")
        tc.variables["QSCINTILLA_LIBRARY_DIR"] = os.path.join(
            qscintilla.package_folder, "lib")
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qt.package_folder, "lib", "cmake", "Qt6")
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qt.package_folder, "lib", "cmake", "Qt6", "platforms")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_qscintilla2 executable directory was not produced")
        cmd = os.path.join(bindirs[0], "test_qscintilla2")
        if not can_run(self):
            return
        lib_paths = []
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                lib_paths.append(os.path.join(dependency.package_folder, libdir))
        qt_prefix = self.dependencies["qtbase"].package_folder
        if qt_prefix:
            lib_paths.insert(0, os.path.join(qt_prefix, "lib"))
        self.run(
            "QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH={} {}".format(
                shlex.quote(os.pathsep.join(lib_paths)), shlex.quote(cmd)),
            env="conanrun")
