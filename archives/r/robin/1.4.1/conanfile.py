#!/usr/bin/env python3
"""Conan recipe — robin-map 1.4.1 (header-only).

The upstream package is TSL's robin-map; the contest task and package name are
`robin`.  Only public headers and upstream CMake package metadata are packaged;
no target binary is produced.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class RobinConan(ConanFile):
    name = "robin"
    version = "1.4.1"
    description = "C++ fast hash map and hash set using Robin Hood hashing (header-only)"
    license = "MIT"
    homepage = "https://github.com/Tessil/robin-map"
    url = "https://github.com/Tessil/robin-map"
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "robin-map supports Linux and OHOS in this recipe, got %s"
                % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TSL_ROBIN_MAP_ENABLE_INSTALL"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "tsl-robin-map")
        self.cpp_info.set_property("cmake_target_name", "tsl::robin_map")
        self.cpp_info.set_property("pkg_config_name", "tsl-robin-map")
