#!/usr/bin/env python3
"""Conan recipe for nvm — Node Version Manager (shell script).

nvm is a pure shell script project (no C/C++ compilation).
It installs nvm.sh (sourced to provide the nvm function) and nvm-exec
(a wrapper that sources nvm.sh and runs a command with a specific node version).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class NvmConan(ConanFile):
    name = "nvm"
    version = "0.40.6"
    description = "Node Version Manager - Simple bash script to manage multiple active node.js versions"
    licenses = "MIT"
    homepage = "https://github.com/nvm-sh/nvm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Copy the main nvm.sh script
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy(
            os.path.join(self.source_folder, "nvm.sh"),
            os.path.join(self.package_folder, "bin", "nvm.sh"),
        )
        # Copy nvm-exec wrapper
        shutil.copy(
            os.path.join(self.source_folder, "nvm-exec"),
            os.path.join(self.package_folder, "bin", "nvm-exec"),
        )
        # Copy bash completion
        os.makedirs(os.path.join(self.package_folder, "share", "bash_completion"), exist_ok=True)
        shutil.copy(
            os.path.join(self.source_folder, "bash_completion"),
            os.path.join(self.package_folder, "share", "bash_completion", "nvm"),
        )
        # Copy license
        os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
        shutil.copy(
            os.path.join(self.source_folder, "LICENSE.md"),
            os.path.join(self.package_folder, "licenses", "LICENSE.md"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
