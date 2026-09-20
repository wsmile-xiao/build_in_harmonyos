#!/usr/bin/env python3
"""Conan recipe for SuperLU 7.0.1 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SuperluConan(ConanFile):
    name = "superlu"
    version = "7.0.1"
    description = "General purpose library for solving large, sparse, nonsymmetric systems of linear equations"
    license = "BSD-2-Clause"
    homepage = "https://github.com/xiaoyeli/superlu"
    url = "https://github.com/xiaoyeli/superlu"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # External BLAS (openblas) instead of the internal CBLAS:
        # better performance and avoids shipping a generic libblas.a
        # inside the package (clashes with the blas/openblas ecosystem).
        self.requires("openblas/0.3.34")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # XSDK defaults force the internal BLAS off; link the external one.
        tc.variables["enable_internal_blaslib"] = False
        tc.variables["enable_fortran"] = False
        tc.variables["XSDK_ENABLE_Fortran"] = False
        tc.variables["enable_matlabmex"] = False
        tc.variables["enable_doc"] = False
        tc.variables["enable_examples"] = False
        tc.variables["enable_tests"] = False
        # Feed the dependency's static library path to upstream's TPL mechanism.
        # Assumes openblas/0.3.34 layout (static libopenblas.a, no shared option).
        openblas = self.dependencies["openblas"]
        blas_lib = openblas.cpp_info.libdirs[0] + "/libopenblas.a"
        tc.variables["TPL_BLAS_LIBRARIES"] = blas_lib
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
        self.cpp_info.libs = ["superlu"]
        self.cpp_info.set_property("cmake_file_name", "superlu")
        self.cpp_info.set_property("cmake_target_name", "superlu::superlu")
        self.cpp_info.set_property("pkg_config_name", "superlu")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
