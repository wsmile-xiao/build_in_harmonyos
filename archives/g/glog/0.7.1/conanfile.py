#!/usr/bin/env python3
"""Conan recipe for glog 0.7.1 — CMake-based Google logging library."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GlogConan(ConanFile):
    name = "glog"
    version = "0.7.1"
    description = "C++ implementation of the Google logging module"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/glog"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_gflags": [True, False],
        "with_symbolize": [True, False],
        "with_tls": [True, False],
    }
    default_options = {
        "shared": True,
        "with_gflags": True,
        "with_symbolize": True,
        "with_tls": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_gflags:
            self.requires("gflags/2.2.2")

    def configure(self):
        if self.options.with_gflags:
            self.options["gflags"].shared = self.options.shared

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_GFLAGS"] = "ON" if self.options.with_gflags else "OFF"
        tc.variables["WITH_GTEST"] = "OFF"
        tc.variables["WITH_UNWIND"] = "none"
        tc.variables["WITH_SYMBOLIZE"] = "ON" if self.options.with_symbolize else "OFF"
        tc.variables["WITH_TLS"] = "ON" if self.options.with_tls else "OFF"
        tc.variables["WITH_PKGCONFIG"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "glog")
        self.cpp_info.set_property("cmake_target_name", "glog::glog")
        self.cpp_info.libs = ["glog"]
        self.cpp_info.defines.append("GLOG_USE_GLOG_EXPORT")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
