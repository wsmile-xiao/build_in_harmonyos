#!/usr/bin/env python3
"""Conan recipe — zstd-jni 1.5.6-5 (CMake)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZstdJniConan(ConanFile):
    name = "zstd-jni"
    version = "1.5.6-5"
    description = "JNI wrapper around zstd providing Java access to Zstandard compression"
    license = "BSD-2-Clause"
    homepage = "https://github.com/luben/zstd-jni"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fallback for systems with limited patch tool: ensure JNI include path
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        'include_directories("src/main/native"',
                        'include_directories("jni" "src/main/native"',
                        strict=False)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # CMakeLists.txt has no install target; copy built artifacts manually
        copy(self, "libzstd-jni-1.5.6-5.so",
             src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        # Include zstd API headers for consumers
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src", "main", "native"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["zstd-jni-1.5.6-5"]
