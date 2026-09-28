#!/usr/bin/env python3
"""Conan recipe — libgff 2.0.1 (CMake, static library).

Upstream: https://github.com/COMBINE-lab/libgff
Build: CMake, produces libgff.a + TestGFFParse; no external dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibgffConan(ConanFile):
    name = "libgff"
    version = "2.0.1"
    description = "A small C++ library for parsing and evaluating GFF/GTF files"
    license = "MIT"
    homepage = "https://github.com/COMBINE-lab/libgff"
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
        # R26: 静态库，禁用共享构建
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        # 上游 CMake 目标名 gff → 产物 libgff.a
        self.cpp_info.libs = ["gff"]
        self.cpp_info.set_property("cmake_file_name", "libgff")
        self.cpp_info.set_property("cmake_target_name", "libgff::libgff")
