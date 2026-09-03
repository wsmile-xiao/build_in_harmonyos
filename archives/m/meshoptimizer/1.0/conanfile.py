#!/usr/bin/env python3
"""Conan recipe — meshoptimizer 1.0 (CMake).

meshoptimizer is a C++ mesh optimization library (simplify, optimize,
build/process meshes) by Arseny Kapoulkine (zeux). Header + static/shared
library build via CMake, MIT licensed, no runtime dependencies.

R26: static-by-default (not a system-name library; shared opt-in allowed).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MeshoptimizerConan(ConanFile):
    name = "meshoptimizer"
    version = "1.0"
    description = "Mesh optimization library that makes meshes smaller and faster to render"
    license = "MIT"
    homepage = "https://github.com/zeux/meshoptimizer"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Library-only package: no demo/gltfpack binaries, no WASM tools.
        tc.variables["MESHOPT_BUILD_DEMO"] = "OFF"
        tc.variables["MESHOPT_BUILD_GLTFPACK"] = "OFF"
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
        self.cpp_info.libs = ["meshoptimizer"]
        self.cpp_info.set_property("cmake_file_name", "meshoptimizer")
        self.cpp_info.set_property("cmake_target_name", "meshoptimizer::meshoptimizer")
