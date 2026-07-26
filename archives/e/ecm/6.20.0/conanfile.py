#!/usr/bin/env python3
"""Conan recipe for ECM 6.20.0 on HarmonyOS PC (aarch64).

ECM (Extra CMake Modules) is a collection of additional CMake modules from KDE.
It is a pure CMake module library — no binary code is compiled or linked.

OHOS-specific adaptations:
  - No patches required; ECM installs cleanly on HarmonyOS.
  - package_type = "build-scripts": ECM ships only CMake modules.
  - package_id() uses self.info.clear() to avoid package ID variations
    from compiler/build_type settings (no compiled artifacts).
  - BUILD_TESTING=OFF to skip upstream tests during build.
"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ECMConan(ConanFile):
    name = "ecm"
    version = "6.20.0"
    description = "Extra CMake Modules - additional CMake modules from KDE"
    license = "BSD-3-Clause"
    homepage = "https://kde.org/products/frameworks/"
    url = "https://invent.kde.org/frameworks/extra-cmake-modules"

    package_type = "build-scripts"

    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ECM")
        self.cpp_info.set_property("cmake_target_name", "ECM::ECM")
        self.cpp_info.builddirs = ["share/ECM/cmake"]
