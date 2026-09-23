#!/usr/bin/env python3
"""Conan recipe — sexpp 0.9.1 (CMake project, static library + CLI)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SexppConan(ConanFile):
    name = "sexpp"
    version = "0.9.1"
    description = "S-expressions parser and generator C++ library, fully compliant to Rivest's Sexp.txt"
    license = "MIT"
    homepage = "https://github.com/rnpgp/sexpp"
    url = ""  # CI fills this

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS: do not fetch googletest over the network during conan create;
        # upstream tests are exercised separately in the build worktree.
        tc.variables["DOWNLOAD_GTEST"] = "OFF"
        tc.variables["WITH_SEXP_TESTS"] = "OFF"
        tc.variables["WITH_SEXP_CLI"] = "ON"
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
        self.cpp_info.libs = ["sexpp"]
        self.cpp_info.set_property("cmake_file_name", "sexpp")
        self.cpp_info.set_property("cmake_target_name", "sexpp::sexpp")
