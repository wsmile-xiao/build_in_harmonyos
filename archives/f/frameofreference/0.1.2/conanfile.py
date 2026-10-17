#!/usr/bin/env python3
"""Conan recipe for FrameOfReference 0.1.2 — C++ integer packing library.

Upstream build: CMake (add_library STATIC + unit test).  Upstream CMakeLists.txt
has NO install() rules, so package() manually installs the headers and the
static library produced by the build.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.build import cross_building
import os


class FrameofreferenceConan(ConanFile):
    name = "frameofreference"
    version = "0.1.2"
    description = "C++ library to pack and unpack vectors of integers having a small range of values (Frame of Reference)"
    license = "Apache-2.0"
    homepage = "https://github.com/fast-pack/FrameOfReference"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream declares cmake_minimum_required(VERSION 2.8.7); CMake >= 4.0
        # requires an explicit policy version to accept such old minimums.
        # Passed as -D on the configure command line so it is honored before
        # the project() call (toolchain-file variables are too late here).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        for build_dir in (self.build_folder, os.path.join(self.build_folder, "Release"),
                          os.path.join(self.build_folder, "build")):
            lib = os.path.join(build_dir, "libFrameOfReference.a")
            if os.path.exists(lib):
                copy(self, "libFrameOfReference.a", src=build_dir,
                     dst=os.path.join(self.package_folder, "lib"))
                break

    def package_info(self):
        self.cpp_info.libs = ["FrameOfReference"]
        self.cpp_info.set_property("cmake_file_name", "frameofreference")
        self.cpp_info.set_property("cmake_target_name", "frameofreference::frameofreference")
