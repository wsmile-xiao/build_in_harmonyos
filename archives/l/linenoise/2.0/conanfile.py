#!/usr/bin/env python3
"""Conan recipe for linenoise 2.0.

linenoise is a minimal, zero-config, BSD-licensed readline replacement
(antirez/linenoise). Upstream ships a plain Makefile with no configure
script and no install target, so this recipe generates a small
CMakeLists.txt (same pattern as MurmurHash3 recipe) to build and
install the library.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches


class LinenoiseConan(ConanFile):
    name = "linenoise"
    version = "2.0"
    description = "A minimal, zero-config, BSD-licensed readline replacement"
    license = "BSD-2-Clause"
    homepage = "https://github.com/antirez/linenoise"
    url = "https://github.com/antirez/linenoise"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Upstream has no CMake build; provide one (build only the library).
        cmake_content = """cmake_minimum_required(VERSION 3.15)
project(linenoise C)

add_library(linenoise linenoise.c)
add_library(linenoise::linenoise ALIAS linenoise)
target_include_directories(linenoise PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

install(TARGETS linenoise
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib)
install(FILES linenoise.h DESTINATION include)
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["linenoise"]
