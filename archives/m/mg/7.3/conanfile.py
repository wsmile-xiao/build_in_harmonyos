#!/usr/bin/env python3
"""Conan recipe for mg (micro GNU emacs) 7.3 — an Emacs-like text editor."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MgConan(ConanFile):
    name = "mg"
    version = "7.3"
    description = "mg (micro GNU emacs) — a lightweight Emacs-like text editor from OpenBSD"
    license = "MIT"
    homepage = "https://github.com/ibara/mg"
    url = "https://github.com/ibara/mg/releases/download/mg-7.3/mg-7.3.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-builtin-curses")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # mg's configure uses sed with relative file paths, requiring in-tree build
        self.run("./configure --prefix=/ --with-builtin-curses",
                 env="conanbuild", cwd=self.source_folder)
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder),
                 env="conanbuild", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
