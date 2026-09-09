#!/usr/bin/env python3
"""Conan recipe for box2d 3.1.1 — CMake 2D physics engine (C API).

Build: CMake. No external runtime dependencies (extern/ glad+jsmn are
samples-only). Unit tests verified separately; recipe builds the static
library + installs public headers and CMake package config.

OHOS notes:
- BOX2D_UNIT_TESTS / BOX2D_SAMPLES / BOX2D_BENCHMARKS disabled in recipe
  build (tests validated during adaptation; samples need GL/graphics).
- Static library (BUILD_SHARED_LIBS=OFF default) — safe for OHOS.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Box2DConan(ConanFile):
    name = "box2d"
    version = "3.1.1"
    description = "Box2D is a 2D rigid body simulation library for games"
    license = "MIT"
    homepage = "https://box2d.org"
    url = "https://github.com/erincatto/box2d"

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
        tc.variables["BOX2D_UNIT_TESTS"] = "OFF"
        tc.variables["BOX2D_SAMPLES"] = "OFF"
        tc.variables["BOX2D_BENCHMARKS"] = "OFF"
        tc.variables["BOX2D_DOCS"] = "OFF"
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
        self.cpp_info.libs = ["box2d"]
        self.cpp_info.set_property("cmake_file_name", "box2d")
        self.cpp_info.set_property("cmake_target_name", "box2d::box2d")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
