#!/usr/bin/env python3
"""Conan recipe — boost-sml 1.2.0 (header-only C++ state machine library).

Boost.SML ships only headers (include/boost/sml.hpp + include/boost/sml/),
so this recipe downloads the official release tarball and installs headers.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class BoostSmlConan(ConanFile):
    name = "boost-sml"
    version = "1.2.0"
    description = "C++14 header-only state machine library (Boost.SML)"
    license = "BSL-1.0"
    homepage = "https://boost-ext.github.io/sml/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []