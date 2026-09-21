#!/usr/bin/env python3
"""Conan test_package consumer for KSyntaxHighlighting 5.116.0 (KF5).

The consumer simulates a business-layer component that links the real public
API of KF5SyntaxHighlighting: it loads the bundled C++ syntax definition and
the default light theme through KSyntaxHighlighting::Repository.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KsyntaxhighlightingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # Rebuild the aggregated Qt5Config (qt5-qtbase only ships per-module
        # configs; find_package(Qt5 COMPONENTS Core Gui) needs one).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        # The installed KF5SyntaxHighlightingConfig.cmake calls
        # find_dependency(Qt5Core)/find_dependency(Qt5Gui) with legacy module
        # names; and the main package uses cmake_find_mode=none, so CMakeDeps
        # does NOT emit a wrapper config for it. Point CMAKE_PREFIX_PATH at
        # both the main package's lib/cmake (KF5SyntaxHighlightingConfig.cmake)
        # and the qtbase lib/cmake (native Qt5CoreConfig.cmake/Qt5GuiConfig.cmake)
        # so every find_package() in the consumer resolves.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep_name in ("ksyntax-highlighting", "qt5-qtbase"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % pkg)
                lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % pkg)
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % pkg)
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = self._runtime_env()
        with env.vars(self).apply():
            exe = os.path.join(self.cpp.build.bindirs[0], "test_ksyntax_highlighting")
            self.run(exe, env="conanrun")

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "bin"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env
