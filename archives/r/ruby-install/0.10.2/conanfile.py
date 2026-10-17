#!/usr/bin/env python3
"""Conan recipe — ruby-install 0.10.2 (Makefile, pure shell script tool)"""
import os

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class RubyinstallConan(ConanFile):
    name = "ruby-install"
    version = "0.10.2"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/postmodern/ruby-install"
    description = "Installs Ruby, JRuby, TruffleRuby, or mruby"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure shell script tool — no compilation needed

    def package(self):
        # Install using the Makefile's install target.
        # Override SHELL to use the OHOS bash path (Makefile has SHELL=/usr/bin/env bash
        # which doesn't exist on OHOS). The conan profile sets SHELL in buildenv.
        shell = os.environ.get("SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f"make -C {self.source_folder} install "
            f"SHELL={shell} PREFIX= DESTDIR={self.package_folder}"
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
