#!/usr/bin/env python3
"""Conan recipe for dgit 15.13 - Perl script tool for Debian packaging with git.

dgit is a Perl CLI tool that integrates git with Debian-style archives.
No C/C++ compilation required - pure Perl scripts and modules.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class DgitConan(ConanFile):
    name = "dgit"
    version = "15.13"
    license = "GPL-3.0+"
    author = "Ian Jackson <ijackson@chiark.greenend.org.uk>"
    url = "https://salsa.debian.org/dgit-team/dgit"
    homepage = "https://packages.debian.org/sid/dgit"
    description = "Integration between git and Debian-style archives"
    topics = ("git", "debian", "packaging", "version-control", "perl")
    package_type = "application"
    settings = "os", "arch"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # dgit is a Perl script package, no compilation needed
        pass

    def package(self):
        # Copy executable scripts to bin/
        scripts = [
            "dgit",
            "git-playtree-setup",
            "mini-git-tag-fsck",
            "tag2upload-fetch-inputs",
            "tag2upload-obtain-origs",
            "git-debrebase",
            "git-debpush",
            "git-deborig",
        ]
        for script in scripts:
            copy(
                self,
                script,
                dst=os.path.join(self.package_folder, "bin"),
                src=self.source_folder,
            )

        # Copy Perl modules to lib/ (preserving directory structure)
        copy(
            self,
            "*.pm",
            dst=os.path.join(self.package_folder, "lib"),
            src=self.source_folder,
            keep_path=True,
        )

        # Copy shared shell functions
        copy(
            self,
            "dgit-functions.sh",
            dst=os.path.join(self.package_folder, "share", "dgit"),
            src=self.source_folder,
        )

        # Copy LICENSE
        copy(
            self,
            "DEVELOPER-CERTIFICATE",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []

        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, "lib")

        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.runenv_info.prepend_path("PATH", bin_path)

        self.output.info(f"Setting PERL5LIB: {lib_path}")
        self.runenv_info.prepend_path("PERL5LIB", lib_path)
