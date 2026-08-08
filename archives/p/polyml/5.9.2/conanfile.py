#!/usr/bin/env python3
"""Conan recipe for Poly/ML 5.9.2."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PolymlConan(ConanFile):
    name = "polyml"
    version = "5.9.2"
    description = "Poly/ML implementation of Standard ML"
    license = "LGPL-2.1-or-later"
    homepage = "https://polyml.org/"
    url = "https://github.com/polyml/polyml"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
            "--without-gmp",
            "--without-x",
        ])
        tc.generate()

    def build(self):
        # Regenerate configure from the patched configure.ac (R6).  autoreconf
        # refreshes config.guess/sub, so preserve the already patched copies.
        guess = os.path.join(self.source_folder, "config.guess")
        sub = os.path.join(self.source_folder, "config.sub")
        guess_data = open(guess, "rb").read()
        sub_data = open(sub, "rb").read()
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        open(guess, "wb").write(guess_data)
        open(sub, "wb").write(sub_data)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        # Upstream installs libpolyml/libpolymain plus polyml.pc as its
        # supported run-time/main-program library contract.  Static consumers
        # need the main-program archive before the run-time archive.
        self.cpp_info.libs = ["polymain", "polyml"]
        self.cpp_info.system_libs = ["stdc++"]
        # Upstream installs no public headers; the documented run-time entry
        # points are C symbols, so do not expose Conan's default include path.
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
