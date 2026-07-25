#!/usr/bin/env python3
"""Conan recipe for anyenv 1.1.5.

anyenv is a pure Bash command-line tool. Packaging copies the upstream
scripts, completions, and support directories without compiling native code.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AnyenvConan(ConanFile):
    name = "anyenv"
    version = "1.1.5"
    description = "All-in-one wrapper for rbenv-style environment managers"
    license = "MIT"
    homepage = "https://github.com/anyenv/anyenv"
    url = ""

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="anyenv-1.1.5.tar.gz", strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "anyenv"))
        copy(self, "*", src=os.path.join(self.source_folder, "libexec"), dst=os.path.join(self.package_folder, "libexec"))
        copy(self, "*", src=os.path.join(self.source_folder, "completions"), dst=os.path.join(self.package_folder, "completions"))
        copy(self, ".keep", src=os.path.join(self.source_folder, "envs"), dst=os.path.join(self.package_folder, "envs"))

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        anyenv_link = os.path.join(bin_dir, "anyenv")
        if os.path.lexists(anyenv_link):
            os.remove(anyenv_link)
        os.symlink(os.path.join("..", "libexec", "anyenv"), anyenv_link)

        for root, _, files in os.walk(os.path.join(self.package_folder, "libexec")):
            for filename in files:
                path = os.path.join(root, filename)
                os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
