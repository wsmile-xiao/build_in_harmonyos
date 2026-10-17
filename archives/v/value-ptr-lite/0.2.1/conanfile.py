#!/usr/bin/env python3
"""Conan recipe — value-ptr-lite 0.2.1 (header-only, CMake).

value-ptr-lite is a single-file header-only C++ library (C++98 and later).
Build is CMake; package is header-only (no compiled artifacts).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ValueptrliteConan(ConanFile):
    name = "value-ptr-lite"
    version = "0.2.1"
    description = "A C++ smart-pointer with value semantics for C++98 and later (header-only)"
    license = "BSL-1.0"
    homepage = "https://github.com/nonstd-lite/value-ptr-lite"
    url = ""  # CI fills this

    package_type = "header-library"

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
        # R26: system-name libraries default to static; header-only -> no shared build
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Do not build upstream tests/examples inside the package
        tc.variables["VALUE_PTR_LITE_OPT_BUILD_TESTS"] = "OFF"
        tc.variables["VALUE_PTR_LITE_OPT_BUILD_EXAMPLES"] = "OFF"
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
        # header-only: no libs, only include dir (CMake config installs value-ptr-lite-config.cmake)
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # 上游 CMake installs nonstd::value-ptr-lite target via its own config;
        # CMakeDeps 默认生成 value-ptr-lite::value-ptr-lite 供消费者引用。
        self.cpp_info.set_property("cmake_file_name", "value-ptr-lite")
        self.cpp_info.set_property("cmake_target_name", "value-ptr-lite::value-ptr-lite")
