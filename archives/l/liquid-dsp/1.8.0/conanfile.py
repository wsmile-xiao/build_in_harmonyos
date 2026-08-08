#!/usr/bin/env python3
"""Conan recipe — liquid-dsp 1.8.0 (software-defined radio DSP library).

Build system: CMake (upstream v1.8.0 migrated to CMake; autotools kept but deprecated).
FFTW (fftw3f) is an optional acceleration; we disable FIND_FFTW and use the
built-in FFT implementation, so there are no external dependencies.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, collect_libs, export_conandata_patches, get


class LiquidDspConan(ConanFile):
    name = "liquid-dsp"
    version = "1.8.0"
    description = "Software-defined radio digital signal processing library"
    license = "MIT"
    homepage = "https://liquidsdr.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        toolchain.variables["BUILD_EXAMPLES"] = False
        toolchain.variables["BUILD_AUTOTESTS"] = False
        toolchain.variables["BUILD_BENCHMARKS"] = False
        toolchain.variables["BUILD_SANDBOX"] = False
        toolchain.variables["BUILD_DOC"] = False
        toolchain.variables["FIND_FFTW"] = False
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["liquid"]
        self.cpp_info.set_property("cmake_file_name", "liquid")
        self.cpp_info.set_property("cmake_target_name", "liquid::liquid-static")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
