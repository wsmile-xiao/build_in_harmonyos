#!/usr/bin/env python3
"""Conan recipe — wasm3 0.5.0 (CMake, WASM interpreter library).

wasm3 0.5.0 builds a static library `m3` (source/) plus an optional CLI
`wasm3` (platforms/app). The recipe ships the library; upstream has no
`make install` target, so packaging copies headers + static lib explicitly.

BUILD_WASI is pinned to "simple" (built-in SimpleWASI) to avoid fetching
the external uvwasi dependency at configure time (uvwasi requires network
FetchContent and is not needed for the interpreter library itself).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class Wasm3Conan(ConanFile):
    name = "wasm3"
    version = "0.5.0"
    description = "wasm3: a fast WebAssembly interpreter written in C"
    license = "MIT"
    homepage = "https://github.com/wasm3/wasm3"
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
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build the interpreter library only; avoid external uvwasi FetchContent
        tc.variables["BUILD_WASI"] = "simple"
        tc.variables["BUILD_NATIVE"] = "OFF"
        # R26: system-name libraries default to static; wasm3 has no install
        # target so BUILD_SHARED_LIBS is informational only
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # BUILD_WASI must be forced via -D: wasm3's CMakeLists sets its CACHE
        # default BEFORE project(), so toolchain CACHE vars are too late.
        cmake.configure(variables={"BUILD_WASI": "simple", "BUILD_NATIVE": "OFF"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        # upstream has no install target: package the static lib + headers
        cmake.install()
        copy(self, "*.a", src=str(self.build_folder), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "source"), dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["m3"]
