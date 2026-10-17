#!/usr/bin/env python3
"""Conan recipe for ftxui 6.1.9 — C++ Functional Terminal User Interface library.

FTXUI builds three static libraries: ftxui-screen, ftxui-dom, ftxui-component.
Dependencies: pthread (system-provided).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FtxuiConan(ConanFile):
    name = "ftxui"
    version = "6.1.9"
    description = "C++ Functional Terminal User Interface library for building terminal applications"
    license = "MIT"
    homepage = "https://github.com/ArthurSonzogni/FTXUI"
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
        tc.variables["FTXUI_BUILD_EXAMPLES"] = "OFF"
        tc.variables["FTXUI_BUILD_DOCS"] = "OFF"
        tc.variables["FTXUI_BUILD_TESTS"] = "OFF"
        tc.variables["FTXUI_ENABLE_INSTALL"] = "ON"
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
        self.cpp_info.libs = ["ftxui-component", "ftxui-dom", "ftxui-screen"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
