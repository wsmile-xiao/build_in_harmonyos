#!/usr/bin/env python3
"""Conan recipe for nicovideo-dl 0.0.20190126.

nicovideo-dl is a single-file Python 3 command-line downloader. It has no
native build step and no third-party package dependencies.
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class NicovideoDlConan(ConanFile):
    name = "nicovideo-dl"
    version = "0.0.20190126"
    description = "Command-line downloader for videos from nicovideo.jp"
    license = "X11"
    homepage = "https://osdn.net/projects/nicovideo-dl"
    url = "https://github.com/hakatashi/nicovideo-dl"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "LICENSE"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )

    def build(self):
        # The upstream archive has no build system. Exercise the source
        # script through the active Python interpreter as the build check.
        script = os.path.join(self.source_folder, "nicovideo-dl")
        self.run(
            f'"{sys.executable}" "{script}" --version',
            cwd=self.source_folder,
        )
        self.run(
            f'"{sys.executable}" "{script}" --help',
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        licenses = os.path.join(self.package_folder, "licenses")

        copy(
            self,
            "nicovideo-dl",
            src=self.source_folder,
            dst=bindir,
            keep_path=False,
        )
        os.chmod(os.path.join(bindir, "nicovideo-dl"), 0o755)
        copy(
            self,
            "LICENSE",
            src=self.export_sources_folder,
            dst=licenses,
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
