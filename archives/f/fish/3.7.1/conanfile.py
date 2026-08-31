#!/usr/bin/env python3
"""Conan recipe for fish 3.7.1 on HarmonyOS PC.

fish is a smart and user-friendly command line shell.
Build system: CMake.
Produces executables: fish, fish_indent, fish_key_reader.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FishConan(ConanFile):
    name = "fish"
    version = "3.7.1"
    description = "fish is a smart and user-friendly command line shell"
    license = "GPL-2.0-only"
    homepage = "https://fishshell.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")
        self.requires("pcre2/10.45.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Use system PCRE2 (provided by conan dependency)
        tc.variables["FISH_USE_SYSTEM_PCRE2"] = True
        # Point cmake to conan-provided ncurses
        ncurses = self.dependencies["ncurses"]
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        tc.variables["CURSES_INCLUDE_PATH"] = ncurses_inc
        tc.variables["CURSES_NCURSES_LIBRARY"] = os.path.join(ncurses_lib, "libncursesw.a")
        # Point cmake to conan-provided pcre2
        pcre2 = self.dependencies["pcre2"]
        pcre2_lib = os.path.join(pcre2.package_folder, "lib")
        pcre2_inc = os.path.join(pcre2.package_folder, "include")
        # fish's PCRE2.cmake uses find_library/find_path, pass via cmake vars
        tc.variables["CMAKE_LIBRARY_PATH"] = pcre2_lib
        tc.variables["CMAKE_INCLUDE_PATH"] = pcre2_inc
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
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
