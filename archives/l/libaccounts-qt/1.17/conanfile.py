#!/usr/bin/env python3
"""Conan recipe — libaccounts-qt 1.17 (Qt6 flavour) for HarmonyOS PC.

Upstream ships a qmake-only build (accounts-qt.pro). The conan qtbase package
provides no qmake executable, so this recipe builds with a hand-written
CMakeLists.txt shipped via exports_sources (same approach as the 1.13 recipe),
targeting Qt6 (AccountsQt6, required by kaccounts-integration >= 1.16).

Dependency note: glib2 is declared with transitive_headers/transitive_libs so
the Accounts/*.h headers that pull in glib/gio types resolve for consumers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches


class LibaccountsQtConan(ConanFile):
    name = "libaccounts-qt"
    version = "1.17"
    description = "libaccounts-qt — a Qt library for managing online account configurations and authentication"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("qtbase/6.11.1.1")
        self.requires("libaccounts-glib/1.27")
        # glib2 types appear in the public Accounts headers -> keep it exported
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consumers (kaccounts-integration) do find_package(AccountsQt6 1.16)
        deps.set_property("libaccounts-qt", "cmake_file_name", "AccountsQt6")
        deps.generate()

        tc = CMakeToolchain(self)
        # qtbase on ohpcd exposes Qt's own Qt6Config.cmake from its package
        # folder (CMakeDeps emits no Qt6 config for it), so point CMake at it.
        qtbase_folder = self.dependencies["qtbase"].package_folder
        qt6_dir = os.path.join(qtbase_folder, "lib", "cmake", "Qt6")
        if os.path.isdir(qt6_dir):
            tc.variables["Qt6_DIR"] = qt6_dir
        # gio-unix-2.0 headers (needed by libaccounts-glib headers) live in a
        # subdirectory of the glib2 package that CMakeDeps does not export.
        glib2_folder = self.dependencies["glib2"].package_folder
        gio_unix = os.path.join(glib2_folder, "include", "gio-unix-2.0")
        if os.path.isdir(gio_unix):
            tc.variables["GLIB_GIO_UNIX_INCLUDE_DIR"] = gio_unix
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
        self.cpp_info.set_property("cmake_file_name", "AccountsQt6")
        self.cpp_info.set_property("cmake_target_name", "AccountsQt6::AccountsQt6")
        self.cpp_info.set_property("pkg_config_name", "accounts-qt6")
        self.cpp_info.libs = ["accounts-qt6"]
        self.cpp_info.includedirs = ["include/accounts-qt"]
        self.cpp_info.cxxstd = "17"
