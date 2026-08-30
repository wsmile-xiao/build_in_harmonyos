#!/usr/bin/env python3
"""Conan recipe — uriparser 1.0.2 (CMake project).

uriparser is a self-contained RFC 3986 URI parsing C library with a small
command-line tool `uriparse`. No runtime dependencies.

License: BSD-3-Clause for the library (test suite LGPL-2.1-or-later, fuzzing
code Apache-2.0 — neither is packaged here).

Build notes:
- Direct CMake build. The upstream `configure` is a bash-only CMake wrapper
  (uses `[[ =~ ]]`, `type -P`, ...) that OHOS /bin/sh cannot run, so we build
  with CMake directly (same conclusion as the historical liburiparser notes).
- URIPARSER_BUILD_TESTS requires GTest; the upstream test suite is built and
  executed in a separate upstream-test step, not inside the packaged build.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class UrparserConan(ConanFile):
    name = "uriparser"
    version = "1.0.2"
    description = "uriparser: RFC 3986 URI parsing library"
    license = "BSD-3-Clause"
    homepage = "https://uriparser.github.io/"
    url = ""  # CI fills this

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
        # uriparser CMake options: library + uriparse tool, no docs/fuzzers/tests
        tc.variables["URIPARSER_BUILD_DOCS"] = "OFF"
        tc.variables["URIPARSER_BUILD_TESTS"] = "OFF"
        tc.variables["URIPARSER_BUILD_FUZZERS"] = "OFF"
        tc.variables["URIPARSER_BUILD_TOOLS"] = "ON"
        tc.variables["URIPARSER_BUILD_CHAR"] = "ON"
        tc.variables["URIPARSER_BUILD_WCHAR_T"] = "ON"
        tc.variables["URIPARSER_ENABLE_INSTALL"] = "ON"
        tc.variables["URIPARSER_WARNINGS_AS_ERRORS"] = "OFF"
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
        self.cpp_info.libs = ["uriparser"]
