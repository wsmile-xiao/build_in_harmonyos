#!/usr/bin/env python3
"""Conan recipe for libMeshb 7.80 (CMake)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibmeshbConan(ConanFile):
    name = "libmeshb"
    version = "7.80"
    description = "libMeshb: Meshb.7 mesh file I/O library (read/write .mesh/.meshb)"
    license = "MIT"
    homepage = "https://github.com/LoicMarechal/libMeshb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        # WITH_GMF_AIO 需要 rt 且走 Unix aio，保持上游默认 OFF；
        # WITH_GMF_CTEST 依赖 tarball 中不存在的 testing/ 目录，保持 OFF。
        tc.cache_variables["WITH_GMF_AIO"] = False
        tc.cache_variables["WITH_GMF_CTEST"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "libmeshb7.h",
            src=os.path.join(self.source_folder, "sources"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libmeshb7.ins",
            src=os.path.join(self.source_folder, "sources"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libmeshb7_helpers.h",
            src=os.path.join(self.source_folder, "utilities"),
            dst=os.path.join(self.package_folder, "include"),
        )
        built_lib = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "libMeshb.7.a" in files:
                built_lib = root
                break
        if built_lib:
            copy(self, "libMeshb.7.a", src=built_lib, dst=os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "copyright.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["Meshb.7"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
