#!/usr/bin/env python3
"""Conan recipe for pugixml 1.16."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PugixmlConan(ConanFile):
    name = "pugixml"
    version = "1.16"
    description = "Light-weight C++ XML processing library"
    license = "MIT"
    homepage = "https://pugixml.org/"
    url = "https://github.com/zeux/pugixml"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
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
