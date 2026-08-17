#!/usr/bin/env python3
"""Conan recipe — sslmate 1.10.0 (Makefile/Perl)

sslmate is a command-line tool for purchasing and managing SSL certificates
through the SSLMate service. It is a pure Perl script application with no
C/C++ compilation — the "build" step runs sed to bake in install paths.

Build system: simple Makefile (no configure script).
License: MIT-style (see COPYING file in source).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SslmateConan(ConanFile):
    name = "sslmate"
    version = "1.10.0"
    description = "Command-line tool for purchasing and managing SSL certificates via SSLMate service"
    license = "MIT"
    homepage = "https://sslmate.com"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external Conan deps: Perl is pre-installed on OHOS

    def layout(self):
        # sslmate builds in-source (Makefile is in source root), so
        # build and source share the same directory.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # sslmate is a Perl script app; "build" runs sed to generate
        # bin/sslmate.bin with absolute paths baked in. We run it to
        # verify the Makefile works, but package the original bin/sslmate
        # which uses FindBin-relative paths (relocatable in Conan cache).
        self.run("make PREFIX=/usr/local", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        # Install the original bin/sslmate (not sslmate.bin) which uses
        # FindBin-relative paths: use lib "$FindBin::Bin/../perllib"
        # This makes the package relocatable within the Conan cache.
        copy(self, "sslmate", src=os.path.join(src, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        os.chmod(os.path.join(self.package_folder, "bin", "sslmate"), 0o755)

        # Perl library modules
        copy(self, "*", src=os.path.join(src, "perllib"),
             dst=os.path.join(self.package_folder, "perllib"))

        # Libexec scripts (approval hooks)
        copy(self, "*", src=os.path.join(src, "libexec"),
             dst=os.path.join(self.package_folder, "libexec"))

        # Shared data (dhparams, etc.)
        copy(self, "*", src=os.path.join(src, "share"),
             dst=os.path.join(self.package_folder, "share"))

        # Man page
        copy(self, "sslmate.1", src=os.path.join(src, "man", "man1"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

        # Documentation
        for doc in ("README", "NEWS", "COPYING"):
            copy(self, doc, src=src,
                 dst=os.path.join(self.package_folder, "share", "doc", "sslmate"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["perllib", "libexec", "share"]
