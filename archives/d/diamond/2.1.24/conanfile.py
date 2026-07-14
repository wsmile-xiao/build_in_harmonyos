#!/usr/bin/env python3
"""Conan recipe for diamond — protein sequence aligner (CMake project).

diamond is a high-performance BLAST-compatible protein sequence alignment tool.
On aarch64/HarmonyOS, requires -DAARCH64=ON -DX86=OFF to avoid x86 SIMD targets.
See: https://github.com/bbuchfink/diamond
"""
import os

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class DiamondConan(ConanFile):
    name = "diamond"
    version = "2.1.24"
    description = "DIAMOND — BLAST-compatible protein sequence aligner for high-throughput analysis"
    license = "GPL-3.0-only"
    homepage = "https://github.com/bbuchfink/diamond"
    url = "https://github.com/bbuchfink/diamond"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: static linking for system-portability
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # aarch64-specific: disable x86 SIMD targets, enable NEON
        if self.settings.arch in ("armv8", "aarch64"):
            tc.variables["AARCH64"] = "ON"
            tc.variables["X86"] = "OFF"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix CMakeLists.txt: replace manual find_library with Conan CMakeDeps targets
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_file, "r") as f:
            content = f.read()
        # Replace the sqlite3 manual find block (lines 486-492) with find_package
        old_block = (
            "#find_package(SQLite3)\n"
            "#target_link_libraries(diamond SQLite::SQLite3 ${CMAKE_DL_LIBS})\n"
            'find_path(${SQLite3_INCLUDE_DIR} NAMES sqlite3.h PATHS ${SQLite3_INCLUDE_DIR})\n'
            'find_library(SQLite3_LIBRARY NAMES libsqlite3.a libsqlite3.so libsqlite3.so.0 sqlite3 '
            'HINTS /opt/homebrew/opt/sqlite/lib /usr/local/opt/sqlite/lib)\n'
            'message(STATUS "SQLite3 Library: ${SQLite3_LIBRARY}")\n'
            'target_include_directories(diamond PRIVATE "${SQLite3_INCLUDE_DIR}")\n'
            'target_link_libraries(diamond ${SQLite3_LIBRARY} ${CMAKE_DL_LIBS})'
        )
        new_block = (
            "find_package(sqlite3 REQUIRED)\n"
            "target_link_libraries(diamond sqlite3::sqlite3 ${CMAKE_DL_LIBS})"
        )
        content = content.replace(old_block, new_block)
        # Replace original find_package(ZLIB) with find_package(zlib) (Conan CMakeDeps)
        content = content.replace("find_package(ZLIB REQUIRED)", "find_package(zlib REQUIRED)")
        # Replace zlib ${ZLIB_LIBRARY} with zlib::zlib Conan target
        content = content.replace("${ZLIB_LIBRARY}", "zlib::zlib")
        # Remove ${ZLIB_INCLUDE_DIR} from include_directories (Conan CMakeDeps handles it)
        content = content.replace('"${ZLIB_INCLUDE_DIR}" ', "")
        with open(cmake_file, "w") as f:
            f.write(content)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]