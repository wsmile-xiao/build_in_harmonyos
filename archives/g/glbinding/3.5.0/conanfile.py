#!/usr/bin/env python3
"""Conan recipe for glbinding 3.5.0 - CMake project.

C++ binding for the OpenGL API.
This recipe enforces R26: static linking for terminal tools (BUILD_SHARED_LIBS=OFF).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class GlbindingConan(ConanFile):
    name = "glbinding"
    version = "3.5.0"
    description = "C++ binding for the OpenGL API"
    license = "MIT"
    homepage = "https://github.com/cginternals/glbinding"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["OPTION_BUILD_TESTS"] = "OFF"
        tc.variables["OPTION_BUILD_DOCS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Pass BUILD_SHARED_LIBS=OFF on the command line to override
        # the project's option() default of ON (R26: static linking).
        cmake.configure(variables={
            "BUILD_SHARED_LIBS": "OFF",
            "OPTION_BUILD_TESTS": "OFF",
            "OPTION_BUILD_DOCS": "OFF",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["glbinding", "glbinding-aux"]
