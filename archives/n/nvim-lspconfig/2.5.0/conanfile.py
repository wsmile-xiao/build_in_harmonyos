#!/usr/bin/env python3
"""Conan recipe for nvim-lspconfig 2.5.0.

Upstream is a Neovim Lua plugin. It has no native build step; this recipe
packages the plugin runtime files under share/nvim-lspconfig.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class NvimLspconfigConan(ConanFile):
    name = "nvim-lspconfig"
    version = "2.5.0"
    description = "Quickstart configurations for Neovim's built-in LSP client"
    license = "Apache-2.0"
    homepage = "https://github.com/neovim/nvim-lspconfig"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        share = os.path.join(self.package_folder, "share", "nvim-lspconfig")
        copy(self, "*", os.path.join(self.source_folder, "lua"), os.path.join(share, "lua"))
        copy(self, "*", os.path.join(self.source_folder, "lsp"), os.path.join(share, "lsp"))
        copy(self, "*", os.path.join(self.source_folder, "plugin"), os.path.join(share, "plugin"))
        copy(self, "*", os.path.join(self.source_folder, "doc"), os.path.join(share, "doc"))
        copy(self, "*", os.path.join(self.source_folder, "test"), os.path.join(share, "test"))
        copy(self, "README.md", self.source_folder, share)
        copy(self, "LICENSE.md", self.source_folder, share)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        plugin_root = os.path.join(self.package_folder, "share", "nvim-lspconfig")
        self.runenv_info.define("NVIM_LSPCONFIG_ROOT", plugin_root)
