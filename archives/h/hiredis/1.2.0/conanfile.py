#!/usr/bin/env python3
"""Conan recipe — hiredis 1.2.0 (CMake)"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir
import os

required_conan_version = ">=2.0"


class HiredisConan(ConanFile):
    name = "hiredis"
    version = "1.2.0"
    description = "Minimalistic C client library for Redis"
    license = "BSD-3-Clause"
    homepage = "https://github.com/redis/hiredis"
    url = "https://github.com/redis/hiredis"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_SSL"] = False
        tc.variables["ENABLE_SSL_TESTS"] = False
        tc.variables["DISABLE_TESTS"] = True
        # OHOS platform detection
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.generate()

    def build(self):
        # Patch CMakeLists.txt for CMake 4.x compatibility
        # hiredis uses cmake_minimum_required(3.0.0) which CMake 4.x no longer supports
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_file) as f:
            content = f.read()
        import re
        content = re.sub(
            r"CMAKE_MINIMUM_REQUIRED\(VERSION\s+3\.0\.0\)",
            "CMAKE_MINIMUM_REQUIRED(VERSION 3.5.0)",
            content,
            flags=re.IGNORECASE
        )
        with open(cmake_file, "w") as f:
            f.write(content)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove unnecessary files
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        # Copy license
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["hiredis"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
        self.cpp_info.includedirs = ["include", "include/hiredis"]

    