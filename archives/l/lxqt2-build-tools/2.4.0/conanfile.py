#!/usr/bin/env python3
"""Conan recipe for lxqt2-build-tools 2.4.0 — LXQt CMake build helper modules.

The package installs:
  - CMake modules and find-modules (share/cmake/lxqt2-build-tools/)
  - the lxqt2-transupdate translation helper tool (bin/)

Qt6 is required at configure time: FindInstallConfigPath.cmake performs an
unconditional find_package(Qt6 REQUIRED) to query QT_INSTALL_CONFIGURATION.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Lxqt2BuildToolsConan(ConanFile):
    name = "lxqt2-build-tools"
    version = "2.4.0"
    description = "LXQt build helper: CMake modules and translation update tools"
    license = "BSD-3-Clause"
    homepage = "https://github.com/lxqt/lxqt-build-tools"
    url = "https://github.com/lxqt/lxqt-build-tools"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 needed at configure time: FindInstallConfigPath.cmake and
        # LXQtQueryQt.cmake call find_package(Qt6 REQUIRED).
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Make Qt6Config.cmake reachable for find_package(Qt6 REQUIRED).
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_prefix
        # Deterministic XDG config dir; avoids relying on qtpaths at configure time.
        tc.cache_variables["LXQT_ETC_XDG_DIR"] = "/etc/xdg"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # The package ships its own lxqt2-build-tools-config.cmake, so the
        # consumer's find_package(lxqt2-build-tools) resolves it directly.
        self.cpp_info.builddirs = [os.path.join("share", "cmake", "lxqt2-build-tools")]
        self.cpp_info.set_property("cmake_find_mode", "none")
