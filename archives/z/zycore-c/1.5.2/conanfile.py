#!/usr/bin/env python3
"""Conan recipe for Zycore-C 1.5.2."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class ZycoreCConan(ConanFile):
    name = "zycore-c"
    version = "1.5.2"
    description = "Platform-independent C types, containers, and utility routines"
    license = "MIT"
    homepage = "https://github.com/zyantific/zycore-c"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ZYCORE_BUILD_SHARED_LIB"] = self.options.shared
        toolchain.variables["ZYCORE_BUILD_EXAMPLES"] = False
        # Upstream tests download GoogleTest when it is not preinstalled.
        toolchain.variables["ZYCORE_BUILD_TESTS"] = False
        toolchain.variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst="licenses")
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["Zycore"]
        self.cpp_info.set_property("cmake_file_name", "zycore")
        self.cpp_info.set_property("cmake_target_name", "Zycore::Zycore")
        self.cpp_info.set_property("pkg_config_name", "zycore")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
