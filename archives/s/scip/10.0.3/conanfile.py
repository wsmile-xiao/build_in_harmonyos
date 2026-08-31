#!/usr/bin/env python3
"""Conan recipe for scip 10.0.3 — Solving Constraint Integer Programs.

SCIP is a mixed-integer programming solver and constraint programming framework.
This recipe uses the scipoptsuite tarball which bundles SoPlex (LP solver),
providing full LP/MIP solving capability (no trimming — LPS=spx, not LPS=none).

Build system: CMake (scipoptsuite top-level CMakeLists.txt)
Library output: libscip.a, libsoplex.a (static by default)
Binary output: bin/scip (command-line solver)
Dependencies: zlib/1.3.1 (from conan registry)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ScipConan(ConanFile):
    name = "scip"
    version = "10.0.3"
    description = "SCIP - Solving Constraint Integer Programs, a mixed-integer programming solver"
    license = "Apache-2.0"
    homepage = "https://scipopt.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
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
        # Build options: full functionality, no trimming
        tc.variables["AUTOBUILD"] = "ON"          # Auto-detect SoPlex in sibling dir
        tc.variables["SHARED"] = "OFF"             # Static library
        tc.variables["ZIMPL"] = "OFF"             # No ZIMPL parser
        tc.variables["PAPILO"] = "OFF"            # Disable Papilo (not needed)
        tc.variables["AMPL"] = "OFF"              # No AMPL interface
        tc.variables["IPOPT"] = "OFF"             # No Ipopt
        tc.variables["READLINE"] = "OFF"          # No readline
        tc.variables["THREADSAFE"] = "ON"         # Thread-safe (uses TinyCThread)
        tc.variables["TPI"] = "tny"               # Use TinyCThread for threading
        tc.variables["EXPRINT"] = "none"          # No expression handler
        tc.variables["SYM"] = "none"             # No symmetry handling
        tc.variables["BUILD_TESTING"] = "OFF"     # Skip upstream tests
        tc.variables["ZLIB"] = "ON"               # Enable ZLIB support
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
        self.cpp_info.set_property("cmake_file_name", "scip")
        self.cpp_info.set_property("cmake_target_name", "scip::scip")
        self.cpp_info.set_property("pkg_config_name", "scip")
        # SCIP and SoPlex are both built from scipoptsuite
        self.cpp_info.libs = ["scip", "soplex"]
        # SCIP also installs the binary
        self.cpp_info.bindirs = ["bin"]
