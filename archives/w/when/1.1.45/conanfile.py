#!/usr/bin/env python3
"""Conan recipe for when — a tiny personal calendar program (Perl).

when is a Perl-based personal calendar application. It has no C/C++ compilation;
the "build" step generates a manpage via pod2man, then installs the Perl script
and manpage.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WhenConan(ConanFile):
    name = "when"
    version = "1.1.45"
    description = "A tiny personal calendar program for Unix"
    license = "GPL-2.0-only"
    homepage = "http://www.lightandmatter.com/when/when.html"
    url = "https://bitbucket.org/ben-crowell/when/get/1.1.45.tar.bz2"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Generate manpage from POD — run in source folder where Makefile lives
        self.run(f"make -C {self.source_folder} when.1")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)

        # Copy the script with correct shebang for OHOS
        script_src = os.path.join(self.source_folder, "when")
        script_dst = os.path.join(bin_dir, "when")
        with open(script_src, "r") as f:
            content = f.read()
        # Rewrite shebang to use system Perl
        perl_path = "/data/service/hnp/bin/perl" if self.settings.os == "OHOS" else "/usr/bin/perl"
        content = re.sub(r'^#!.*perl', f"#!{perl_path}", content, count=1)
        with open(script_dst, "w") as f:
            f.write(content)
        os.chmod(script_dst, 0o755)

        # Copy manpage
        copy(self, "when.1", self.source_folder, man_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
