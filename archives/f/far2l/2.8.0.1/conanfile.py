#!/usr/bin/env python3
"""Conan recipe for far2l 2.8.0 — Linux port of FAR Manager.

far2l is a terminal (and optionally GUI) file manager originally ported
from Windows FAR Manager.  This recipe builds the TTY-only, plugin-minimal
variant suitable for HarmonyOS (musl libc, aarch64).

Key adaptations:
  - Disable GUI (USEWX=NO), X11 extensions (TTYX=NO), uchardet (USEUCD=NO)
  - Disable colorer plugin (COLORER=NO) which requires LibXml2 not available
  - Disable NetRocks (NETROCKS=NO) and multiarc (MULTIARC=NO) to avoid
    un-adapted optional dependencies (samba, nfs, neon, aws-sdk, etc.)
  - Enable MUSL=YES which adds -D__MUSL__ across the whole project
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 for CMake 4.x compatibility (E187)
  - Testing disabled (TESTING=NO) since the upstream smoke framework
    requires Go + network access unavailable on-device
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)


class Far2lConan(ConanFile):
    name = "far2l"
    version = "2.8.0.1"
    license = "GPL-2.0"
    homepage = "https://github.com/elfmz/far2l"
    url = "https://github.com/elfmz/far2l"
    description = "Linux port of FAR Manager — terminal file manager"
    topics = ("file-manager", "terminal", "far-manager")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # --- Disable un-adapted or unavailable backends/plugins ---
        tc.variables["USEWX"] = "NO"       # wxWidgets GUI not available
        tc.variables["TTYX"] = "NO"        # X11 TTY extensions not needed
        tc.variables["USEUCD"] = "NO"      # uchardet not adapted
        tc.variables["COLORER"] = "NO"     # colorer plugin needs LibXml2
        tc.variables["NETROCKS"] = "NO"    # network protocols — deps not published
        tc.variables["MULTIARC"] = "NO"    # multiarc archive plugin — libarchive optional
        tc.variables["PYTHON"] = "NO"      # Python plugin disabled
        tc.variables["TESTING"] = "NO"     # upstream smoke tests need Go + network
        tc.variables["LEGACY"] = "NO"      # legacy registry support disabled
        # --- musl / OHOS semantic alignment ---
        tc.variables["MUSL"] = "YES"       # adds -D__MUSL__ globally
        # --- C++ standard explicit (E096) ---
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # --- CMake 4.x compatibility (E103/E187) ---
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy license
        copy(
            self,
            "LICENSE.txt",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        # Clean up cmake config files that should not be in an application package
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share", "cmake"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
