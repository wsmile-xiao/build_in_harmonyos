"""Conan recipe for the qmc 0.94 Boolean expression simplifier."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class QmcConan(ConanFile):
    name = "qmc"
    version = "0.94"
    description = "Quine-McCluskey Boolean expression simplifier"
    license = "GPL-2.0-or-later"
    homepage = "http://qmc.pollaknet.at/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
