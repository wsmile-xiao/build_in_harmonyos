#!/usr/bin/env python3
"""Conan recipe — mts-esp 0.0-git20230110.9df9a9c (CMake)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MtsEspConan(ConanFile):
    name = "mts-esp"
    version = "0.0-git20230110.9df9a9c"
    description = "C++ client and master wrappers for MTS-ESP microtuning"
    license = "ISC"
    homepage = "https://github.com/ODDSound/MTS-ESP"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mts-esp supports Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["MTS"]
        self.cpp_info.system_libs = ["dl"]
        self.cpp_info.set_property("cmake_file_name", "mts-esp")
        self.cpp_info.set_property("cmake_target_name", "mts-esp::mts-esp")
