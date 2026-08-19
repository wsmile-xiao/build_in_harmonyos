#!/usr/bin/env python3
"""Conan test package for Qt Quick Timeline 6.11.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QtQuickTimelineTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        prefixes = [
            dependency.package_folder
            for dependency in self.dependencies.host.values()
        ]
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        # The umbrella Qt6Config only scans its own prefix for add-on modules
        # (Core/Gui come from qtbase, Qml from qtdeclarative). Expose every
        # dependency prefix so find_package(Qt6 COMPONENTS Qml) resolves.
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(prefixes)
        tc.generate()
        env = Environment()
        timeline_pkg = self.dependencies["qtquicktimeline"].package_folder
        env.prepend_path("QML2_IMPORT_PATH", os.path.join(timeline_pkg, "qml"))
        env.vars(self).save_script("conanrun_qtquicktimeline")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "qtquicktimeline test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qtquicktimeline")
            self.run(
                executable,
                env=["conanrun", "conanrun_qtquicktimeline"],
                ignore_errors=False,
            )
