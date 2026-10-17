#!/usr/bin/env python3
"""Conan recipe for SuperNOVAS 1.7.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class SupernovasConan(ConanFile):
    name = "supernovas"
    version = "1.7.1"
    description = "SuperNOVAS C/C++ astrometry library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Smithsonian/SuperNOVAS"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("SuperNOVAS is adapted for Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.arch == "armv8":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_DOC"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_BENCHMARK"] = False
        tc.variables["BUILD_TESTING"] = True
        tc.variables["ENABLE_TESTING_ONLINE"] = False
        tc.variables["WITHOUT_CURL"] = True
        tc.variables["WITHOUT_LIBC"] = False
        tc.variables["ENABLE_CPP"] = True
        tc.variables["ENABLE_CALCEPH"] = False
        tc.variables["ENABLE_CSPICE"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            cmake.ctest(cli_args=["--output-on-failure"])
        else:
            self.output.info("Cross-building: upstream tests compiled but cannot run")

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "supernovas")

        core = self.cpp_info.components["core"]
        core.set_property("cmake_target_name", "supernovas::core")
        core.libs = ["supernovas"]
        if self.settings.os in ("Linux", "OHOS"):
            core.system_libs = ["m"]

        cpp = self.cpp_info.components["cpp"]
        cpp.set_property("cmake_target_name", "supernovas::cpp")
        cpp.libs = ["supernovas++"]
        cpp.requires = ["core"]
