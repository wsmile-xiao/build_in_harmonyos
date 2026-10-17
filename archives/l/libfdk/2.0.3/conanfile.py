#!/usr/bin/env python3
"""Conan recipe — libfdk 2.0.3 (CMake)"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches


class LibfdkConan(ConanFile):
    name = "libfdk"
    version = "2.0.3"
    description = "Fraunhofer FDK AAC codec library (standalone)"
    license = "FDK-AAC"
    homepage = "https://github.com/mstorsjo/fdk-aac"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libfdk requires a POSIX-like target (Linux or OHOS), not %s" % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_PROGRAMS"] = "OFF"
        tc.variables["FDK_AAC_INSTALL_CMAKE_CONFIG_MODULE"] = "ON"
        tc.variables["FDK_AAC_INSTALL_PKGCONFIG_MODULE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "NOTICE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["fdk-aac"]
        self.cpp_info.set_property("cmake_file_name", "fdk-aac")
        self.cpp_info.set_property("cmake_target_name", "FDK-AAC::fdk-aac")
        self.cpp_info.set_property("pkg_config_name", "fdk-aac")
        self.cpp_info.includedirs = ["include", "include/fdk-aac"]
