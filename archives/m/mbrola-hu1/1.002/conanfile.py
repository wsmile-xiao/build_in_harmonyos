#!/usr/bin/env python3
"""Conan recipe for the MBROLA Hungarian female voice database HU1."""

import os
import sys

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MbrolaHu1Conan(ConanFile):
    name = "mbrola-hu1"
    version = "1.002"
    description = "Hungarian female diphone voice database for MBROLA"
    license = "LicenseRef-MBROLA"
    homepage = (
        "https://github.com/numediart/MBROLA-voices/tree/master/data/hu1"
    )
    url = "https://github.com/numediart/MBROLA-voices"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "test_mbrola_hu1.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="mbrola-hu1_1.002+repack2.orig.tar.xz",
            strip_root=True,
        )
        apply_conandata_patches(self)

    @property
    def _validator(self):
        return os.path.join(
            self.export_sources_folder,
            "test_package",
            "test_mbrola_hu1.py",
        )

    def build(self):
        command = (
            f'"{sys.executable}" "{self._validator}" '
            f'--source-root "{self.source_folder}"'
        )
        self.run(command)

    def package(self):
        voice_dir = os.path.join(
            self.package_folder, "share", "mbrola", "hu1"
        )
        documentation_dir = os.path.join(
            self.package_folder,
            "share",
            "doc",
            "mbrola-hu1",
        )
        examples_dir = os.path.join(documentation_dir, "examples")

        copy(
            self,
            "hu1",
            src=self.source_folder,
            dst=voice_dir,
        )
        copy(
            self,
            "README.txt",
            src=self.source_folder,
            dst=documentation_dir,
        )
        copy(
            self,
            "*.pho",
            src=os.path.join(self.source_folder, "test"),
            dst=examples_dir,
        )
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "test"),
            dst=examples_dir,
        )
        copy(
            self,
            "license.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]

        voice_file = os.path.join(
            self.package_folder,
            "share",
            "mbrola",
            "hu1",
            "hu1",
        )
        examples_dir = os.path.join(
            self.package_folder,
            "share",
            "doc",
            "mbrola-hu1",
            "examples",
        )
        self.buildenv_info.define_path("MBROLA_VOICE_HU1", voice_file)
        self.buildenv_info.define_path(
            "MBROLA_HU1_EXAMPLES", examples_dir
        )
        self.runenv_info.define_path("MBROLA_VOICE_HU1", voice_file)
        self.runenv_info.define_path(
            "MBROLA_HU1_EXAMPLES", examples_dir
        )
