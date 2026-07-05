#!/usr/bin/env python3
"""Conan recipe template — Autotools project.

Usage: Copy to archives/{letter}/{name}/{version}/conanfile.py
       Replace {name}, {version}, {description} with actual values.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class {Name}Conan(ConanFile):
    name = "{name}"
    version = "{version}"
    description = "{description}"
    license = ""  # TODO: 填写许可证
    homepage = ""  # TODO: 填写主页 URL

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["{name}"]
