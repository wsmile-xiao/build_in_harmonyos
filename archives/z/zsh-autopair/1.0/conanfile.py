#!/usr/bin/env python3
"""Conan recipe — zsh-autopair 1.0 (custom, pure Zsh plugin)"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZshAutopairConan(ConanFile):
    name = "zsh-autopair"
    version = "1.0"
    description = "Auto-close and delete matching delimiters in Zsh"
    license = "MIT"
    homepage = "https://github.com/hlissner/zsh-autopair"
    url = "https://github.com/hlissner/zsh-autopair"
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
        self.output.info("Pure Zsh plugin; no native build step required")

    def package(self):
        plugin_dir = os.path.join(self.package_folder, "share", "zsh-autopair")
        copy(self, "autopair.zsh", src=self.source_folder, dst=plugin_dir)
        copy(self, "*.plugin.zsh", src=self.source_folder, dst=plugin_dir)
        copy(self, "README.md", src=self.source_folder, dst=plugin_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=plugin_dir)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        plugin_dir = os.path.join(self.package_folder, "share", "zsh-autopair")
        self.runenv_info.prepend_path("ZSH_AUTOPAIR_DIR", plugin_dir)
