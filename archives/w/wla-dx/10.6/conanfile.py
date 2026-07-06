#!/usr/bin/env python3
"""Conan recipe — wla-dx 10.6 (CMake, terminal tool).

wla-dx is a cross-assembler package producing multiple binary executables
(wla-gb, wla-z80, wla-6502, etc.) and wlalink/wlab utilities.
No shared libraries are produced.

R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
R27: Dependencies must reference .
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import check_min_cppstd


class WlaDxConan(ConanFile):
    name = "wla-dx"
    version = "10.6"
    description = "Yet another crossassembler package supporting GB-Z80/Z80/Z80N/6502/65C02/65CE02/65816/68000/6800/6801/6809/8008/8080/HUC6280/SPC-700/SuperFX"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/vhelin/wla-dx"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: Dependencies must reference 
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        from conan.tools.cmake import CMakeToolchain
        tc = CMakeToolchain(self)
        # Override profile generator "Make" -> "Unix Makefiles" for CMake 4.x
        tc.generator = "Unix Makefiles"
        # R26: Terminal tools must be statically linked
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # CMake 4.x compatibility: project uses cmake_minimum_required(VERSION 2.8.12)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        # wla-dx produces only executables (bin/), no libraries
        self.cpp_info.libs = []
        # Add bin directory to PATH for consumers
        self.cpp_info.bindirs = ["bin"]
