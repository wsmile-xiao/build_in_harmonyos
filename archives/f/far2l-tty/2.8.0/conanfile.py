#!/usr/bin/env python3
"""Conan recipe for far2l-tty 2.8.0 — TTY-only Unix port of FAR Manager.

far2l-tty is the plain-terminal flavour of far2l (Linux port of FAR Manager v2):
no wxWidgets GUI backend, no X11 TTY extensions, no Python plugins and no SMB
protocol — matching Homebrew's far2l-tty formula (USEWX=OFF, USESDL=OFF,
TTYX=OFF, NR_SMB=OFF, NR_AWS=OFF, MULTIARC=ON, PYTHON=OFF, COLORER=ON).

HarmonyOS (musl libc, aarch64) convergence, proven by far2l/2.8.0.1:
  - USEWX=NO (no wxWidgets on OHOS), USESDL=NO, TTYX=NO (no X11)
  - USEUCD=NO (uchardet has no conan recipe in this repo)
  - COLORER=NO (colorer needs LibXml2; out of scope, same as far2l)
  - NETROCKS=NO (libnfs/uchardet have no conan recipes; neon is SSL-downgraded)
  - MULTIARC=NO (libarchive is published but scope-converged, same as far2l)
  - PYTHON=NO, TESTING=NO (upstream smoke needs Go toolchain + network),
    LEGACY=NO, MUSL=YES (-D__MUSL__ globally)
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 for CMake 4.x compatibility
  - No hard conan requires: all optional deps gracefully degrade inside
    upstream CMake (warnings only), so the build stays self-contained.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get, rmdir


class Far2lTtyConan(ConanFile):
    name = "far2l-tty"
    version = "2.8.0"
    license = "GPL-2.0-only"
    homepage = "https://github.com/elfmz/far2l"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Unix TTY port of FAR Manager v2 (plain terminal, no GUI/X11)"
    topics = ("file-manager", "terminal", "far-manager", "tty")

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

    def generate(self):
        tc = CMakeToolchain(self)
        # --- TTY-only backends (Homebrew far2l-tty alignment) ---
        tc.variables["USEWX"] = "NO"
        tc.variables["USESDL"] = "NO"
        tc.variables["TTYX"] = "NO"
        tc.variables["TTYXI"] = "NO"
        # --- Plugins converged for OHOS (same scope as far2l/2.8.0.1) ---
        tc.variables["USEUCD"] = "NO"
        tc.variables["COLORER"] = "NO"
        tc.variables["NETROCKS"] = "NO"
        tc.variables["NR_SMB"] = "NO"
        tc.variables["NR_AWS"] = "NO"
        tc.variables["MULTIARC"] = "NO"
        tc.variables["PYTHON"] = "NO"
        tc.variables["TESTING"] = "NO"
        tc.variables["LEGACY"] = "NO"
        # --- musl / OHOS semantic alignment ---
        tc.variables["MUSL"] = "YES"
        # --- C++ standard explicit ---
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # --- CMake 4.x compatibility ---
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.txt",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share", "cmake"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
