#!/usr/bin/env python3
"""Conan recipe - cctest 1.0.0 (Modern C++ xUnit Test Framework)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os


class CctestConan(ConanFile):
    name = "cctest"
    version = "1.0.0"
    description = "A simple, practical and scalable xUnit Test Framework in Modern C++"
    license = "Apache-2.0"
    homepage = "https://github.com/ccup/cctest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS_SKIP"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cctest"]
        if str(self.settings.os) == "Linux" or str(self.settings.os) == "ohos":
            self.cpp_info.system_libs = ["pthread"]