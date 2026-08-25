#!/usr/bin/env python3
"""Conan recipe — asplib 1.0 (CMake, C++11).

asplib (Achim's Signal Processing LIBrary) is a small and lightweight C++
library for digital signal processing. This recipe builds the self-contained
modules (Core, Biquad, IIR, Dynamics, Logger, Signals, Timer, Resampling)
as static libraries. Modules requiring external dependencies (AudioInterfaces
needs PortAudio; FFT/SpectrumVisProcessor/Convolution need KissFFT) and the
x86-only ComputeDeviceInfo module are excluded on OHOS.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, rm
import os


class AsplibConan(ConanFile):
    name = "asplib"
    version = "1.0"
    description = "Achim's Signal Processing LIBrary — C/C++ library for digital signal processing"
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
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x dropped compatibility with cmake_minimum_required < 3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # R32: treat OHOS as Linux-like
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
        # Remove cmake config files and pkgconfig (not needed for consumers)
        rm(self, "*.cmake", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pc", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # asplib builds each module as a separate static library
        self.cpp_info.libs = [
            "asplib_Biquad",
            "asplib_Core",
            "asplib_Dynamics",
            "asplib_IIR",
            "asplib_Logger",
            "asplib_Resampling",
            "asplib_Signals",
            "asplib_Timer",
        ]
        self.cpp_info.includedirs = ["include", "include/asplib"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "asplib")
        self.cpp_info.set_property("cmake_target_name", "asplib::asplib")
