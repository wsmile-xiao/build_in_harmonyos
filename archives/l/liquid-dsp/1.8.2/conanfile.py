#!/usr/bin/env python3
"""Conan recipe for liquid-dsp 1.8.2 (upstream v1.8.2).

Build system: CMake (upstream v1.8.0 migrated to CMake; autotools kept but deprecated).
FFTW (fftw3f) is an optional acceleration; we disable FIND_FFTW and use the
built-in FFT implementation, so there are no external dependencies.
This package revision deliberately supports the validated static variant only.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LiquidDspConan(ConanFile):
    name = "liquid-dsp"
    version = "1.8.2"
    description = "Software-defined radio digital signal processing library"
    license = "MIT"
    homepage = "https://liquidsdr.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = os.environ.get("LIQUID_DSP_SOURCE_ARCHIVE")
        if local_archive:
            archive_path = Path(local_archive).resolve()
            if not archive_path.is_file():
                raise ConanException(f"LIQUID_DSP_SOURCE_ARCHIVE is not a file: {archive_path}")
            source["url"] = archive_path.as_uri()
            source["filename"] = archive_path.name
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.variables["BUILD_STATIC_LIBS"] = True
        toolchain.variables["BUILD_EXAMPLES"] = False
        toolchain.variables["BUILD_AUTOTESTS"] = True
        toolchain.variables["BUILD_BENCHMARKS"] = False
        toolchain.variables["BUILD_SANDBOX"] = False
        toolchain.variables["BUILD_DOC"] = False
        toolchain.variables["FIND_FFTW"] = False
        toolchain.variables["FIND_SIMD"] = False
        toolchain.variables["ENABLE_SIMD"] = False
        toolchain.variables["ENABLE_LOGGING"] = True
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

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
