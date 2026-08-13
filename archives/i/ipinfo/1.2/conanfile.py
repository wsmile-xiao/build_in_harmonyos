#!/usr/bin/env python3
"""Conan recipe — ipinfo 1.2 (Makefile)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class IpinfoConan(ConanFile):
    name = "ipinfo"
    version = "1.2"
    description = "IP network calculation tool for computing and analyzing IP address info"
    license = "Unknown"
    homepage = "https://kyberdigi.cz/projects/ipinfo/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run(f"make -C {self.source_folder} -j2")

    def package(self):
        copy(self, "ipinfo", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "ipmatch", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
