#!/usr/bin/env python3
"""Conan recipe for log4cpp 1.1.6."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class Log4cppConan(ConanFile):
    name = "log4cpp"
    version = "1.1.6"
    description = "C++ library for flexible logging"
    license = "LGPL-2.1-or-later"
    homepage = "https://log4cpp.sourceforge.net"
    url = "https://github.com/log4cpp/log4cpp"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        toolchain.variables["LOG4CPP_BUILD_EXAMPLES"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not cross_building(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" '
                "--output-on-failure --no-tests=error"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["log4cpp"]
        if str(self.settings.os) != "Windows":
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "log4cpp")
        self.cpp_info.set_property(
            "cmake_target_name", "log4cpp::log4cpp"
        )
        self.cpp_info.set_property("pkg_config_name", "log4cpp")
