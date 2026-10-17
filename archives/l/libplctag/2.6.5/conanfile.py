#!/usr/bin/env python3
"""Conan recipe for libplctag 2.6.5 — CMake project.

libplctag is a C library for reading/writing PLC tags over Ethernet/IP,
Modbus, and other protocols. It builds with CMake and has no external
runtime dependencies beyond the C library and pthreads.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibplctagConan(ConanFile):
    name = "libplctag"
    version = "2.6.5"
    description = "libplctag is a portable C library for reading/writing PLC tags"
    license = "MPL-2.0"
    homepage = "https://github.com/libplctag/libplctag"
    url = "https://github.com/libplctag/libplctag"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # E092: CMake does not recognize HarmonyOS as a platform; treat it
        # as Linux so the upstream UNIX platform block is selected.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Skip building example binaries inside the package (test_package
        # exercises the installed library instead).
        tc.variables["BUILD_EXAMPLES"] = "OFF"
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
        # Upstream target names: plctag_dyn (OUTPUT_NAME=plctag -> libplctag.so)
        # and plctag_static (OUTPUT_NAME=plctag_static -> libplctag_static.a,
        # which requires LIBPLCTAG_STATIC=1 to be defined at consumer side).
        if self.options.shared:
            self.cpp_info.libs = ["plctag"]
        else:
            self.cpp_info.libs = ["plctag_static"]
            self.cpp_info.defines.append("LIBPLCTAG_STATIC=1")
