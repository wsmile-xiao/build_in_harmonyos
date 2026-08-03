#!/usr/bin/env python3
"""Conan recipe for LightGBM 4.6.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LightGBMConan(ConanFile):
    name = "lightgbm"
    version = "4.6.0"
    description = "A fast, distributed, high performance gradient boosting framework"
    license = "MIT"
    homepage = "https://github.com/microsoft/LightGBM"
    url = "https://github.com/microsoft/LightGBM"
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
        for destination, metadata in self.conan_data.get("submodules", {}).items():
            get(
                self,
                url=metadata["url"],
                sha256=metadata["sha256"],
                destination=destination,
                strip_root=True,
                filename=metadata["filename"],
            )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["USE_OPENMP"] = "OFF"
        tc.variables["USE_MPI"] = "OFF"
        tc.variables["USE_GPU"] = "OFF"
        tc.variables["BUILD_CLI"] = "ON"
        tc.variables["BUILD_CPP_TEST"] = "ON"
        tc.variables["BUILD_STATIC_LIB"] = "ON"
        fpic = self.options.get_safe("fPIC")
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True if fpic is None else bool(fpic)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run(f'ctest --test-dir "{self.build_folder}" --output-on-failure', env=["conanbuild"])

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lightgbm"]
        self.cpp_info.bindirs = ["bin"]
