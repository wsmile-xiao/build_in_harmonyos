#!/usr/bin/env python3
"""Conan test_package - consumer view of the qca-qt6 library."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QcaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qca = self.dependencies["qca"]
        qt = self.dependencies["qtbase"]
        tc.variables["QCA_INCLUDE_DIR"] = os.path.join(
            qca.package_folder, "include", "Qca-qt6")
        tc.variables["QCA_LIBRARY_DIR"] = os.path.join(qca.package_folder, "lib")
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qt.package_folder, "lib", "cmake", "Qt6")
        # qca 包自带 Qt6Core5Compat（主配方 package() 打进包）——消费方
        # find_package(Qt6 Core5Compat) 通过本配置找到
        tc.cache_variables["Qt6Core5Compat_DIR"] = os.path.join(
            qca.package_folder, "lib", "cmake", "Qt6Core5Compat")
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qt.package_folder, "lib", "cmake", "Qt6", "platforms")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise RuntimeError("test_qca executable directory was not produced")
            env = Environment()
            for dependency in self.dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    env.append_path("LD_LIBRARY_PATH", os.path.join(
                        dependency.package_folder, libdir))
            with env.vars(self).apply():
                self.run(os.path.join(bindirs[0], "test_qca"))
