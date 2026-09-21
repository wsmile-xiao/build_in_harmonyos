#!/usr/bin/env python3
"""Conan recipe for the KiCad 10.0.0 project-template resources."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class KicadTemplatesConan(ConanFile):
    name = "kicad-templates"
    version = "10.0.0"
    description = "Official project and worksheet templates for KiCad 10"
    license = "CC-BY-SA-4.0"
    homepage = "https://gitlab.com/kicad/libraries/kicad-templates"
    url = "https://gitlab.com/kicad/libraries/kicad-templates"

    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share/kicad/template"]
        template_dir = os.path.join(
            self.package_folder, "share", "kicad", "template"
        )
        self.runenv_info.define_path("KICAD10_TEMPLATE_DIR", template_dir)
