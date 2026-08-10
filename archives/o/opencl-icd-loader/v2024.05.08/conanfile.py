#!/usr/bin/env python3
"""Conan recipe — opencl-icd-loader v2024.05.08 (CMake)

Khronos OpenCL ICD Loader - Installable Client Driver Loader for OpenCL.
Builds libOpenCL.so, the standard OpenCL ICD loader library.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class OpenclIcdLoaderConan(ConanFile):
    name = "opencl-icd-loader"
    version = "v2024.05.08"
    description = "Khronos OpenCL ICD Loader - Installable Client Driver Loader for OpenCL"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/OpenCL-ICD-Loader"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("opencl-headers/2026.05.29")

    def configure(self):
        # R32: platform check must use "in" with OHOS
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                f"opencl-icd-loader only supports Linux/OHOS/FreeBSD/Macos/Windows, got: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Map shared option to BUILD_SHARED_LIBS
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Disable layers (optional feature, not needed for core ICD loader)
        tc.variables["ENABLE_OPENCL_LAYERS"] = "OFF"
        # Set OpenCL headers directory from the opencl-headers dependency
        headers_dir = os.path.join(self.dependencies["opencl-headers"].package_folder, "include")
        tc.variables["OPENCL_ICD_LOADER_HEADERS_DIR"] = headers_dir
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenCL")
        self.cpp_info.set_property("cmake_target_name", "OpenCL::OpenCL")
        self.cpp_info.libs = ["OpenCL"]
        # No headers installed in this package; headers come from opencl-headers
        self.cpp_info.includedirs = []
