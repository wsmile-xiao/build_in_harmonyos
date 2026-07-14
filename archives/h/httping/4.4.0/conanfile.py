#!/usr/bin/env python3
"""Conan recipe for httping 4.4.0."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class HttpingConan(ConanFile):
    name = "httping"
    version = "4.4.0"
    description = "Ping an HTTP server and measure response times"
    license = "AGPL-3.0-or-later"
    homepage = "https://www.vanheusden.com/httping/"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["USE_SSL"] = False
        tc.cache_variables["USE_TUI"] = False
        tc.cache_variables["USE_FFTW3"] = False
        tc.cache_variables["USE_GETTEXT"] = False
        tc.generate()

    def build(self):
        replace_in_file(
            self,
            os.path.join(self.source_folder, "main.c"),
            'setlocale(LC_ALL, "");\n\tbindtextdomain("httping", LOCALEDIR);\n\ttextdomain("httping");',
            'setlocale(LC_ALL, "");',
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
