#!/usr/bin/env python3
"""Conan recipe — docx2txt 1.4 (Perl application)"""

import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Docx2txtConan(ConanFile):
    name = "docx2txt"
    version = "1.4"
    description = "Perl command-line utility for converting DOCX documents to plain text"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/docx2txt/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        config_dir = os.path.join(self.package_folder, "etc")
        copy(self, "docx2txt.pl", self.source_folder, bin_dir)
        copy(self, "docx2txt.sh", self.source_folder, bin_dir)
        copy(self, "docx2txt.config", self.source_folder, config_dir)
        os.rename(os.path.join(bin_dir, "docx2txt.pl"), os.path.join(bin_dir, "docx2txt"))
        copy(self, "docx2txt.pl", self.source_folder, bin_dir)
        for name in ("docx2txt", "docx2txt.pl", "docx2txt.sh"):
            path = os.path.join(bin_dir, name)
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path(
            "DOCX2TXT_CONFIG",
            os.path.join(self.package_folder, "etc", "docx2txt.config"),
        )
