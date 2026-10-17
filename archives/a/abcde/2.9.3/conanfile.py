#!/usr/bin/env python3
"""Conan recipe for abcde — Better CD Encoder (shell script).

Shell script project, no compilation needed.
Installs scripts, config file, man pages and docs.
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class AbcdeConan(ConanFile):
    name = "abcde"
    version = "2.9.3"
    description = "A Better CD Encoder"
    license = "GPL-2.0-or-later"
    homepage = "https://abcde.einval.com/"
    url = ""

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Install shell scripts
        for f in ["abcde", "cddb-tool", "abcde-musicbrainz-tool"]:
            copy(self, f, src=self.source_folder, dst=bin_dir)
        # Install config
        etc_dir = os.path.join(self.package_folder, "etc")
        os.makedirs(etc_dir, exist_ok=True)
        copy(self, "abcde.conf", src=self.source_folder, dst=etc_dir)
        # Install docs
        doc_dir = os.path.join(self.package_folder, "share", "doc", "abcde")
        os.makedirs(doc_dir, exist_ok=True)
        for f in ["README", "FAQ", "COPYING", "changelog"]:
            copy(self, f, src=self.source_folder, dst=doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
