#!/usr/bin/env python3
"""Conan test_package for syndication 6.26.0.

Compiles a small consumer against the installed KF6SyndicationConfig.cmake
and links libKF6Syndication.so, then parses a hard-coded RSS 2.0 feed and
validates the result (R34: real API usage, no empty shell test).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SyndicationTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kcodecs/6.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Consumer-side C++20 to match the library ABI expectations
        # (KDEFrameworkCompilerSettings builds the lib as C++20).
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        tc.generate()

        # qtbase / kcodecs are consumed with cmake_find_mode=none, so
        # CMakeDeps does not add their lib/cmake builddirs to
        # CMAKE_PREFIX_PATH. The KF6SyndicationConfig.cmake installed by the
        # package resolves find_dependency(KF6Codecs/Qt6Xml) at consumer
        # time, so every dependency package folder must be on the path.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "'
                    + dep.package_folder
                    + '/lib/cmake")'
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "'
                    + dep.package_folder
                    + '/lib")'
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "'
                    + dep.package_folder
                    + '/include")'
                )
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            # Qt6 module configs (Qt6Core) are found through the additional
            # prefixes list (Qt6 convention).
            prefixes = [
                dep.package_folder
                for dep in list(self.dependencies.values())
                + list(self.dependencies.build.values())
                if dep and dep.package_folder
            ]
            lines.append(
                'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH "'
                + ";".join(prefixes)
                + '")'
            )
            lines.append(
                'set(CONAN_RUNTIME_LIB_DIRS "'
                + os.path.join(qtbase.package_folder, "lib")
                + '")'
            )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, "lib"),
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins"),
                )
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_syndication"),
                env="conanrun",
            )
