#!/usr/bin/env python3
"""Conan recipe — cpp-can-parser 1.0.0 (CMake build).

cpp-can-parser is a C++ library for parsing CAN databases (DBC format),
built with CMake (cmake_minimum_required 3.7). Official upstream:
https://github.com/xatavian/cpp-can-parser (tag v1.0.0, LGPL-3.0).

Adaptation fixes (patch cpp_can_parser_cmake_fixes.patch, required for the
build to work at all on any platform):
  1. target_include_directories: add include/cpp-can-parser to PRIVATE dirs —
     upstream source files do `#include "CANDatabase.h"` while the header
     lives in include/cpp-can-parser/ (upstream only exposes the PUBLIC root
     include/), so the library itself could not compile.
  2. install rules: upstream `install(FILES cpp-can-parser ...)` referenced a
     non-existent path and installed into the build dir; replaced with
     install(TARGETS ...) lib + headers + generated export header.
  3. test target: cpc-test-parsing needs include/cpp-can-parser on its include
     path (`#include "CANDatabase.h"` in tests/test-parsing.cpp).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CppCanParserConan(ConanFile):
    name = "cpp-can-parser"
    version = "1.0.0"
    description = "C++ library for parsing CAN databases (DBC format)"
    license = "LGPL-3.0"
    homepage = "https://github.com/xatavian/cpp-can-parser"
    url = "https://github.com/xatavian/cpp-can-parser"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required 3.7; CMake 4 removed
        # compatibility with < 3.5, so 3.7 is fine without policy pinning.
        # Native OHOS build with clang; CMake has no OHOS platform module but the
        # library uses only the C++ standard library, so Linux mapping suffices.
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # Upstream builds a shared library by default; honor the shared option.
        toolchain.cache_variables["CPP_CAN_PARSER_USE_STATIC"] = (
            "ON" if not self.options.shared else "OFF"
        )
        # Upstream tests are exercised via the adapted build/test gate; the
        # packaged library itself must not build/register tests (a native CI
        # consumer runs its own check via test_package).
        toolchain.cache_variables["BUILD_TESTING"] = "OFF"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cpp-can-parser"]
        self.cpp_info.set_property("pkg_config_name", "cpp-can-parser")
