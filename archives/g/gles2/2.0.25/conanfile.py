#!/usr/bin/env python3
"""Conan recipe for gles2 2.0.25 — CMake build system.

gles2 is a cross-platform wrapper for OpenGL ES 2.0 API.
This recipe builds the dummy wrapper (stub implementations) as a static library.
The upstream uses a custom "Yip" build system; we replace it with CMake.
"""
import os

from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


CMAKE_CONTENT = (
    "cmake_minimum_required(VERSION 3.15)\n"
    "project(gles2 CXX)\n"
    "\n"
    "set(GLES2_SOURCES\n"
    "    gl.cpp\n"
    "    gl_error.cpp\n"
    "    dummy/dummy_gl.cpp\n"
    ")\n"
    "\n"
    "add_library(gles2 STATIC ${GLES2_SOURCES})\n"
    "target_include_directories(gles2 PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})\n"
    "\n"
    "install(TARGETS gles2 ARCHIVE DESTINATION lib)\n"
    "install(FILES gl.h gl_constants.h gl_error.h DESTINATION include)\n"
)


class Gles2Conan(ConanFile):
    name = "gles2"
    version = "2.0.25"
    description = "Cross-platform wrappers for OpenGL ES 2.0 API"
    license = "MIT"
    homepage = "https://github.com/yiptool/gles2"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Upstream uses custom "Yip" build system; generate CMakeLists.txt
        # in source() so it lands in the source folder (not build folder)
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), CMAKE_CONTENT)

    def generate(self):
        tc = CMakeToolchain(self)
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
        self.cpp_info.libs = ["gles2"]
