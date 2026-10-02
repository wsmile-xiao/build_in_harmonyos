#!/usr/bin/env python3
"""Conan test_package - consumer view of the qoauth library."""
import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

class QoauthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qca/2.3.10")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qoauth = self.dependencies["qoauth"]
        qca = self.dependencies["qca"]
        qt = self.dependencies["qtbase"]
        tc.variables["QOAUTH_INCLUDE_DIR"] = os.path.join(qoauth.package_folder, "include")
        tc.variables["QOAUTH_LIBRARY_DIR"] = os.path.join(qoauth.package_folder, "lib")
        tc.variables["QCA_INCLUDE_DIR"] = os.path.join(qca.package_folder, "include", "Qca-qt6")
        tc.variables["QCA_LIBRARY_DIR"] = os.path.join(qca.package_folder, "lib")
        tc.cache_variables["Qt6_DIR"] = os.path.join(qt.package_folder, "lib", "cmake", "Qt6")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise RuntimeError("test_qoauth executable directory was not produced")
            env = Environment()
            for dependency in self.dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    env.append_path("LD_LIBRARY_PATH", os.path.join(dependency.package_folder, libdir))
            with env.vars(self).apply():
                self.run(os.path.join(bindirs[0], "test_qoauth"))
