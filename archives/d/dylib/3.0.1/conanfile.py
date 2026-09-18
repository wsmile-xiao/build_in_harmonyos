#!/usr/bin/env python3
"""Conan recipe for dylib 3.0.1 (CMake, MIT).

dylib: C++11 dynamic library loader covering .so/.dll/.dylib.
Adapted for HarmonyOS PC (aarch64-linux-ohos): see patches/ for the
symbols.cpp dl_iterate_phdr fallback and format.cpp std::__n1 normalization.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class DylibConan(ConanFile):
    name = "dylib"
    version = "3.0.1"
    description = "C++11 library to load dynamic libraries at runtime"
    license = "MIT"
    homepage = "https://github.com/martin-olivier/dylib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["DYLIB_BUILD_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["dylib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]