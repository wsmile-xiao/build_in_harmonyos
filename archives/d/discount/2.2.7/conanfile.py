#!/usr/bin/env python3
"""Conan recipe for discount 2.2.7 — a fast C implementation of Markdown.

discount uses a custom configure.sh (not standard autotools configure).
The build system is: configure.sh → Makefile → make → make install.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class DiscountConan(ConanFile):
    name = "discount"
    version = "2.2.7"
    description = "A fast C implementation of John Gruber's Markdown markup language"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Orc/discount"
    url = "https://github.com/Orc/discount"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # discount uses a custom configure.sh, not standard autotools configure
        self.run("./configure.sh --prefix={}".format(self.package_folder),
                 cwd=self.source_folder, env="conanbuild")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = ["markdown"]
        self.cpp_info.set_property("cmake_target_name", "discount::discount")
