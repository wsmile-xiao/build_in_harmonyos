#!/usr/bin/env python3
"""Conan recipe for ansifilter — ANSI terminal escape code filter.

Builds the CLI binary (no libraries) using the provided Makefile.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class AnsifilterConan(ConanFile):
    name = "ansifilter"
    version = "2.22"
    description = "Handles text files containing ANSI terminal escape codes"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/saalen/ansifilter"
    url = "https://gitlab.com/saalen/ansifilter"

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
        # ansifilter uses a plain Makefile, not autotools configure
        cxx = os.environ.get("CXX", "clang++")
        cxxflags = "-Wall -O2 -DNDEBUG -std=c++17 -fPIC -D_FILE_OFFSET_BITS=64"
        self.run(f"make -C src -f makefile -j1 CXX={cxx} CXXFLAGS='{cxxflags}'",
                 cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        dst = self.package_folder

        # Binary — copy from src/src/ansifilter to bin/ansifilter
        copy(self, "ansifilter", src=os.path.join(src, "src"),
             dst=os.path.join(dst, "bin"), keep_path=False)

        # Documentation
        for f in ("README.adoc", "ChangeLog.adoc", "COPYING", "INSTALL"):
            copy(self, f, src=src, dst=os.path.join(dst, "share", "doc", "ansifilter"),
                 keep_path=False)

        # Man page
        copy(self, "ansifilter.1", src=os.path.join(src, "man"),
             dst=os.path.join(dst, "share", "man", "man1"), keep_path=False)

        # Shell completions
        copy(self, "ansifilter.bash", src=os.path.join(src, "sh-completion"),
             dst=os.path.join(dst, "share", "bash-completion", "completions"),
             keep_path=False)
        copy(self, "ansifilter.fish", src=os.path.join(src, "sh-completion"),
             dst=os.path.join(dst, "share", "fish", "vendor_completions.d"),
             keep_path=False)
        copy(self, "ansifilter.zsh", src=os.path.join(src, "sh-completion"),
             dst=os.path.join(dst, "share", "zsh", "site-functions"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
