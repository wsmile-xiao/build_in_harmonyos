#!/usr/bin/env python3
"""Conan recipe for farama-notifications 0.0.6 — pure Python library.

Farama Foundation notifications package. Base dependency of Gymnasium.
Pure Python: package copies the farama_notifications package into
site-packages.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FaramaNotificationsConan(ConanFile):
    name = "farama-notifications"
    version = "0.0.6"
    description = "Farama Foundation notifications helper package"
    license = "MIT"
    homepage = "https://github.com/Farama-Foundation/farama-notifications"
    url = ""

    package_type = "python-require"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "farama_notifications")):
            raise ConanException(
                "farama_notifications/ package dir not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(pkg_dir, exist_ok=True)
        shutil.copytree(
            os.path.join(self.source_folder, "farama_notifications"),
            os.path.join(pkg_dir, "farama_notifications"),
            dirs_exist_ok=True,
        )
        for f in ("LICENSE", "LICENSE.md", "py.typed", "README.md"):
            src = os.path.join(self.source_folder, f)
            if os.path.isfile(src):
                shutil.copy2(src, pkg_dir)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []