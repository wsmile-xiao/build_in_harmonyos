#!/usr/bin/env python3
"""Conan recipe for libMeshb 8.02 (CMake)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibmeshbConan(ConanFile):
    name = "libmeshb"
    version = "8.02"
    description = "libMeshb: Meshb.8 mesh file I/O library (read/write .mesh/.meshb)"
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
        # WITH_GMF_CTEST=ON：v8.02 release tarball 携带 testing/ 目录（7.80 没有），
        # 可注册上游 ctest 测试而不影响 conan create（add_subdirectory(testing) 仅 add_test）。
        tc.cache_variables["WITH_GMF_AIO"] = False
        tc.cache_variables["WITH_GMF_CTEST"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "libmeshb8.h",
            src=os.path.join(self.source_folder, "sources"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libmeshb8.ins",
            src=os.path.join(self.source_folder, "sources"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libmeshb8_helpers.h",
            src=os.path.join(self.source_folder, "utilities"),
            dst=os.path.join(self.package_folder, "include"),
        )
        built_lib = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "libMeshb.8.a" in files:
                built_lib = root
                break
        if built_lib:
            copy(self, "libMeshb.8.a", src=built_lib, dst=os.path.join(self.package_folder, "lib"))
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
        self.cpp_info.libs = ["Meshb.8"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]