#!/usr/bin/env python3
"""Conan recipe for kicad-library-footprints 10.0.5 (CMake resource package)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


required_conan_version = ">=2.0.0"


class KicadLibraryFootprintsConan(ConanFile):
    name = "kicad-library-footprints"
    version = "10.0.5"
    description = "Official KiCad footprint libraries for PCB design"
    homepage = "https://gitlab.com/kicad/libraries/kicad-footprints"
    license = "CC-BY-SA-4.0"
    topics = ("kicad", "footprints", "pcb", "eda", "data")
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            destination=self.source_folder,
            strip_root=True,
        )

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.md",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "kicad-library-footprints")
