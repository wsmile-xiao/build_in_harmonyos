#!/usr/bin/env python3
"""Conan recipe for libyaml 0.2.5 — CMake build system."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibyamlConan(ConanFile):
    name = "libyaml"
    version = "0.2.5"
    description = "YAML parser/emitter library"
    license = "MIT"
    homepage = "https://pyyaml.org/wiki/LibYAML"
    url = "https://github.com/yaml/libyaml/archive/refs/tags/0.2.5.tar.gz"

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
        if not self.options.shared:
            tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        else:
            tc.cache_variables["BUILD_SHARED_LIBS"] = "ON"
        # CMake 4.x removed compat for < 3.5; libyaml's cmake_minimum_required(VERSION 3.0)
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
        self.cpp_info.set_property("cmake_file_name", "yaml")
        self.cpp_info.set_property("cmake_target_name", "yaml")
        self.cpp_info.libs = ["yaml"]
