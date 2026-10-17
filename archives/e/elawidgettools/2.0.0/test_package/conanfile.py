#!/usr/bin/env python3
"""Conan test_package for ElaWidgetTools 2.0.0."""
import os
import shlex
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

class ElaWidgetToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")
    def layout(self):
        cmake_layout(self)
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    def test(self):
        test_bin = os.path.join(self.build_folder, "test_ElaWidgetTools")
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_lib = os.path.join(qt5.package_folder, "lib")
        qt5_plugins = os.path.join(qt5.package_folder, "plugins")
        cmd = (
            f"export LD_LIBRARY_PATH={shlex.quote(qt5_lib)}:$LD_LIBRARY_PATH && "
            f"export QT_QPA_PLATFORM=offscreen && "
            f"export QT_PLUGIN_PATH={shlex.quote(qt5_plugins)} && "
            f"{shlex.quote(test_bin)}"
        )
        self.run(cmd)
