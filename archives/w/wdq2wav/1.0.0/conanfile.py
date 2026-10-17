#!/usr/bin/env python3
"""Conan recipe for wdq2wav, a WinDAQ channel to WAV converter."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.files import chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class Wdq2wavConan(ConanFile):
    name = "wdq2wav"
    version = "1.0.0"
    description = "Convert a channel of a WinDAQ file to WAV format"
    license = "GPL-2.0-only"
    homepage = "https://packages.debian.org/source/wdq2wav"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        with chdir(self, self.source_folder):
            self.run("make -j1")

    def package(self):
        copy(self, "wdq2wav", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "wdq2wav.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
