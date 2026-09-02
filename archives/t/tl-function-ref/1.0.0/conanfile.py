#!/usr/bin/env python3
"""Conan recipe — tl-function-ref 1.0.0 (header-only, CMake).

TartanLlama/function_ref is a single-header C++14 low-overhead
non-owning function reference.  Build is CMake-only (no configure).
Recipe follows the OHOS header-only pattern: fetch official source,
install headers + CMake config via CMakeToolchain/CMake.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.scm import Version
import os


class TlFunctionRefConan(ConanFile):
    name = "tl-function-ref"
    version = "1.0.0"
    description = "A low-overhead, non-owning function reference for C++14"
    license = "CC0-1.0"
    homepage = "https://github.com/TartanLlama/function_ref"
    url = "https://github.com/TartanLlama/function_ref"
    topics = ("function", "functional", "header-only", "c++14")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "header-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Header-only: nothing to compile; keep tests out of the package build.
        tc = CMakeToolchain(self)
        tc.variables["FUNCTION_REF_ENABLE_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        # Header-only package: no code to compile.  Building via upstream CMake
        # would FetchContent-clone tl-cmake from GitHub on every create (slow
        # and network-fragile); the header is packaged directly instead.
        pass

    def package(self):
        # Direct header copy (no CMake install: build() is a no-op for
        # header-only, so no cmake_install.cmake exists).
        copy(self, "function_ref.hpp", src=os.path.join(self.source_folder, "include", "tl"),
             dst=os.path.join(self.package_folder, "include", "tl"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "tl-function-ref")
        self.cpp_info.set_property("cmake_target_name", "tl::function_ref")
        # Header-only: dependents get the include dir and CMake config.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
