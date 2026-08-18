#!/usr/bin/env python3
"""Conan recipe — eless 0.7 (pure bash script tool, no C/C++ compilation).

eless is a bash script that uses Emacs in view-mode as a pager (replacement
for less/diff/man). It is distributed as a single executable script — no
configure/make/cmake build step is needed. The build() method simply copies
the script into the package bin/ directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ElessConan(ConanFile):
    name = "eless"
    version = "0.7"
    description = "Bash script to run emacs in view-mode as a pager (replaces less/diff/man)"
    license = "MIT"
    homepage = "https://github.com/kaushalmodi/eless"
    url = ""  # CI fills this

    # eless is a command-line tool (bash script), not a library
    package_type = "application"

    # R32: settings.os must use in ("Linux", "OHOS")
    # L0p: CI requires all four settings even for script tools
    settings = "os", "compiler", "build_type", "arch"

    # No shared/static options — this is a script tool, not a compiled library
    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # eless is a pure bash script — no compilation step.
        # The tarball already contains the generated 'eless' script.
        # No configure, no make needed.
        # apply_conandata_patches is called for G1 compliance (no patches in conandata.yml).
        apply_conandata_patches(self)

    def package(self):
        # Install the eless script to bin/
        copy(self, "eless", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # eless is a command-line tool; declare bindirs so consumers get it on PATH
        self.cpp_info.bindirs = ["bin"]
        # No libs — this is a script tool, not a library
        self.cpp_info.libs = []
