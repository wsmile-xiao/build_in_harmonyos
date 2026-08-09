#!/usr/bin/env python3
"""Conan recipe for MFEM 4.9 on HarmonyOS aarch64."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MfemConan(ConanFile):
    name = "mfem"
    version = "4.9"
    description = "Finite Element Method Library — lightweight, scalable C++ library for finite element methods."
    license = "BSD-3-Clause"
    homepage = "https://mfem.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Serial build: zero external dependencies

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["MFEM_USE_MPI"] = "NO"
        tc.variables["MFEM_USE_LAPACK"] = "NO"
        tc.variables["MFEM_USE_OPENMP"] = "NO"
        tc.variables["MFEM_USE_CUDA"] = "NO"
        tc.variables["MFEM_USE_HIP"] = "NO"
        tc.variables["MFEM_USE_METIS"] = "NO"
        tc.variables["MFEM_ENABLE_TESTING"] = "ON"
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.build(target="tests")
        cmake.build(target="examples")
        cmake.build(target="miniapps")
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mfem"]
        self.cpp_info.set_property("cmake_file_name", "MFEM")
        self.cpp_info.set_property("cmake_target_name", "mfem")
