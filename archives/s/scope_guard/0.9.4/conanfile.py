#!/usr/bin/env python3
"""Conan recipe for scope_guard 0.9.4 — header-only C++ RAII scope guard library.

Upstream: https://github.com/Neargye/scope_guard (MIT, tag v0.9.4)
Build system: CMake INTERFACE (header-only). No runtime dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ScopeGuardConan(ConanFile):
    name = "scope_guard"
    version = "0.9.4"
    description = "Header-only C++11 RAII wrapper for executing arbitrary code at scope exit (scope_exit/scope_fail/scope_success)"
    license = "MIT"
    homepage = "https://github.com/Neargye/scope_guard"
    url = "https://github.com/Neargye/scope_guard"
    topics = ("scope-guard", "raii", "header-only", "scope-exit")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only: upstream tests/examples are exercised outside the recipe
        tc.variables["SCOPE_GUARD_OPT_BUILD_TESTS"] = "OFF"
        tc.variables["SCOPE_GUARD_OPT_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        src = str(self.source_folder)
        copy(self, "scope_guard.hpp",
             src=os.path.join(src, "include"),
             dst=os.path.join(str(self.package_folder), "include"))
        copy(self, "LICENSE",
             src=src,
             dst=str(self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
