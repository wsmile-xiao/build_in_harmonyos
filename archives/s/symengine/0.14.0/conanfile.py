#!/usr/bin/env python3
"""Conan recipe for SymEngine 0.14.0."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SymengineConan(ConanFile):
    name = "symengine"
    version = "0.14.0"
    description = "Fast symbolic manipulation library written in C++"
    license = "MIT"
    homepage = "https://github.com/symengine/symengine"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("SymEngine supports Linux and OHOS")

    def requirements(self):
        self.requires("gmp/6.3.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _gmp_library(folder):
        for pattern in ("libgmp.a", "libgmp.so", "libgmp.so.*"):
            matches = glob.glob(os.path.join(folder, "lib", pattern))
            if matches:
                return matches[0]
        return os.path.join(folder, "lib", "libgmp.a")

    def generate(self):
        gmp = self.dependencies["gmp"].package_folder
        tc = CMakeToolchain(self)
        tc.cache_variables["GMP_INCLUDE_DIR"] = os.path.join(gmp, "include")
        tc.cache_variables["GMP_LIBRARY"] = self._gmp_library(gmp)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["INTEGER_CLASS"] = "gmp"
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_BENCHMARKS_GOOGLE"] = False
        tc.variables["WITH_COTIRE"] = False
        tc.variables["WITH_FLINT"] = False
        tc.variables["WITH_ARB"] = False
        tc.variables["WITH_MPFR"] = False
        tc.variables["WITH_MPC"] = False
        tc.variables["WITH_LLVM"] = False
        tc.variables["WITH_PIRANHA"] = False
        tc.variables["WITH_OPENMP"] = False
        tc.variables["WITH_SYSTEM_CEREAL"] = False
        tc.variables["WITH_SYSTEM_FASTFLOAT"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            cmake.test()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        gmp_include = os.path.join(self.dependencies["gmp"].package_folder, "include")
        self.cpp_info.libs = ["symengine"]
        self.cpp_info.includedirs = ["include", gmp_include]
        self.cpp_info.requires = ["gmp::gmp"]
        self.cpp_info.set_property("cmake_file_name", "symengine")
        self.cpp_info.set_property("cmake_target_name", "symengine::symengine")
        self.cpp_info.system_libs = ["m", "pthread"]
