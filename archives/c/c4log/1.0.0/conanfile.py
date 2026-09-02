#!/usr/bin/env python3
"""Conan recipe — c4log 1.0.0 (CMake)"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class C4logConan(ConanFile):
    name = "c4log"
    version = "1.0.0"
    description = "C++ type-safe logging, mean and lean"
    license = "MIT"
    homepage = "https://github.com/biojppm/c4log"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("logging", "c4core")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            url="https://github.com/biojppm/c4core/archive/7f3863e15ffcb2eef386d899c9c63b4db9418979.tar.gz",
            sha256="f975df6b80e810283b8186322b8266d03a3b25686a448f2541596f15ade2917f",
            strip_root=True,
            destination=os.path.join(self.source_folder, "ext/c4core"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["c4log", "c4core"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "c4log")
        self.cpp_info.set_property("cmake_target_name", "c4log::c4log")
