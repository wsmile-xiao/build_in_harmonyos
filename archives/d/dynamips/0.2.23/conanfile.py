#!/usr/bin/env python3
"""Conan recipe — dynamips 0.2.23 (CMake)

dynamips is a Cisco router emulation platform. On aarch64, JIT is not
available so DYNAMIPS_ARCH=nojit is used. libelf and libpcap are Conan
dependencies. The custom FindLibElf.cmake needs LIBELF_INCLUDE_DIRS
and LIBELF_LIBRARIES pre-set to find conan-installed libelf.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DynamipsConan(ConanFile):
    name = "dynamips"
    version = "0.2.23"
    description = "Cisco router emulation platform"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/GNS3/dynamips"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/d/dynamips/0.2.23"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libelf/0.8.13")
        self.requires("libpcap/1.10.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DYNAMIPS_ARCH"] = "nojit"
        tc.variables["ANY_COMPILER"] = "1"
        # Pre-set LIBELF paths for custom FindLibElf.cmake
        libelf = self.dependencies["libelf"]
        libelf_pkg = libelf.package_folder
        tc.variables["LIBELF_INCLUDE_DIRS"] = f"{libelf_pkg}/include"
        tc.variables["LIBELF_LIBRARIES"] = f"{libelf_pkg}/lib/libelf.a"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
