#!/usr/bin/env python3
"""Conan recipe for efi-mkuki — EFI Unified Kernel Image Maker (shell script).

Shell script project, no compilation needed.
Installs the efi-mkuki script to bin/ directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class EfiMkukiConan(ConanFile):
    name = "efi-mkuki"
    version = "1.0.0"
    description = "EFI Unified Kernel Image Maker — create UKI from kernel, initrd and cmdline"
    license = "MIT"
    homepage = "https://github.com/jirutka/efi-mkuki"
    url = "https://github.com/jirutka/efi-mkuki"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "efi-mkuki", src=self.source_folder, dst=bin_dir)
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README*", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "efi-mkuki"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
