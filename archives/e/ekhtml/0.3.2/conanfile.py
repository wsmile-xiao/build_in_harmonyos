#!/usr/bin/env python3
"""Conan recipe — ekhtml 0.3.2 (Autotools, BSD-2-Clause).

ekhtml is an El-Kabong HTML parser library written in C.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EkhtmlConan(ConanFile):
    name = "ekhtml"
    version = "0.3.2"
    description = "El-Kabong HTML parser library - a fast, lightweight HTML parsing library in C"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/ekhtml/"
    url = ""  # CI fills this

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
        # R26: Static linking for libraries on HarmonyOS
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Fix: Update config.guess/config.sub for HarmonyOS platform detection (E007)
        am_share = os.path.join(os.path.expanduser("~"), "usr", "local", "share", "automake-1.16")
        for fn in ("config.guess", "config.sub"):
            src_f = os.path.join(am_share, fn)
            dst_f = os.path.join(src, fn)
            if os.path.isfile(src_f):
                shutil.copy2(src_f, dst_f)
                os.chmod(dst_f, 0o755)

        # Fix: Remove umask 077 in configure (HarmonyOS HMDFS blocks 0700 dirs)
        configure_path = os.path.join(src, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077 && mktemp -d", "mktemp -d")
            content = content.replace("umask 077 && mkdir", "mkdir")
            with open(configure_path, "w") as f:
                f.write(content)

        # In-source build: ekhtml's old Makefile uses -I../include relative paths
        # that break with out-of-source builds
        self.run("chmod +x configure && ./configure --prefix=/ "
                 "--bindir=${prefix}/bin --sbindir=${prefix}/bin "
                 "--libdir=${prefix}/lib --includedir=${prefix}/include",
                 cwd=src)
        self.run("make -j1", cwd=src)

    def package(self):
        src = self.source_folder
        self.run("make install DESTDIR={}".format(self.package_folder), cwd=src)

    def package_info(self):
        self.cpp_info.libs = ["ekhtml"]
