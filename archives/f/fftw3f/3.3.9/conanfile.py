#!/usr/bin/env python3
"""Conan recipe for fftw3f 3.3.9 (single-precision FFTW)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class Fftw3fConan(ConanFile):
    name = "fftw3f"
    version = "3.3.9"
    description = "Single-precision FFTW fast Fourier transform library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.fftw.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "threads": [True, False]}
    default_options = {"shared": True, "fPIC": True, "threads": False}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["ENABLE_FLOAT"] = True
        tc.variables["ENABLE_THREADS"] = bool(self.options.threads)
        tc.variables["WITH_COMBINED_THREADS"] = bool(self.options.threads)
        tc.variables["ENABLE_OPENMP"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["DISABLE_FORTRAN"] = True
        tc.variables["ENABLE_SSE"] = False
        tc.variables["ENABLE_SSE2"] = False
        tc.variables["ENABLE_AVX"] = False
        tc.variables["ENABLE_AVX2"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fftw3f"]
        self.cpp_info.set_property("cmake_file_name", "FFTW3f")
        self.cpp_info.set_property("cmake_target_name", "FFTW3::fftw3f")
        self.cpp_info.set_property("pkg_config_name", "fftw3f")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
            if self.options.threads:
                self.cpp_info.system_libs.append("pthread")
