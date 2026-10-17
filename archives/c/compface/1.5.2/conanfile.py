#!/usr/bin/env python3
"""Conan recipe for compface 1.5.2 — 48x48x1 image (X-Face) compressor.

compface ships a small C static library (libcompface + compface.h) and two
command-line tools (compface, uncompface) built by a 2005-era autoconf
configure. Real autoconf: the CC environment variable set by the Conan
AutotoolsToolchain is respected, no configure-argument workaround needed.

E011: the HMDFS filesystem cannot write into the `umask 077` temp dirs the
configure script creates, so the umask is relaxed to 022 via a source patch
(see patches/; validated repo knowledge E011/E114).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    copy,
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


class CompfaceConan(ConanFile):
    name = "compface"
    version = "1.5.2"
    description = "48x48x1 (X-Face) image compression and decompression tools and library"
    license = "MIT"  # per upstream README: MIT "captures the original author's intent"
    homepage = "https://ftp.xemacs.org/pub/xemacs/aux/"  # canonical (historic) upstream location
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # compface's 2005-era Makefile.in has no VPATH/srcdir support (plain
        # `cmain.o: cmain.c` rules), so the build must run in-source; Conan's
        # default out-of-source layout fails with "No rule to make target".
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # compface is a real autoconf configure that honours CC/CXX from the
        # environment; the toolchain provides them plus the build env files
        # (conanbuild.sh) that the Autotools helper requires.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream ships no automated test suite (no `check` target in
        # Makefile.in, no testsuite directory); functional verification is
        # provided by the consumer test in test_package/ instead.

    def package(self):
        # The 2005-era Makefile.in has no DESTDIR support, so `make install`
        # would bypass Conan's staging and write into the configure --prefix.
        # Mirror the upstream install rules manually instead (same approach
        # as other OHOS tool packages; also immune to a missing `install`
        # host tool on the worker).
        src = self.source_folder
        bld = self.build_folder
        copy(self, "compface", src=bld, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "uncompface", src=bld, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libcompface.a", src=bld, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "compface.h", src=src, dst=os.path.join(self.package_folder, "include"))
        copy(self, "compface.1", src=src, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "compface.3", src=src, dst=os.path.join(self.package_folder, "share", "man", "man3"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "licenses"))
        for exe in ("compface", "uncompface"):
            exe_path = os.path.join(self.package_folder, "bin", exe)
            if os.path.exists(exe_path):
                os.chmod(exe_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["compface"]
