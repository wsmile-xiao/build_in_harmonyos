#!/usr/bin/env python3
"""Conan recipe for Catalan Hunspell dictionaries, task version 3.0.91."""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class HunspellCaConan(ConanFile):
    name = "hunspell-ca"
    version = "3.0.91"
    description = "Catalan and Valencian Hunspell dictionaries"
    license = "GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://www.softcatala.org/projectes/corrector-ortografic/"
    url = "https://salsa.debian.org/debian/hunspell-ca"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="hunspell-ca_3.0.9+repack1.orig.tar.xz",
        )

    @staticmethod
    def _validate_dictionary(dictionary):
        lines = Path(dictionary).read_text(
            encoding="utf-8", errors="strict"
        ).splitlines()
        if not lines or not lines[0].isdigit():
            raise ValueError(f"{dictionary} has no numeric entry count")
        if int(lines[0]) != len(lines) - 1:
            raise ValueError(
                f"{dictionary} declares {lines[0]} entries but contains "
                f"{len(lines) - 1}"
            )

    def build(self):
        for stem in ("catalan", "catalan-valencia"):
            aff = Path(self.source_folder) / f"{stem}.aff"
            dic = Path(self.source_folder) / f"{stem}.dic"
            if "SET UTF-8" not in aff.read_text(encoding="utf-8"):
                raise ValueError(f"{aff} does not declare UTF-8")
            self._validate_dictionary(dic)

    def package(self):
        dictionary_dir = os.path.join(
            self.package_folder, "share", "hunspell"
        )
        os.makedirs(dictionary_dir, exist_ok=True)

        mappings = {
            "catalan.aff": ("ca.aff", "ca_ES.aff"),
            "catalan.dic": ("ca.dic", "ca_ES.dic"),
            "catalan-valencia.aff": ("ca_ES-valencia.aff",),
            "catalan-valencia.dic": ("ca_ES-valencia.dic",),
        }
        for source, destinations in mappings.items():
            for destination in destinations:
                shutil.copy2(
                    os.path.join(self.source_folder, source),
                    os.path.join(dictionary_dir, destination),
                )

        for license_file in (
            "LICENSE",
            "gpl-2.0.txt",
            "lgpl-2.1.txt",
            "README.txt",
            "release-notes_en.txt",
        ):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        dictionary_dir = os.path.join(
            self.package_folder, "share", "hunspell"
        )
        self.buildenv_info.define_path("DICPATH", dictionary_dir)
        self.runenv_info.define_path("DICPATH", dictionary_dir)
