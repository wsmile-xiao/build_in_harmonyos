#!/usr/bin/env python3
"""Conan recipe for OpenOBEX 1.7.2."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    copy,
    get,
    replace_in_file,
)


class OpenobexConan(ConanFile):
    name = "openobex"
    version = "1.7.2"
    description = "Object Exchange protocol library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/openobex/mainline"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("openobex supports POSIX platforms")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            cmake_file,
            "cmake_minimum_required ( VERSION 3.1 FATAL_ERROR )",
            "cmake_minimum_required ( VERSION 3.5 FATAL_ERROR )",
        )
        replace_in_file(
            self,
            cmake_file,
            'option ( BUILD_SHARED_LIBS "Build shared libraries" ON )',
            'option ( BUILD_SHARED_LIBS "Build shared libraries" ON )\n'
            'option ( BUILD_APPLICATIONS "Build command-line applications" ON )\n'
            'option ( BUILD_UDEV_SUPPORT "Build Linux udev integration" ON )',
        )
        replace_in_file(
            self,
            cmake_file,
            "add_subdirectory ( udev )",
            "if ( BUILD_UDEV_SUPPORT )\n"
            "  add_subdirectory ( udev )\n"
            "endif ( BUILD_UDEV_SUPPORT )",
        )
        replace_in_file(
            self,
            cmake_file,
            "add_subdirectory ( apps )",
            "if ( BUILD_APPLICATIONS )\n"
            "  add_subdirectory ( apps )\n"
            "endif ( BUILD_APPLICATIONS )",
        )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.variables["BUILD_APPLICATIONS"] = False
        toolchain.variables["BUILD_UDEV_SUPPORT"] = False
        toolchain.variables["BUILD_DOCUMENTATION"] = False
        toolchain.variables["OPENOBEX_BLUETOOTH"] = False
        toolchain.variables["OPENOBEX_IRDA"] = False
        toolchain.variables["OPENOBEX_USB"] = False
        toolchain.variables["OBEX_DEBUG_SYSLOG"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["openobex"]
        self.cpp_info.set_property("cmake_file_name", "OpenObex")
        self.cpp_info.set_property("cmake_target_name", "OpenObex::openobex")
