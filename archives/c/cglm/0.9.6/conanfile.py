#!/usr/bin/env python3
"""Conan recipe — cglm 0.9.6 (CMake)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CglmConan(ConanFile):
    name = "cglm"
    version = "0.9.6"
    description = "Highly optimized 2D/3D math library for C (OpenGL Mathematics)"
    license = "MIT"
    homepage = "https://github.com/recp/cglm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.variables["CGLM_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["CGLM_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["CGLM_USE_TEST"] = "OFF"
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
        self.cpp_info.libs = ["cglm"]
