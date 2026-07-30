#!/usr/bin/env python3
"""Conan recipe for HdrHistogram_c 0.11.9."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HdrhistogramConan(ConanFile):
    name = "hdrhistogram"
    version = "0.11.9"
    description = "High Dynamic Range Histogram C implementation for latency and performance measurement"
    license = "CC0-1.0 / BSD-2-Clause"
    homepage = "https://github.com/HdrHistogram/HdrHistogram_c"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

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
        tc.variables["HDR_LOG_REQUIRED"] = "OFF"
        tc.variables["HDR_HISTOGRAM_BUILD_PROGRAMS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hdr_histogram"]
        system_libs = ["pthread", "m"]
        if self.settings.os not in ("OHOS",):
            system_libs.append("rt")
        self.cpp_info.system_libs = system_libs
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "hdr_histogram")
        self.cpp_info.set_property("cmake_target_name", "hdr_histogram::hdr_histogram")
        self.cpp_info.set_property("pkg_config_name", "hdr_histogram")
