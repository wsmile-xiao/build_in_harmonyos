#!/usr/bin/env python3
"""Conan recipe for latex2html 2026 — Autotools project (Perl-based)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Latex2HtmlConan(ConanFile):
    name = "latex2html"
    version = "2026"
    description = "LaTeX2HTML — converts LaTeX documents to HTML"
    license = "GPL-2.0-or-later"
    homepage = "https://www.latex2html.org/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # latex2html requires in-source build (Makefile.in dependency)
        import os
        src = self.source_folder
        configure = os.path.join(src, "configure")
        os.chdir(src)
        self.run(f"perl {configure} --prefix=/", cwd=src)
        self.run("make -j1", cwd=src)

    def package(self):
        import os
        src = self.source_folder
        os.chdir(src)
        self.run("make install DESTDIR=" + self.package_folder, cwd=src)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []