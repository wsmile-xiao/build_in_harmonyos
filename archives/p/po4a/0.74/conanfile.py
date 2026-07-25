#!/usr/bin/env python3
"""Conan recipe for po4a 0.74.

po4a is a Perl-based documentation translation toolkit.  The upstream
distribution is mostly scripts plus Locale::Po4a modules, so this recipe
packages the runtime files directly and leaves heavyweight optional document
generation out of the package step.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Po4aConan(ConanFile):
    name = "po4a"
    version = "0.74"
    description = "Tools to ease translation of documentation and other materials"
    license = "GPL-2.0-or-later"
    homepage = "https://po4a.org/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run('perl -Ilib -c "po4a"', cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "*.pm",
            src=os.path.join(self.source_folder, "lib"),
            dst=os.path.join(self.package_folder, "lib", "perl5"),
            keep_path=True,
        )
        copy(
            self,
            "*.po",
            src=os.path.join(self.source_folder, "po", "bin"),
            dst=os.path.join(self.package_folder, "share", "po4a", "po"),
            keep_path=False,
        )
        copy(
            self,
            "po4a.pot",
            src=os.path.join(self.source_folder, "po", "bin"),
            dst=os.path.join(self.package_folder, "share", "po4a", "po"),
            keep_path=False,
        )

        scripts = [
            "po4a",
            "po4a-display-man",
            "po4a-display-pod",
            "po4a-gettextize",
            "po4a-normalize",
            "po4a-translate",
            "po4a-updatepo",
            "msguntypot",
        ]
        bin_dir = os.path.join(self.package_folder, "bin")
        for script in scripts:
            copy(self, script, src=self.source_folder, dst=bin_dir, keep_path=False)
            packaged = os.path.join(bin_dir, script)
            if os.path.exists(packaged):
                mode = os.stat(packaged).st_mode
                os.chmod(packaged, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
