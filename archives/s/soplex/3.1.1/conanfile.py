#!/usr/bin/env python3
"""Conan recipe for soplex 3.1.1 — Sequential object-oriented Simplex (LP solver).

SoPlex is an LP solver library with an interactive command-line solver.
Build system: CMake (project SOPLEX, C++11).
Library output: libsoplex.a (static), libsoplex-pic.a (static)
Binary output:  bin/soplex (command-line LP solver, R38 -> commands.json)
Dependencies: gmp/6.3.0 (exact/rational arithmetic), zlib/1.3.1 (gz I/O).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SoplexConan(ConanFile):
    name = "soplex"
    version = "3.1.1"
    description = "SoPlex - Sequential object-oriented Simplex, a linear programming (LP) solver"
    license = "LicenseRef-ZIB-Academic-License"
    homepage = "https://soplex.zib.de/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # SoPlex options: keep GMP (rational) and ZLIB (gz) support
        tc.variables["GMP"] = "ON"
        tc.variables["ZLIB"] = "ON"
        # Sanitizers only apply in Debug builds; keep them off for determinism
        tc.variables["SANITIZE_UNDEFINED"] = "OFF"
        # CMake >= 4 removed compatibility with projects declaring
        # cmake_minimum_required(VERSION < 3.5); SoPlex 3.1.1 declares 3.0.0
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.set_property("cmake_file_name", "soplex")
        self.cpp_info.set_property("cmake_target_name", "soplex::soplex")
        self.cpp_info.set_property("pkg_config_name", "soplex")
        self.cpp_info.libs = ["soplex"]
        # the CLI solver binary is installed to bin/
        self.cpp_info.bindirs = ["bin"]
