#!/usr/bin/env python3
"""Conan recipe — pv 1.7.24 (Autotools).

pv is a terminal-based tool that shows the progress of data through a pipe.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PvConan(ConanFile):
    name = "pv"
    version = "1.7.24"
    description = "Pipe Viewer - terminal-based tool to monitor data through pipelines"
    license = "Artistic-2.0"
    homepage = "https://github.com/a-j-wood/pv"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        with chdir(self, src):
            # Generate configure from autoconf (source tarball doesn't ship pre-generated)
            self.run("autoconf autoconf/configure.in > configure")
            self.run("chmod 755 configure")
            # E011: HMDFS umask 077 prevents temp dir creation during configure
            self.run("sed -i 's/umask 077/umask 022/g' configure")
            # Create empty Makefile fragment files needed by configure
            for f in ["filelist.mk~", "depend.mk~", "modules.mk~"]:
                self.run(f"echo > autoconf/make/{f}")
        autotools = Autotools(self)
        autotools.configure()
        # pv build system requires regenerating Makefile fragments and dependencies
        autotools.make(target="make")
        autotools.make(target="dep")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
