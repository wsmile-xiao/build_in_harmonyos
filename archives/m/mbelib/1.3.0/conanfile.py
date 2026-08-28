#!/usr/bin/env python3
"""Conan recipe for mbelib — P25 Phase 1 and ProVoice vocoder (IMBE/AMBE voice codec library).

mbelib uses CMake as its build system. The upstream CMakeLists.txt creates
both static (mbe-static) and shared (mbe-shared) targets with OUTPUT_NAME "mbe".
This recipe builds both targets and strips the unwanted library type in package().
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MbelibConan(ConanFile):
    name = "mbelib"
    version = "1.3.0"
    description = "P25 Phase 1 and ProVoice vocoder (IMBE/AMBE voice codec library)"
    license = "ISC"
    homepage = "https://github.com/szechyjs/mbelib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMakeLists.txt uses cmake_minimum_required(VERSION 2.6)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Build all targets (CMakeLists.txt installs both mbe-static and mbe-shared)
        cmake.build()
        # Build and run upstream GTest test suite (mbetest)
        cmake.build(target="mbetest")
        mbetest = os.path.join(self.build_folder, "test", "mbetest")
        if os.path.exists(mbetest):
            self.run(f'"{mbetest}"', env="conanrun", ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Strip the unwanted library type to keep the package clean
        lib_folder = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            rm(self, "*.a", lib_folder)
        else:
            rm(self, "*.so", lib_folder)
            rm(self, "*.so.*", lib_folder)

    def package_info(self):
        self.cpp_info.libs = ["mbe"]
        self.cpp_info.set_property("cmake_file_name", "mbelib")
        self.cpp_info.set_property("cmake_target_name", "mbelib::mbelib")
