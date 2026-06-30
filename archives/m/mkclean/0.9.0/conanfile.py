#!/usr/bin/env python3
"""Conan recipe for mkclean 0.9.0 — CMake projects.

Build system: cmake (with bundled corec/libebml2/libmatroska2)
This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class MkcleanConan(ConanFile):
    name = "mkclean"
    version = "0.9.0"
    description = "mkclean - Matroska stream cleaning tool"
    license = "MIT"
    homepage = "https://www.matroska.org/downloads/mkclean.html"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies — corec/libebml2/libmatroska2 are bundled
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # cmake 4.x removed compatibility with cmake_minimum_required < 3.5
        # Must use cache_variables (command-line -D) not variables (toolchain file set())
        # because cmake_minimum_required is processed before the toolchain file
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # HarmonyOS is not recognized by cmake as UNIX; force Linux to trigger
        # UNIX code paths (str_linux.c, file_libc.c, date_libc.c, ccsystem_posix.c)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Fix: profile sets generator=Make which is invalid in cmake 4.x
        tc.generator = "Unix Makefiles"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # mkclean CMakeLists.txt has no install() for executables, copy manually
        copy(self, "mkclean", src=os.path.join(self.build_folder, "mkclean"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mkWDclean", src=os.path.join(self.build_folder, "mkclean"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["corec", "ebml2", "matroska2"]
