#!/usr/bin/env python3
"""Conan recipe — mpegdemux 0.1.5 (MPEG1/MPEG2 system stream demultiplexer).

Upstream: http://www.hampa.ch/mpegdemux/
License:  GPL-2.0
Product:  single CLI binary `mpegdemux` (no libraries)

Build: autotools with a pre-generated `configure` (autoconf 2.71) and a
custom hand-written `Makefile.in` (not automake-generated). The tarball
already ships `configure`, so no autoreconf is needed. Zero patches.
"""
import os

from conan import ConanFile
from conan.tools.files import get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpegdemuxConan(ConanFile):
    name = "mpegdemux"
    version = "0.1.5"
    description = "MPEG1/MPEG2 system stream demultiplexer"
    license = "GPL-2.0"
    homepage = "http://www.hampa.ch/mpegdemux/index.html"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # mpegdemux is a self-contained C program with no external dependencies.
    def requirements(self):
        pass

    def build_requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # The tarball ships a pre-generated configure (autoconf 2.71),
        # so autoreconf is unnecessary.
        # E129: HMDFS umask 077 makes config.status create drwx--S--- temp
        # dirs, causing "can't create ./confXXXX/subs1.awk: Permission denied".
        # Fix the generated configure in-place (build-system file, not source).
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            content = load(self, configure_path)
            content = content.replace("umask 077", "umask 022")
            save(self, configure_path, content)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool: only bindirs, no libraries
        self.cpp_info.bindirs = ["bin"]
