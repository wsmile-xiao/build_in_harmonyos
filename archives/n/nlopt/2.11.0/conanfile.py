#!/usr/bin/env python3
"""Conan recipe — nlopt 2.11.0 (CMake).

NLopt is a nonlinear-optimization library with C and C++ APIs.
This recipe keeps the C/C++ core (NLOPT_CXX=ON) and disables optional
language bindings (Python/Octave/Matlab/Guile/SWIG) which have no
OHOS toolchain support.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NloptConan(ConanFile):
    name = "nlopt"
    version = "2.11.0"
    description = "Library for nonlinear optimization"
    license = "MIT/LGPL"
    homepage = "https://github.com/stevengj/nlopt"
    url = "https://github.com/stevengj/nlopt"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # NLopt is a self-contained math library with no external
        # runtime dependencies (all optional bindings disabled above).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build shared or static per package option
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # NLopt: keep C API + C++ API, disable optional language bindings
        # (Python/Octave/Matlab/Guile/SWIG have no OHOS toolchain support).
        tc.variables["NLOPT_CXX"] = "ON"
        tc.variables["NLOPT_PYTHON"] = "OFF"
        tc.variables["NLOPT_OCTAVE"] = "OFF"
        tc.variables["NLOPT_MATLAB"] = "OFF"
        tc.variables["NLOPT_GUILE"] = "OFF"
        tc.variables["NLOPT_SWIG"] = "OFF"
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
        self.cpp_info.libs = ["nlopt"]
