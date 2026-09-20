#!/usr/bin/env python3
"""Conan recipe for gifify 2.4.0 — a Node.js CLI tool.

gifify converts any video file to an optimized animated GIF.
It is a pure Node.js project (no C/C++ compilation).
Build step: npm install --omit=dev to fetch npm dependencies.
Runtime dependencies: ffmpeg, convert (ImageMagick), gifsicle, Node.js.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GififyConan(ConanFile):
    name = "gifify"
    version = "2.4.0"
    description = "Convert any video file to an optimized animated GIF"
    license = "ISC"
    homepage = "https://github.com/vvo/gifify"

    package_type = "application"

    # Node.js project: no compiler needed, but CI L0p requires all four settings
    settings = "os", "compiler", "build_type", "arch"  # noqa: all four required by CI profile

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # basic_layout separates source and build folders;
        # npm install must run in source folder where package.json lives.
        self.run("npm install --omit=dev", cwd=self.source_folder)

    def package(self):
        # Copy project files to lib/gifify/
        dest = os.path.join(self.package_folder, "lib", "gifify")
        # Copy bin/gifify script (src/bin/ -> dest/bin/)
        copy(self, "gifify", os.path.join(self.source_folder, "bin"),
             os.path.join(dest, "bin"))
        # Copy root-level project files
        copy(self, "index.js", self.source_folder, dest)
        copy(self, "package.json", self.source_folder, dest)
        copy(self, "HISTORY.md", self.source_folder, dest)
        copy(self, "LICENSE.md", self.source_folder, dest)
        copy(self, "README.md", self.source_folder, dest)
        # Copy node_modules
        copy(self, "*", os.path.join(self.source_folder, "node_modules"),
             os.path.join(dest, "node_modules"))
        # Create bin/gifify symlink (relative path for portability)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        link_path = os.path.join(bin_dir, "gifify")
        if os.path.lexists(link_path):
            os.remove(link_path)
        os.symlink("../lib/gifify/bin/gifify", link_path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/gifify"]
