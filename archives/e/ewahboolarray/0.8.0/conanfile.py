#!/usr/bin/env python3
"""Conan recipe for EWAHBoolArray 0.8.0.

The upstream project is a C++11 header-only library.  Its CMake project is
still used here because it builds and runs the official unit target and
installs the upstream CMake/pkg-config metadata.
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EwahboolarrayConan(ConanFile):
    name = "ewahboolarray"
    version = "0.8.0"
    description = "A compressed bitmap class in C++"
    license = "Apache-2.0 OR MIT"
    homepage = "https://github.com/lemire/EWAHBoolArray"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

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
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        # The upstream CMake project registers one CTest target (unit).  It
        # executes the full upstream test driver, including real bitmap data.
        cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        # Preserve the target name exported by the upstream CMake project.
        self.cpp_info.set_property("cmake_file_name", "ewahboolarray")
        self.cpp_info.set_property("cmake_target_name", "ewah::ewah")
        self.cpp_info.set_property("pkg_config_name", "ewah")

    def package_id(self):
        # The package contains headers and metadata only; settings do not
        # change its contents.
        self.info.clear()
