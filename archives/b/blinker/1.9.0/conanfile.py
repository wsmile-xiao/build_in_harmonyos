#!/usr/bin/env python3
"""Conan recipe for blinker 1.9.0, a pure-Python signal dispatching library."""
import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class BlinkerConan(ConanFile):
    name = "blinker"
    version = "1.9.0"
    description = "Fast, simple object-to-object and broadcast signaling"
    license = "MIT"
    homepage = "https://github.com/pallets-eco/blinker"
    url = "https://github.com/pallets-eco/blinker"
    package_type = "build-scripts"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        site_packages = os.path.join(staging, "lib", "site-packages")
        os.makedirs(site_packages, exist_ok=True)
        copy(self, "*", src=os.path.join(self.source_folder, "src", "blinker"), dst=os.path.join(site_packages, "blinker"))

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = "site-packages"
        site_src = os.path.join(staging, "lib", py_ver)
        if not os.path.isdir(site_src):
            raise Exception(f"site-packages not found under {staging}")
        copy(self, "*", src=site_src, dst=os.path.join(self.package_folder, "lib", py_ver))
        copy(
            self,
            "*.py",
            src=os.path.join(self.source_folder, "tests"),
            dst=os.path.join(self.package_folder, "res", "upstream_tests"),
        )
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "site-packages",
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
