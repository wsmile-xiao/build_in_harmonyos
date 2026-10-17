#!/usr/bin/env python3
"""Conan recipe for nodenv — Node.js version manager (shell script).

nodenv is a pure shell script project (no C/C++ compilation).
It installs shell scripts, completions, hooks, and man pages.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class NodenvConan(ConanFile):
    name = "nodenv"
    version = "1.6.2"
    description = "Node.js version manager similar to rbenv"
    license = "MIT"
    homepage = "https://github.com/nodenv/nodenv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Copy libexec scripts (the core of nodenv) preserving symlinks
        libexec_src = os.path.join(self.source_folder, "libexec")
        libexec_dst = os.path.join(self.package_folder, "libexec")
        shutil.copytree(libexec_src, libexec_dst, symlinks=True)

        # Create bin/nodenv as symlink to ../libexec/nodenv
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        os.symlink("../libexec/nodenv", os.path.join(bin_dir, "nodenv"))

        # Copy completions
        completions_src = os.path.join(self.source_folder, "completions")
        completions_dst = os.path.join(self.package_folder, "completions")
        if os.path.isdir(completions_src):
            shutil.copytree(completions_src, completions_dst, symlinks=True)

        # Copy nodenv.d hooks
        nodenv_d_src = os.path.join(self.source_folder, "nodenv.d")
        nodenv_d_dst = os.path.join(self.package_folder, "nodenv.d")
        if os.path.isdir(nodenv_d_src):
            shutil.copytree(nodenv_d_src, nodenv_d_dst, symlinks=True)

        # Copy share/man
        share_src = os.path.join(self.source_folder, "share")
        share_dst = os.path.join(self.package_folder, "share")
        if os.path.isdir(share_src):
            shutil.copytree(share_src, share_dst, symlinks=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec"]
        self.cpp_info.resdirs = ["share"]
