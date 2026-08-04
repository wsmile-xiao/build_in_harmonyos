#!/usr/bin/env python3
"""Conan recipe — festvox-kdlpc8k 1.4.0 (Festival voice data package).

A pure voice/resource data package for Festival speech synthesis system:
American English male diphone voice (Kurt Diphone, 8 kHz, LPC).

This is a resource-only package — no C/C++ code, no build step.
Installed to share/festival/voices/english/ked_diphone/.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FestvoxKdlpc8kConan(ConanFile):
    name = "festvox-kdlpc8k"
    version = "1.4.0"
    description = (
        "Festival voice data: American English male diphone voice "
        "(Kurt Diphone, 8 kHz, LPC residual excited synthesis)"
    )
    license = "Festival-license"  # BSD-style 4-condition permissive (CSTR Edinburgh COPYING)
    homepage = "https://www.cstr.ed.ac.uk/projects/festival/"
    url = ""  # CI fills this

    package_type = "unknown"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        src = os.path.join(self.source_folder, "lib", "voices", "english", "ked_diphone")
        dst = os.path.join(self.package_folder, "share", "festival", "voices", "english", "ked_diphone")
        copy(self, "*", src, dst)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
