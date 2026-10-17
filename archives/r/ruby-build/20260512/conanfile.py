#!/usr/bin/env python3
"""Conan recipe — ruby-build 20260512 (bash script tool).

ruby-build is a command-line tool for compiling and installing Ruby
from source on Unix-like systems. It can be used as an rbenv plugin
or standalone. The package is pure bash scripts — no compilation needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class RubyBuildConan(ConanFile):
    name = "ruby-build"
    version = "20260512"
    description = "Compile and install Ruby from source on Unix-like systems"
    license = "MIT"
    homepage = "https://github.com/rbenv/ruby-build"

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
        src_bin = os.path.join(self.source_folder, "bin")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "ruby-build", src=src_bin, dst=bin_dir)
        copy(self, "rbenv-install", src=src_bin, dst=bin_dir)
        copy(self, "rbenv-uninstall", src=src_bin, dst=bin_dir)

        share_dir = os.path.join(self.package_folder, "share", "ruby-build")
        os.makedirs(share_dir, exist_ok=True)
        copy(self, "*", src=os.path.join(self.source_folder, "share", "ruby-build"), dst=share_dir)

        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "*.1", src=os.path.join(self.source_folder, "share", "man", "man1"), dst=man_dir)

        for script in ("ruby-build", "rbenv-install", "rbenv-uninstall"):
            script_path = os.path.join(bin_dir, script)
            if os.path.exists(script_path):
                os.chmod(script_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
