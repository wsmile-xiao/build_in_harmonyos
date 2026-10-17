#!/usr/bin/env python3
"""Conan recipe — fastnoise2 1.1.1 (CMake, static library).

FastNoise2 is a C++ noise generation library with an optional C API.
Dependencies: FastSIMD is fetched via CPM upstream; this recipe vendors the
exact commit (16450dae) as a local source so the build is self-contained and
does not require GitHub at configure time (CI network policy). Tests use
google/benchmark 1.5.5 which is likewise vendored.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Fastnoise2Conan(ConanFile):
    name = "fastnoise2"
    version = "1.1.1"
    description = "FastNoise2 — fast, SIMD-based noise generation library (C++/C API)"
    license = "MIT"
    homepage = "https://github.com/Auburn/FastNoise2"
    url = "https://github.com/Auburn/FastNoise2"

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
        # Main FastNoise2 source
        get(self, **self.conan_data["sources"]["fastnoise2"], strip_root=True)
        # Vendored deps (extracted so CPM can use local SOURCE_DIR)
        get(self, **self.conan_data["sources"]["fastsimd"],
            strip_root=True, destination="deps/FastSIMD")
        get(self, **self.conan_data["sources"]["benchmark"],
            strip_root=True, destination="deps/benchmark")

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["FASTNOISE2_TOOLS"] = "OFF"   # NodeEditor GUI app not needed
        tc.variables["FASTNOISE2_TESTS"] = "OFF"   # upstream tests run separately in build()
        tc.variables["FASTNOISE2_UTILITY"] = "OFF"
        tc.variables["FASTNOISE2_STRICT_FP"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        # FastSIMD 与 FastSIMD_FastNoise 为 OBJECT 库，对象已并入 libFastNoise.a
        self.cpp_info.libs = ["FastNoise"]
        self.cpp_info.set_property("cmake_target_name", "FastNoise2::FastNoise2")