#!/usr/bin/env python3
"""Conan recipe for aconf-mod-strongswan 0.8.1."""

import os

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class AconfModStrongswanConan(ConanFile):
    name = "aconf-mod-strongswan"
    version = "0.8.1"

    description = "strongSwan configuration module for aconf"
    license = "MIT"
    homepage = "https://gitlab.alpinelinux.org/alpinelinux/aconf"
    url = "https://gitlab.alpinelinux.org/alpinelinux/aconf"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aconf/0.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "strongswan.lua",
            src=os.path.join(
                self.source_folder,
                "aconf",
                "modules",
            ),
            dst=os.path.join(
                self.package_folder,
                "usr",
                "share",
                "lua",
                "5.4",
                "aconf",
                "modules",
            ),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
