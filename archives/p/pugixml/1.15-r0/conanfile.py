#!/usr/bin/env python3
"""Conan recipe for pugixml 1.15-r0 — CMake-based XML processing library.

pugixml is a lightweight, simple XML processing library for C++.
This recipe uses CMake build system with static library build.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PugixmlConan(ConanFile):
    name = "pugixml"
    version = "1.15-r0"
    description = "pugixml is a light-weight C++ XML processing library"
    license = "MIT"
    homepage = "https://pugixml.org/"
    url = "https://github.com/zeux/pugixml"

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
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["PUGIXML_BUILD_TESTS"] = False
        tc.variables["PUGIXML_INSTALL"] = True
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
        self.cpp_info.libs = ["pugixml"]
        self.cpp_info.set_property("cmake_file_name", "pugixml")
        self.cpp_info.set_property("cmake_target_name", "pugixml::pugixml")
        self.cpp_info.set_property("pkg_config_name", "pugixml")