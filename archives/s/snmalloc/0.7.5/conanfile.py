#!/usr/bin/env python3
"""Conan recipe for snmalloc 0.7.5 (CMake project, HarmonyOS PC adaptation).

Build: CMake-based header-heavy C++ memory allocator.
Adapted for OHOS: mitigations.h adds __OHOS__ branch disabling random_pagemap
(pagemap randomization would reserve ~1.25TB VA; HarmonyOS mmap single
reservation limit is ~256-384GB, causing ENOMEM at startup).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SnmallocConan(ConanFile):
    name = "snmalloc"
    version = "0.7.5"
    description = "snmalloc 0.7.5 - a fast, lightweight, memory allocator"
    license = "MIT"
    homepage = "https://github.com/microsoft/snmalloc"
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
        # snmalloc is header-heavy; build the static library target only.
        tc.variables["SNMALLOC_BUILD_TESTING"] = "OFF"
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
        # snmalloc installs the static library as libsnmallocshim-static.a
        # (the top-level "snmalloc" CMake target is an INTERFACE/header-only
        # target).  Expose the actual static lib; headers carry the API.
        self.cpp_info.libs = ["snmallocshim-static"]
        self.cpp_info.includedirs = ["include"]
        # The INTERFACE target in upstream CMakeLists propagates
        # SNMALLOC_USE_WAIT_ON_ADDRESS to consumers; replicate that here so
        # headers compile (ds/combininglock.h requires the macro).
        self.cpp_info.defines = ["SNMALLOC_USE_WAIT_ON_ADDRESS=1"]