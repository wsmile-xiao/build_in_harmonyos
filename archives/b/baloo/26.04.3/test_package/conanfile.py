#!/usr/bin/env python3
"""Conan test_package for baloo 26.04.3 (upstream baloo 6.25.0).

Verifies that libKF6Baloo is consumable via CMake (find_package(KF6Baloo))
and that the Baloo::Query API is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class BalooTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append("list(PREPEND CMAKE_PREFIX_PATH "
                             "\"%s/lib/cmake\")" % dep.package_folder)
                lines.append("list(PREPEND CMAKE_LIBRARY_PATH "
                             "\"%s/lib\")" % dep.package_folder)
                lines.append("list(PREPEND CMAKE_INCLUDE_PATH "
                             "\"%s/include\")" % dep.package_folder)
        lines.append("list(PREPEND CMAKE_PREFIX_PATH "
                     "\"${CMAKE_CURRENT_LIST_DIR}\")")
        lines.append("list(PREPEND CMAKE_MODULE_PATH "
                     "\"${CMAKE_CURRENT_LIST_DIR}\")")
        paths_file = os.path.join(self.generators_folder,
                                  "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH",
                                 os.path.join(dep.package_folder, "plugins"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_kbaloo"), env="conanrun")
