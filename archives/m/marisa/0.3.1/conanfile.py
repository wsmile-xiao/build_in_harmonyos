#!/usr/bin/env python3
"""Conan recipe for marisa 0.3.1 — CMake build system.

MARISA (Matching Algorithm with Recursively Implemented StorAge) is a static
and space-efficient trie data structure. libmarisa is its C++ library.

Build: static library only (BUILD_SHARED_LIBS=OFF), CLI tools disabled
(ENABLE_TOOLS=OFF) so the package ships a pure library. Native SIMD code
paths (ENABLE_NATIVE_CODE) stay off to avoid -march=native on the worker.
Upstream unit tests (BUILD_TESTING) are built and run via cmake.test().
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MarisaConan(ConanFile):
    name = "marisa"
    version = "0.3.1"
    description = "Static and space-efficient trie data structure (C++ library)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/s-yata/marisa-trie"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build a static library only — no .so to avoid polluting system
        # lib paths. marisa is not a system same-name library, but static is
        # the simplest, dependency-free deliverable for this adaptation.
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Ship the library only; the marisa-* CLI tools are thin wrappers and
        # are not part of this adaptation (keeps the package library-only).
        tc.variables["ENABLE_TOOLS"] = "OFF"
        # Keep native SIMD code paths off (avoid -march=native on the worker).
        tc.variables["ENABLE_NATIVE_CODE"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9: single-job build for the OHOS worker parallel constraint.
        cmake.build(cli_args=["--parallel", "1"])
        # ── Upstream official tests (base/io/vector/trie/marisa suites) ──
        cmake.test(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["marisa"]
