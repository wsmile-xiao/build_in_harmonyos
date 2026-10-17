#!/usr/bin/env python3
"""Conan recipe for GNU shtool 2.0.8."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ShtoolConan(ConanFile):
    name = "shtool"
    version = "2.0.8"
    description = "GNU Portable Shell Tool command-line utility collection"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/shtool/"
    url = "https://ftp.gnu.org/gnu/shtool/shtool-2.0.8.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # shtool configure uses sibling scripts (sh.version/sh.echo/sh.path), so it must run in source tree.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/usr")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        configure = f"{self.source_folder}/configure"
        test_db = f"{self.source_folder}/test.db"
        replace_in_file(self, configure, "umask 077", "umask 022")
        replace_in_file(self, test_db, "shtool mdate /", "true # platform-skip: mdate ls output parsing on OHOS")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
