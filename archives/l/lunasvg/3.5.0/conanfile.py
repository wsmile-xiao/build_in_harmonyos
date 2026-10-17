#!/usr/bin/env python3
"""Conan recipe for lunasvg 3.5.0 (CMake, C++17 SVG rendering library).

lunasvg bundles plutovg as a submodule (USE_SYSTEM_PLUTOVG=OFF default), so the
package ships both liblunasvg.a and libplutovg.a. Static consumers must link
both, hence package_info lists both libs.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LunasvgConan(ConanFile):
    name = "lunasvg"
    version = "3.5.0"
    description = "lunasvg is a standalone C++ SVG rendering library."
    license = "MIT"
    homepage = "https://github.com/sammycage/lunasvg"
    url = "https://github.com/sammycage/lunasvg"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

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
        # plutovg is bundled inside lunasvg; no external dependency
        tc.variables["USE_SYSTEM_PLUTOVG"] = "OFF"
        tc.variables["LUNASVG_BUILD_EXAMPLES"] = "OFF"
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
        self.cpp_info.libs = ["lunasvg", "plutovg"]
        if not self.options.shared:
            self.cpp_info.defines = ["LUNASVG_BUILD_STATIC"]
