#!/usr/bin/env python3
"""Conan recipe — gpx 2.6.8 (Autotools).

GPX is a G-code parser/translator for 3D printing (MakerBot/RepRap).
Produces terminal tools: gpx, s3gdump, machines.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GpxConan(ConanFile):
    name = "gpx"
    version = "2.6.8"
    description = "G-code parser/translator for 3D printing (MakerBot/RepRap)"
    license = "GPL-2.0"
    homepage = "https://github.com/markwal/GPX"
    url = ""

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
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix 1: Replace outdated config.guess/config.sub (2014 -> supports ohos)
        build_aux = os.path.join(self.source_folder, "build-aux")
        automake_share = os.path.join(os.path.expanduser("~"), "usr", "local", "share", "automake-1.16")
        for fname in ("config.guess", "config.sub"):
            src = os.path.join(automake_share, fname)
            dst = os.path.join(build_aux, fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                self.output.info(f"Replaced {fname} with automake version")

        # Fix 2: Patch configure to use umask 022 (HMDFS can't write in 0700 dirs)
        # and use $TMPDIR for mktemp instead of current directory
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            content = content.replace('mktemp -d "./confXXXXXX"',
                                      'mktemp -d "$TMPDIR/confXXXXXX"')
            content = content.replace('tmp=./conf$$-$RANDOM',
                                      'tmp=$TMPDIR/conf$$-$RANDOM')
            with open(configure_path, "w") as f:
                f.write(content)
            self.output.info("Patched configure: umask 077->022, mktemp->TMPDIR")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gpx is a terminal tool package — no shared libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Bindir is automatically set by Conan based on layout
