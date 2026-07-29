#!/usr/bin/env python3

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TimidityConan(ConanFile):
    name = "timidity"
    version = "2.13.2"
    description = "TiMidity++ - MIDI-to-WAVE converter and player"
    license = "GPL-2.0"
    homepage = "http://www.timidity.jp"
    url = "https://sourceforge.net/projects/timidity/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # TiMidity++ 2.13.2 (2004) relies on -fcommon semantics for tentative
        # definitions of global variables shared across translation units
        # (e.g. insertion_effect_gs, reverb_status_xg). Modern clang/ld.lld
        # default to -fno-common, causing duplicate-symbol link errors.
        tc.extra_cflags.append("-fcommon")
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--enable-audio=no")
        tc.configure_args.append("--disable-ncurses")
        tc.configure_args.append("--disable-slang")
        tc.configure_args.append("--disable-motif")
        tc.configure_args.append("--disable-tcltk")
        tc.configure_args.append("--disable-emacs")
        tc.configure_args.append("--disable-vt100")
        tc.configure_args.append("--disable-xaw")
        tc.configure_args.append("--disable-xskin")
        tc.configure_args.append("--disable-gtk")
        tc.configure_args.append("--enable-server=no")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
