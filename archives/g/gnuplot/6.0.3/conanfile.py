#!/usr/bin/env python3
"""Conan recipe for gnuplot 6.0.3 (autotools build).

gnuplot is a command-line interactive plotting tool.
This recipe builds gnuplot with zero external dependencies
(builtin readline, no gd/cairo/pango/lua/qt/wxwidgets).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnuplotConan(ConanFile):
    name = "gnuplot"
    version = "6.0.3"
    description = "Interactive plotting program that generates 2D and 3D plots"
    license = "gnuplot"
    homepage = "https://gnuplot.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        # Avoid config.guess HarmonyOS detection issue (E007)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # gnuplot-specific configure options for zero-dependency build
        tc.configure_args.append("--with-readline=builtin")
        tc.configure_args.append("--without-gd")
        tc.configure_args.append("--without-cairo")
        tc.configure_args.append("--without-lua")
        tc.configure_args.append("--without-qt")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
