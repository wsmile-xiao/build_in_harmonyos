#!/usr/bin/env python3
"""Conan recipe for iniparser 4.2.6.

iniparser is a standalone C library offering both shared and static
builds via CMake. Upstream: https://github.com/ndevilla/iniparser
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class IniparserConan(ConanFile):
    name = "iniparser"
    version = "4.2.6"
    description = "A free stand-alone ini file parsing library written in C"
    license = "MIT"
    homepage = "https://github.com/ndevilla/iniparser"
    url = "https://github.com/ndevilla/iniparser"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # iniparser has zero external dependencies — pure C standard library
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build both shared and static simultaneously is NOT supported by
        # the conan options model; static-only is the default here.
        tc.variables["BUILD_TESTING"] = "OFF"  # tests need ruby + Unity (FetchContent)
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_DOCS"] = "OFF"     # docs need doxygen
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
        # Upstream installs headers to include/iniparser/ — consumers use
        # #include <iniparser/iniparser.h>. Expose the subdirectory so both
        # plain "iniparser.h" and "iniparser/iniparser.h" resolve.
        self.cpp_info.includedirs = ["include", "include/iniparser"]
        self.cpp_info.libs = ["iniparser"]
        self.cpp_info.set_property("cmake_file_name", "iniparser")
        self.cpp_info.set_property("cmake_target_name", "iniparser::iniparser")
        self.cpp_info.set_property("pkg_config_name", "iniparser")
