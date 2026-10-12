#!/usr/bin/env python3
"""Conan recipe — libsignon-qt 8.61 (Qt6 flavour) for HarmonyOS PC.

Upstream is qmake-only (lib/SignOn/libsignon-qt.pri: TEMPLATE=lib,
TARGET=signon-qt5, CMAKE_BASENAME=SignOnQt5) and the conan qtbase package has
no OHOS mkspec, so this recipe builds with a hand-written CMakeLists.txt
shipped via exports_sources, targeting Qt6: target signon-qt6 / CMake package
SignOnQt6 — the name kaccounts-integration requires
(find_package(SignOnQt6 8.55 CONFIG)).

Scope: only the client library (lib/SignOn). The signond daemon and its
plugins (server/, src/) are out of scope for this package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibsignonQtConan(ConanFile):
    name = "libsignon-qt"
    version = "8.61"
    description = "libsignon-qt — Qt6 client library for the Single Sign On daemon (signond)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/accounts-sso/signond"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "CMakeLists.txt", "SignOnQt6Config.cmake.in", "libsignon-qt6.pc.in"

    def export_sources(self):
        export_conandata_patches(self)
        for f in ("CMakeLists.txt", "SignOnQt6Config.cmake.in", "libsignon-qt6.pc.in"):
            copy(self, f, src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("qtbase/6.11.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consumers look the package up as SignOnQt6 (kaccounts-integration:
        # find_package(SignOnQt6 8.55 CONFIG)).
        deps.set_property("libsignon-qt", "cmake_file_name", "SignOnQt6")
        deps.generate()

        tc = CMakeToolchain(self)
        # qtbase on ohpcd sets cmake_find_mode=none and ships Qt's own
        # Qt6Config.cmake from its package folder (CMakeDeps emits no Qt6
        # config for it), so point CMake at that folder explicitly.
        qtbase_folder = self.dependencies["qtbase"].package_folder
        qt6_dir = os.path.join(qtbase_folder, "lib", "cmake", "Qt6")
        if os.path.isdir(qt6_dir):
            tc.variables["Qt6_DIR"] = qt6_dir
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SignOnQt6")
        self.cpp_info.set_property("cmake_target_name", "SignOnQt6::SignOnQt6")
        self.cpp_info.set_property("pkg_config_name", "libsignon-qt6")
        self.cpp_info.libs = ["signon-qt6"]
        self.cpp_info.includedirs = ["include/signon-qt6"]
        self.cpp_info.cxxstd = "17"
