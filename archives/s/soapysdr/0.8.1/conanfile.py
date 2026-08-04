#!/usr/bin/env python3
"""Conan recipe for SoapySDR 0.8.1 — CMake build system.

SoapySDR is a vendor-neutral SDR (Software Defined Radio) hardware abstraction layer
and driver API library. It provides a unified C/C++ API for controlling SDR devices.
Build: CMake with C++11 standard.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class SoapySDRConan(ConanFile):
    name = "soapysdr"
    version = "0.8.1"
    description = "Vendor-neutral SDR hardware abstraction layer and driver API library."
    license = "BSL-1.0"
    homepage = "https://github.com/pothosware/SoapySDR"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable optional components not needed on OHOS
        tc.variables["ENABLE_PYTHON"] = False
        tc.variables["ENABLE_PYTHON3"] = False
        tc.variables["ENABLE_DOCS"] = False
        # Build the upstream tests; build() executes them with CTest.
        tc.variables["ENABLE_TESTS"] = True
        tc.variables["ENABLE_APPS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # This must be a command-line cache variable: the toolchain loads after
        # upstream's cmake_minimum_required(VERSION 2.8) has already run.
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "UNIX": True,
        })
        cmake.build()
        # Run upstream unit tests
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["SoapySDR"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "SoapySDR")
        self.cpp_info.set_property("cmake_target_name", "SoapySDR::SoapySDR")
        # pkg-config file is installed to lib/pkgconfig
        self.cpp_info.set_property("pkg_config_name", "SoapySDR")
