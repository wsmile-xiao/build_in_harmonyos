#!/usr/bin/env python3
"""Conan recipe for cpp-dump 0.7.0 (C++17 header-only debugging/dump library)."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CppDumpConan(ConanFile):
    name = "cpp-dump"
    version = "0.7.0"
    package_type = "header-library"

    description = "An all-round dump function library for C++ that can print any type, even user-defined types."
    license = "MIT"
    homepage = "https://github.com/philip82148/cpp-dump"
    url = "https://github.com/philip82148/cpp-dump"
    topics = ("debug", "dump", "header-only", "cpp17")

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # Upstream requires C++17 (README + CI matrix std=17/20).
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The upstream log-label fixture records __FILE__ captured from a checkout
        # directory named exactly "cpp-dump" (its GitHub Actions workspace layout):
        # the fixed_length(0, 40, 0) label keeps the last 34 chars of the path, so
        # only that exact directory suffix reproduces the expected output. Build
        # from a copy of the sources under <build_folder>/cpp-dump instead of the
        # Conan cache source folder, whose name would break the fixture.
        src = os.path.join(self.build_folder, "cpp-dump")
        if os.path.isdir(src):
            shutil.rmtree(src)
        shutil.copytree(self.source_folder, src)

        cmake = CMake(self)
        cmake.configure(build_script_folder=src)
        cmake.build()
        # Upstream official tests: 27 registered CTest cases run in the build phase.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        # Header-only package: independent of os/arch/compiler/build_type.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "cpp-dump")
        self.cpp_info.set_property("cmake_target_name", "cpp-dump::cpp-dump")
