#!/usr/bin/env python3
"""Conan recipe — lfqueue 1.2.2 (lock-free FIFO queue, C, CMake-based).

Taymindis/lfqueue: cross-platform lock-free FIFO queue built with native C
and GCC/Clang __sync CAS builtins. No external dependencies.

Build: upstream CMakeLists builds liblfqueue.a/.so + lfqueue-example test
binary. A minimal patch makes the library target respect BUILD_SHARED_LIBS
and removes the install-time `ldconfig` call (absent on OHOS).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LfqueueConan(ConanFile):
    name = "lfqueue"
    version = "1.2.2"
    description = "Lock-free FIFO queue by C native built it, easy built cross platform (no extra dependencies needed), guarantee thread safety memory management"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Taymindis/lfqueue"
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
        # R26: default static; BUILD_SHARED_LIBS drives the (patched) CMake target.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream declares cmake_minimum_required(2.8); allow modern CMake policy range.
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
        self.cpp_info.libs = ["lfqueue"]
        self.cpp_info.set_property("cmake_file_name", "lfqueue")
        self.cpp_info.set_property("cmake_target_name", "lfqueue::lfqueue")