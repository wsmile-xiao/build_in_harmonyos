#!/usr/bin/env python3
"""Conan recipe for cutter 1.04 — TCP/IP connection cutter for Linux firewalls.

Cutter is a command-line tool that allows firewall administrators to abort
TCP/IP connections routed over the firewall or router.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class CutterConan(ConanFile):
    name = "cutter"
    version = "1.04"
    description = "TCP/IP connection cutter for Linux firewalls"
    license = "GPL-2.0-only"
    homepage = "http://www.digitage.co.uk/cutter"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self.run(f"make -C {self.source_folder} cutter")

    def package(self):
        self.run(f'make -C {self.source_folder} install DESTDIR="{self.package_folder}" PREFIX=""')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
