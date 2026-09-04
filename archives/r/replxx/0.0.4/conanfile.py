#!/usr/bin/env python3
"""Conan recipe — replxx 0.0.4 (CMake, HarmonyOS PC adaptation).

Static C++11 readline-like line editing library; depends only on system
Threads. Built with CMake toolchain for OHOS (aarch64).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ReplxxConan(ConanFile):
    name = "replxx"
    version = "0.0.4"
    description = "replxx 0.0.4 — readline-like line editing library"
    license = "MIT"
    homepage = "https://github.com/AmokHuginnsson/replxx"
    url = "https://github.com/AmokHuginnsson/replxx"

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
        tc.variables["CMAKE_INSTALL_PREFIX"] = "/storage/Users/currentUser/usr/local"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
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
        self.cpp_info.libs = ["replxx"]
