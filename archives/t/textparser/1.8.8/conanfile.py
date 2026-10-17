#!/usr/bin/env python3
"""Conan recipe — textparser 1.8.8 (CMake)"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
import os


class TextparserConan(ConanFile):
    name = "textparser"
    version = "1.8.8"
    description = "Text Parser library for YAML-like simple parameter structure"
    license = "BSD-2-Clause"
    homepage = "https://github.com/avr-aics-riken/TextParser"
    url = ""
    
    package_type = "library"
    
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_mpi": [True, False],
        "enable_fapi": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_mpi": False,
        "enable_fapi": False,
    }
    
    def export_sources(self):
        export_conandata_patches(self)
    
    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Disable C++ standard if not needed
        if not self.options.enable_fapi:
            self.settings.rm_safe("compiler.cppstd")
        # Fix libcxx for OHOS/clang
        if self.settings.os == "OHOS" and self.settings.compiler == "clang":
            self.settings.compiler.libcxx = "c++_shared"
    
    def layout(self):
        cmake_layout(self, src_folder="src")
    
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
    
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["enable_fapi"] = self.options.enable_fapi
        tc.variables["enable_test"] = False
        tc.variables["with_MPI"] = self.options.with_mpi
        tc.generate()
    
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "License.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "share"))
    
    def package_info(self):
        self.cpp_info.libs = ["TP"]
        self.cpp_info.set_property("pkg_config_name", "textparser")
        if self.options.with_mpi:
            self.cpp_info.defines.append("ENABLE_MPI")
