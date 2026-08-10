#!/usr/bin/env python3
"""Conan recipe — alpine-make-vm-image 0.13.4 (Makefile, shell script tool)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AlpineMakeVmImageConan(ConanFile):
    name = "alpine-make-vm-image"
    version = "0.13.4"
    description = "Create Alpine Linux virtual machine images for various hypervisors"
    license = "MIT"
    homepage = "https://github.com/alpinelinux/alpine-make-vm-image"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch"

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
        # Shell script project — use Makefile install target to stage the script
        staging = os.path.join(self.build_folder, "staging")
        self.run(f"make -C {self.source_folder} install PREFIX= DESTDIR={staging}")

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=os.path.join(staging, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
