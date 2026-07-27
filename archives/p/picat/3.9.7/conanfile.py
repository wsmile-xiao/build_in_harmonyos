#!/usr/bin/env python3
"""Conan recipe — picat 3.9.7 (Makefile)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PicatConan(ConanFile):
    name = "picat"
    version = "3.9.7"
    description = "Simple, and yet powerful, logic-based multi-paradigm programming language"
    license = "MPL-2.0"
    homepage = "https://picat-lang.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Picat uses a custom Makefile (Makefile.ohos) for OpenHarmony
        # The Makefile sets CC/CPP to clang/clang++ with -D__OHOS__ and other flags
        # Build happens in the emu/ subdirectory
        self.run("make -f Makefile.ohos -j1", cwd=os.path.join(self.source_folder, "emu"))

    def package(self):
        # Copy the picat binary
        copy(self, "picat", os.path.join(self.source_folder, "emu"),
             os.path.join(self.package_folder, "bin"))
        # Copy the picat library modules (.pi files)
        copy(self, "*.pi", os.path.join(self.source_folder, "lib"),
             os.path.join(self.package_folder, "share", "picat", "lib"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Picat needs PICATPATH to find non-preloaded library modules
        libdir = os.path.join(self.package_folder, "share", "picat", "lib")
        self.runenv_info.append_path("PICATPATH", libdir)
