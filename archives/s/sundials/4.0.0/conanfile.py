#!/usr/bin/env python3
"""Conan recipe for Sundials 4.0.0 — CMake projects.

SUNDIALS (Suite of Nonlinear and DIfferential/ALgebraic equation Solvers)
Static libraries build for OpenHarmony (aarch64).

This recipe enforces R26: BUILD_SHARED_LIBS=OFF for DevBox deployment.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SundialsConan(ConanFile):
    name = "sundials"
    version = "4.0.0"
    description = "SUNDIALS (Suite of Nonlinear and DIfferential/ALgebraic equation Solvers) - nonlinear and differential/algebraic equation solver suite"
    license = "BSD-3-Clause"
    homepage = "https://computing.llnl.gov/projects/sundials"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Sundials 4.0.0 has no external dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Static linking for DevBox deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "ON"
        # CMake 4.x compatibility
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Sundials module selection
        tc.variables["BUILD_CVODE"] = "ON"
        tc.variables["BUILD_CVODES"] = "ON"
        tc.variables["BUILD_IDA"] = "ON"
        tc.variables["BUILD_IDAS"] = "ON"
        tc.variables["BUILD_ARKODE"] = "ON"
        tc.variables["BUILD_KINSOL"] = "ON"
        # Examples
        tc.variables["EXAMPLES_ENABLE"] = "ON"
        tc.variables["EXAMPLES_INSTALL"] = "ON"
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
        # Sundials produces 19 static libraries
        self.cpp_info.libs = [
            "sundials_arkode",
            "sundials_cvode",
            "sundials_cvodes",
            "sundials_ida",
            "sundials_idas",
            "sundials_kinsol",
            "sundials_nvecserial",
            "sundials_sunlinsolband",
            "sundials_sunlinsoldense",
            "sundials_sunlinsolpcg",
            "sundials_sunlinsolspbcgs",
            "sundials_sunlinsolspfgmr",
            "sundials_sunlinsolspgmr",
            "sundials_sunlinsolsptfqmr",
            "sundials_sunmatrixband",
            "sundials_sunmatrixdense",
            "sundials_sunmatrixsparse",
            "sundials_sunnonlinsolfixedpoint",
            "sundials_sunnonlinsolnewton",
        ]
