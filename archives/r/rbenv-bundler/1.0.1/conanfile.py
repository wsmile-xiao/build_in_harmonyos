#!/usr/bin/env python3
"""Conan recipe for rbenv-bundler 1.0.1

rbenv-bundler is an rbenv plugin that makes shims aware of bundle
installation paths. It is a pure shell/ruby script project — no compilation
required, only file installation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RbenvBundlerConan(ConanFile):
    name = "rbenv-bundler"
    version = "1.0.1"
    description = "An rbenv plugin that makes shims aware of bundle installation paths"
    license = "Apache-2.0"
    homepage = "https://github.com/carsomyr/rbenv-bundler"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Shell script project — no compilation needed

    def package(self):
        copy(self, "rbenv-bundler", os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "*", os.path.join(self.source_folder, "etc", "rbenv.d"), os.path.join(self.package_folder, "etc", "rbenv.d"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["etc"]
