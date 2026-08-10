#!/usr/bin/env python3
"""Conan recipe — ncftp 3.3.0-r0 (FTP client suite).

NcFTP is a set of free application programs implementing the File Transfer
Protocol. It includes ncftp (interactive client), ncftpget, ncftpput,
ncftpls, ncftpbatch, ncftpspooler, and ncftpbookmarks (visual bookmark
editor using ncurses).

OHOS CI workers ship the ncurses runtime library (libncursesw.so.6) but NOT
the development headers/static archive, so ncurses headers and libncursesw.a
are bundled under res/ (same approach as nudoku/bitwise/mp3info recipes).

NcFTP uses old autoconf 2.13 which:
- Does NOT support VPATH (out-of-tree) builds
- Interprets VAR=value args as host types, so CC/CFLAGS must be env vars
- Does not search -I paths for header detection (needs config.h fix)
- clang needs TMPDIR set (E052: /tmp is read-only on OHOS)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NcftpConan(ConanFile):
    name = "ncftp"
    version = "3.3.0-r0"
    description = "A set of free application programs implementing FTP"
    license = "Clarified Artistic License"
    homepage = "https://www.ncftp.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Copy bundled ncurses headers/libs into source folder
        res_src = os.path.join(self.export_sources_folder, "res") \
            if hasattr(self, "export_sources_folder") and self.export_sources_folder \
            else os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Set environment variables for old autoconf 2.13 build.
        # E001: configure looks for 'cc' which doesn't exist on OHOS.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c", "clang")
        cxx = ce.get("cpp", "clang++")

        # E052: /tmp is read-only on OHOS, must set TMPDIR.
        # Use system TMPDIR if available, fallback to HOME/tmp.
        tmpdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # Locate bundled ncurses headers and lib
        res_headers = os.path.join(src, "res", "headers")
        res_libs = os.path.join(src, "res", "libs")

        cflags = "-D_REENTRANT -fPIC -O2"
        ldflags = ""
        if os.path.isdir(res_headers):
            cflags += f" -I{os.path.abspath(res_headers)}"
        if os.path.isdir(res_libs):
            ldflags += f" -L{os.path.abspath(res_libs)}"

        # Build env prefix for make commands
        env_prefix = f"CC={cc} CXX={cxx} CFLAGS=\"{cflags}\" LDFLAGS=\"{ldflags}\" TMPDIR={tmpdir} TMP={tmpdir} TEMP={tmpdir}"

        # NcFTP's old autoconf 2.13 does NOT support VPATH builds.
        # Run configure and make in the source folder directly.
        self.run(f'{env_prefix} ./configure --prefix=/', cwd=src)

        # Fix config.h: configure detects the ncurses library but fails to
        # set HAVE_CURSES_H because old autoconf 2.13 header check doesn't
        # search -I paths. Only replace if the pattern exists (CI workers
        # with ncurses dev headers may already have it defined).
        config_h = os.path.join(src, "config.h")
        if os.path.isfile(config_h):
            content = open(config_h).read()
            if "/* #undef HAVE_CURSES_H */" in content:
                replace_in_file(self, config_h,
                                "/* #undef HAVE_CURSES_H */",
                                "#define HAVE_CURSES_H 1")

        # Fix: HMDFS doesn't support hard links. Replace ln with cp for
        # ncftpspooler in the generated Makefile.
        makefile = os.path.join(src, "Makefile")
        if os.path.isfile(makefile):
            content = open(makefile).read()
            old1 = 'ln "$(DESTDIR)$(BINDIR)/ncftpbatch" "$(DESTDIR)$(BINDIR)/ncftpspooler"'
            new1 = 'cp "$(DESTDIR)$(BINDIR)/ncftpbatch" "$(DESTDIR)$(BINDIR)/ncftpspooler"'
            if old1 in content:
                replace_in_file(self, makefile, old1, new1)
            # Also fix the tar target
            old2 = 'ln "$(TMPDIR)/TAR/$(TARDIR)/bin/ncftpbatch" "$(TMPDIR)/TAR/$(TARDIR)/bin/ncftpspooler"'
            new2 = 'cp "$(TMPDIR)/TAR/$(TARDIR)/bin/ncftpbatch" "$(TMPDIR)/TAR/$(TARDIR)/bin/ncftpspooler"'
            if old2 in content:
                replace_in_file(self, makefile, old2, new2)

        self.run(f"make -j1 CC=\"{cc}\" CXX=\"{cxx}\" TMPDIR={tmpdir} TMP={tmpdir} TEMP={tmpdir}", cwd=src)

    def package(self):
        src = self.source_folder
        self.run(f'make install DESTDIR="{self.package_folder}"', cwd=src)

        # If ncftpspooler wasn't created (hard link failed), copy it
        spooler = os.path.join(self.package_folder, "bin", "ncftpspooler")
        batch = os.path.join(self.package_folder, "bin", "ncftpbatch")
        if not os.path.isfile(spooler) and os.path.isfile(batch):
            shutil.copy2(batch, spooler)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["ncftp"]
