#!/usr/bin/env python3
"""Conan recipe — check 0.15.2 (CMake).

A unit testing framework for C.  Uses CMake build system.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
from conan.tools.env import VirtualBuildEnv
import os

required_conan_version = ">=2.0"


class CheckConan(ConanFile):
    name = "check"
    version = "0.15.2"
    package_type = "library"

    description = "A unit testing framework for C"
    homepage = "https://libcheck.github.io/check/"
    license = "LGPL-2.1-only"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        venv = VirtualBuildEnv(self)
        venv.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # check 上游许可证文件名为 COPYING.LESSER，一并拷贝
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "check")
        self.cpp_info.set_property("cmake_target_name", "Check::check")
        self.cpp_info.libs = ["check"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["m", "rt", "pthread"]

    # package_id intentionally omitted: settings (os, arch, compiler, build_type)
    # must contribute to the Conan package ID so that different platform builds
    # produce distinct binaries.
