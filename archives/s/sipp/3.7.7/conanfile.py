#!/usr/bin/env python3
"""Conan recipe for SIPp 3.7.7."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class SippConan(ConanFile):
    name = "sipp"
    version = "3.7.7"
    description = "Traffic generator for the SIP protocol"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/SIPp/sipp"
    url = "https://github.com/SIPp/sipp"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["USE_SSL"] = "OFF"
        tc.variables["USE_PCAP"] = "OFF"
        tc.variables["USE_SCTP"] = "OFF"
        tc.variables["USE_GSL"] = "OFF"
        tc.variables["BUILD_STATIC"] = False
        tc.variables["USE_ASAN"] = False

        default_prefix = os.environ.get("DEFAULT_PREFIX")
        if default_prefix:
            include_dir = os.path.join(default_prefix, "include")
            lib_dir = os.path.join(default_prefix, "lib")
            curses_library = os.path.join(lib_dir, "libncursesw.a")
            tinfo_library = os.path.join(lib_dir, "libtinfow.a")
            if not os.path.exists(tinfo_library):
                tinfo_library = os.path.join(lib_dir, "libtinfo.a")
            if os.path.exists(curses_library):
                tc.variables["CURSES_LIBRARY"] = curses_library
                if os.path.exists(tinfo_library):
                    tc.variables["TINFO_LIBRARY"] = tinfo_library
                tc.variables["CURSES_LIBRARY_INCLUDE_DIRS"] = ";".join([include_dir, os.path.join(include_dir, "ncursesw")])
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "sipp", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(
            self,
            "*.xml",
            os.path.join(self.source_folder, "sipp_scenarios"),
            os.path.join(self.package_folder, "res", "sipp_scenarios"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]