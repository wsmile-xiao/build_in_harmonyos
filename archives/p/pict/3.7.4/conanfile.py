#!/usr/bin/env python3
"""Conan recipe for PICT 3.7.4 -- Microsoft Pairwise Independent Combinatorial Testing CLI."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class PictConan(ConanFile):
    name = "pict"
    version = "3.7.4"
    description = "Microsoft PICT -- Pairwise Independent Combinatorial Testing tool (command line)"
    license = "MIT"
    homepage = "https://github.com/microsoft/pict"
    url = "https://github.com/microsoft/pict"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"PICT only supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compilers.get("ar"):
            tc.variables["CMAKE_AR"] = compilers["ar"]
        if compilers.get("ranlib"):
            tc.variables["CMAKE_RANLIB"] = compilers["ranlib"]

        if str(self.settings.os) in ("OHOS", "Linux") and \
                str(self.settings.compiler.libcxx) == "libc++":
            # OHOS clang has no default C++ header search path; must pass
            # -stdlib=libc++ explicitly (see E130; alacenc precedent).  The
            # target sysroot provides libc++.so, so link against it explicitly
            # instead of relying on a compiler default (libc++_shared).
            tc.variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-lc++ -lpthread"
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-lc++ -lpthread"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE.TXT", self.source_folder, license_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
