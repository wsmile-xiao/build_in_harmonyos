#!/usr/bin/env python3
"""Conan recipe for the official KiCad 3D model libraries, tag 10.0.5."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0.0"


class KicadLibrary3dConan(ConanFile):
    name = "kicad-library"
    version = "3d-10.0.5"
    description = "Official KiCad 3D model libraries for PCB design"
    homepage = "https://gitlab.com/kicad/libraries/kicad-packages3D"
    license = "CC-BY-SA-4.0"
    url = ""
    topics = ("kicad", "3d-models", "pcb", "eda", "data")

    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share/kicad/3dmodels"]
        self.cpp_info.set_property("cmake_file_name", "kicad-library")
        self.runenv_info.define_path(
            "KICAD10_3DMODEL_DIR",
            os.path.join(self.package_folder, "share/kicad/3dmodels"),
        )

    def package_id(self):
        self.info.clear()
