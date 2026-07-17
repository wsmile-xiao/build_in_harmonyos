#!/usr/bin/env python3
"""Conan recipe for convmv 2.06 — pure Perl script utility.

convmv converts filenames from one character encoding to another.
It is a pure Perl script with a simple Makefile (no configure step).

Platform adaptations for OHOS:
  1. Shebang fix: #!/usr/bin/perl → #!/usr/bin/env perl
     (OHOS has no /usr/bin/perl; perl is at /data/service/hnp/bin/perl)

R28: test_package/ exists.
R32: settings.os check uses "in" not "==".
R34: test_package tests actual convmv functionality (encoding conversion).
R38: commands.json declared (command-line tool).
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ConvmvConan(ConanFile):
    name = "convmv"
    version = "2.06.1"
    description = "Converts filenames from one encoding to another"
    license = "GPL-2.0-only"
    homepage = "https://www.j3e.de/linux/convmv/"
    url = "https://www.j3e.de/linux/convmv/"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # convmv has no external dependencies (pure Perl script)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # convmv uses a simple Makefile: make generates manpage, no configure needed
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install convmv binary and man page
        self.run(
            f'make install DESTDIR="{self.package_folder}" '
            f'PREFIX="" MANDIR="/share/man"',
            cwd=self.source_folder
        )
        # Ensure the binary is executable
        bin_path = os.path.join(self.package_folder, "bin", "convmv")
        if os.path.isfile(bin_path):
            os.chmod(bin_path, os.stat(bin_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # Pure script project: no libraries, just executables in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
