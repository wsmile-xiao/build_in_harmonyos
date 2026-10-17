#!/usr/bin/env python3
"""Conan recipe — ansiweather (bash script tool for weather display)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AnsiweatherConan(ConanFile):
    name = "ansiweather"
    version = "1.19.0"
    description = "Weather in your terminal, with ANSI colors and Unicode symbols"
    license = "BSD-2-Clause"
    homepage = "https://github.com/fcambus/ansiweather"
    url = ""  # CI fills this

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
        # Pure bash script — no compilation needed
        pass

    def package(self):
        import shutil
        src_dir = self.source_folder
        pkg_dir = self.package_folder

        # Install main script
        os.makedirs(os.path.join(pkg_dir, "bin"), exist_ok=True)
        shutil.copy2(os.path.join(src_dir, "ansiweather"),
                     os.path.join(pkg_dir, "bin", "ansiweather"))
        os.chmod(os.path.join(pkg_dir, "bin", "ansiweather"), 0o755)

        # Install man page
        man_dir = os.path.join(pkg_dir, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        shutil.copy2(os.path.join(src_dir, "ansiweather.1"),
                     os.path.join(man_dir, "ansiweather.1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
