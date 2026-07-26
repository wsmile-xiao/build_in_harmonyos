#!/usr/bin/env python3
"""Conan recipe — zimfw 1.20.0 (pure Zsh script, no compilation)."""
import gzip
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class ZimfwConan(ConanFile):
    name = "zimfw"
    version = "1.20.0"
    description = "Zim Framework — Zsh plugin manager"
    license = "MIT"
    homepage = "https://zimfw.sh"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # zimfw is distributed as a single gzip-compressed Zsh script.
        # download() fetches the .gz file; we decompress it manually since
        # get() expects tar.gz / zip archives, not plain .gz files.
        src_data = self.conan_data["sources"]
        gz_name = src_data.get("filename", "zimfw.zsh.gz")
        download(self, url=src_data["url"], sha256=src_data["sha256"],
                 filename=gz_name)
        gz_path = os.path.join(self.source_folder, gz_name)
        zsh_path = os.path.join(self.source_folder, "zimfw.zsh")
        with gzip.open(gz_path, "rb") as f_in:
            with open(zsh_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.unlink(gz_path)

    def build(self):
        # zimfw is a pure Zsh script — no native build step required
        apply_conandata_patches(self)

    def package(self):
        # Install zimfw.zsh into share/ (matching Homebrew layout)
        share_dir = os.path.join(self.package_folder, "share")
        copy(self, "zimfw.zsh", src=self.source_folder, dst=share_dir)
        # Ensure executable bit
        zsh_path = os.path.join(share_dir, "zimfw.zsh")
        if os.path.isfile(zsh_path):
            os.chmod(zsh_path, 0o755)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["share"]
        share_dir = os.path.join(self.package_folder, "share")
        self.runenv_info.prepend_path("ZIMFW_DIR", share_dir)
