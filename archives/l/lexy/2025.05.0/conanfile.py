#!/usr/bin/env python3
"""Conan recipe for lexy 2025.05.0 — C++17 parser combinator library.

lexy's core is header-only (INTERFACE CMake targets: lexy_core / lexy_dev /
lexy_unicode / lexy_ext / lexy / _lexy_base), with a single STATIC target
`lexy_file` (compiled from src/input/file.cpp). The upstream CMake build
compiles lexy_file, installs the public headers (include/lexy + include/lexy_ext)
and the foonathan:: CMake package config, which is exactly what this recipe
relies on.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LexyConan(ConanFile):
    name = "lexy"
    version = "2025.05.0"
    description = "C++17 parser combinator library (DSL-based parsing, Unicode-aware)"
    license = "BSL-1.0"
    homepage = "https://github.com/foonathan/lexy"
    url = ""  # CI fills this
    topics = ("parser", "combinator", "grammar", "lexing")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable upstream optional components (tests/examples/benchmarks/docs/
        # package zip) so the library itself builds without fetching doctest.
        tc.variables["LEXY_BUILD_TESTS"] = "OFF"
        tc.variables["LEXY_BUILD_EXAMPLES"] = "OFF"
        tc.variables["LEXY_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["LEXY_BUILD_DOCS"] = "OFF"
        tc.variables["LEXY_BUILD_PACKAGE"] = "OFF"
        tc.variables["LEXY_ENABLE_INSTALL"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Headers are the primary API; lexy_file is the only compiled (STATIC)
        # component. Mirror upstream CMake package: find_package(lexy) + foonathan::lexy.
        self.cpp_info.set_property("cmake_file_name", "lexy")
        self.cpp_info.set_property("cmake_target_name", "foonathan::lexy")
        self.cpp_info.set_property("cmake_build_modules", [])
        self.cpp_info.libs = ["lexy_file"]
