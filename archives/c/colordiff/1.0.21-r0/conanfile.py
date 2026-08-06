#!/usr/bin/env python3
"""Conan recipe for colordiff — colourised diff wrapper (Perl script).

Perl script project, no compilation needed.
Installs colordiff/cdiff scripts, config file, and man pages.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ColordiffConan(ConanFile):
    name = "colordiff"
    version = "1.0.21-r0"
    description = "A Perl script wrapper for 'diff' producing colourised output"
    license = "GPL-2.0-or-later"
    homepage = "https://www.colordiff.org/"
    url = ""

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # colordiff is a Perl script — no compilation, just install files.
        # The upstream Makefile's install target runs sed to set ETC_DIR,
        # copies scripts/man pages/config. We replicate that here with copy().
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Install colordiff script (patched shebang: #!/usr/bin/env perl)
        copy(self, "colordiff.pl", src=self.source_folder, dst=bin_dir)
        # Rename colordiff.pl to colordiff
        os.rename(os.path.join(bin_dir, "colordiff.pl"),
                  os.path.join(bin_dir, "colordiff"))
        os.chmod(os.path.join(bin_dir, "colordiff"), 0o755)
        # Install cdiff wrapper
        copy(self, "cdiff.sh", src=self.source_folder, dst=bin_dir)
        os.rename(os.path.join(bin_dir, "cdiff.sh"),
                  os.path.join(bin_dir, "cdiff"))
        os.chmod(os.path.join(bin_dir, "cdiff"), 0o755)
        # Install config files
        etc_dir = os.path.join(self.package_folder, "etc")
        os.makedirs(etc_dir, exist_ok=True)
        copy(self, "colordiffrc", src=self.source_folder, dst=etc_dir)
        copy(self, "colordiffrc-lightbg", src=self.source_folder, dst=etc_dir)
        copy(self, "colordiffrc-gitdiff", src=self.source_folder, dst=etc_dir)
        # Install man pages
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "colordiff.1", src=self.source_folder, dst=man_dir)
        copy(self, "cdiff.1", src=self.source_folder, dst=man_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
