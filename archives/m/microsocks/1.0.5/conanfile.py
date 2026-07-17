#!/usr/bin/env python3
"""Conan recipe for microsocks 1.0.5 (Tiny SOCKS5 proxy)."""

import os
from conan import ConanFile
from conan.tools.files import get, copy


class MicrosocksConan(ConanFile):
    name = "microsocks"
    version = "1.0.5"
    package_type = "application"

    description = "Tiny SOCKS5 proxy server"
    license = "MIT"
    homepage = "https://github.com/rofl0r/microsocks"
    url = "https://github.com/rofl0r/microsocks"
    topics = ("proxy", "socks5", "network")

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self.run("make -j$(nproc) CC=clang", cwd=self.source_folder)
        self.run("make check", ignore_errors=True, cwd=self.source_folder)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "microsocks", self.source_folder, bin_dir)
        os.chmod(os.path.join(bin_dir, "microsocks"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []