#!/usr/bin/env python3
"""Conan recipe - srtp 2.8.0 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class SrtpConan(ConanFile):
    name = "srtp"
    version = "2.8.0"
    description = "Implementation of the Secure Real-time Transport Protocol"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cisco/libsrtp"
    url = "https://github.com/cisco/libsrtp"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["LIBSRTP_TEST_APPS"] = True
        toolchain.variables["ENABLE_WARNINGS_AS_ERRORS"] = False
        toolchain.variables["ENABLE_OPENSSL"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["srtp2"]
        self.cpp_info.set_property("cmake_file_name", "libSRTP")
        self.cpp_info.set_property("cmake_target_name", "libSRTP::srtp2")
