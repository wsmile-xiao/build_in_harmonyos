#!/usr/bin/env python3
"""Conan recipe — mmap_allocator 3.1 (CMake project, upstream master).

mmap_allocator is a STL allocator that mmaps files (CMake-based build).
The upstream CMakeLists declares `cmake_minimum_required(VERSION 3.1)`,
which is rejected by CMake >= 4 without an explicit policy minimum;
we set CMAKE_POLICY_VERSION_MINIMUM to keep the upstream project usable.

R32 note: settings.os is consumed by the OHOS-adapted conan toolchain
(os=OHOS maps to CMAKE_SYSTEM_NAME=HarmonyOS via CMakeToolchain); no
manual os branch is needed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file


class MmapAllocatorConan(ConanFile):
    name = "mmap_allocator"
    version = "3.1"
    description = "A STL allocator that mmaps files"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/ekg/mmap_allocator"
    url = "https://github.com/ekg/mmap_allocator"  # CI fills this

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
        # Upstream declares cmake_minimum_required(VERSION 3.1); CMake >= 4
        # refuses to configure such projects without an explicit policy minimum.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # CMake >= 4 removed compatibility with cmake_minimum_required < 3.5;
        # the upstream project declares 3.1, so bump it in the source tree.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 3.1)",
            "cmake_minimum_required(VERSION 3.5)",
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mmap_allocator"]
        # Upstream installs PUBLIC_HEADER into include/mmap_allocator/.
        self.cpp_info.includedirs = ["include/mmap_allocator"]
        self.cpp_info.set_property("cmake_file_name", "mmap_allocator")
        self.cpp_info.set_property("cmake_target_name", "mmap_allocator::mmap_allocator")
