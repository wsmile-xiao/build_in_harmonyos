#!/usr/bin/env python3
"""Conan recipe — asplib 20160310.da66f51 (CMake, C++).

asplib (Achim's Signal Processing LIBrary) is a small and lightweight C++
library for digital signal processing. This version (upstream commit da66f51,
2016-03-10) builds a single static library `asplib` implementing Biquad
filters (Native path, no x86 SSE/AVX requirement) plus supporting util
headers (logger / os abstraction / typedefs). No external dependencies.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, rm
import os


class AsplibConan(ConanFile):
    name = "asplib"
    version = "20160310.da66f51"
    description = "Achim's Signal Processing LIBrary — small and lightweight C/C++ library for digital signal processing"
    license = "GPL-3.0"
    homepage = "https://github.com/AchimTuran/asplib"
    url = "https://github.com/AchimTuran/asplib"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # asplib has no external runtime/library dependencies (only libc/libm)
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x dropped compatibility with cmake_minimum_required < 3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # asplib add_library() has no explicit SHARED/STATIC keyword -> BUILD_SHARED_LIBS decides
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # R32: treat OHOS as Linux-like (CMAKE_SYSTEM_NAME=HarmonyOS on OHOS)
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"asplib is only supported on Linux/OHOS, not {self.settings.os}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy license
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Remove cmake config / pkgconfig files: they embed the configure-time
        # prefix and are not needed by Conan consumers.
        rm(self, "asplib-config.cmake", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.pc", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["asplib"]
        # Headers are installed under include/asplib/ (with Biquads/, interfaces/,
        # asplib_utils/ subdirs); expose both roots so consumers can use either
        # #include <Biquads/...> or #include <asplib/Biquads/...>
        self.cpp_info.includedirs = ["include", "include/asplib"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "asplib")
        self.cpp_info.set_property("cmake_target_name", "asplib::asplib")
