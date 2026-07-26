#!/usr/bin/env python3
"""Conan recipe for cpufetch 1.07 (CPU architecture fetcher)."""

import os
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain


class CpufetchConan(ConanFile):
    name = "cpufetch"
    version = "1.07"
    package_type = "application"

    description = "Simple yet fancy CPU architecture fetching tool"
    license = "GPL-2.0"
    homepage = "https://github.com/Dr-Noob/cpufetch"
    topics = ("cpu", "architecture", "system-info")

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.make(args=["-j1", "os=Linux"])

    def package(self):
        copy(self, "cpufetch", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
