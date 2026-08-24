#!/usr/bin/env python3
"""Conan recipe — catdoc 0.94.2

catdoc reads MS-Word binary files (.doc) and prints readable ASCII text to
stdout.  Companion tools xls2csv and catppt handle Excel (.xls) and
PowerPoint (.ppt) files respectively.

Build system: Autoconf + hand-written Makefile.in (no automake).
License: GPL-2.0-only
Source: petewarden/catdoc on GitHub (pinned to commit 37af16c2).

OHOS adaptations:
  - --disable-wordview (no Tcl/Tk dependency; wordview is a Tk GUI wrapper).
  - --disable-charset-check (charset files are shipped but cross-compiled
    environment cannot verify default charset presence at configure time).
  - --prefix=/ so that CHARSETPATH embeds /share/catdoc and installroot
    redirects installation to package_folder correctly.
  - CFLAGS=-O0 — clang-15 on OHOS aarch64 miscompiles fileutil.c at -O1+,
    causing SIGSEGV before main().  Verified: -O0 works, -O1/-O2/-Og crash.
    Root cause: fileutil.c (glob/path handling) triggers a codegen bug in
    the clang-15 OHOS toolchain when optimization is enabled.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CatdocConan(ConanFile):
    name = "catdoc"
    version = "0.94.2"
    description = "Extract plain text from MS Word/Excel/PowerPoint files"
    license = "GPL-2.0-only"
    homepage = "https://github.com/petewarden/catdoc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-wordview",
            "--disable-charset-check",
            "--with-output=utf-8",
            # --prefix=/ so CHARSETPATH compiles to /share/catdoc;
            # installroot in make install redirects to package_folder.
            "--prefix=/",
        ])
        # R8: clang-15 on OHOS aarch64 miscompiles fileutil.c at -O1+,
        # causing SIGSEGV before main().  Force -O0.
        # R9: legacy C code emits many warnings; suppress errors.
        tc.extra_cflags = [
            "-O0",
            "-Wno-error=implicit-function-declaration",
            "-Wno-error=implicit-int",
            "-Wno-error=int-conversion",
            "-Wno-error=incompatible-pointer-types",
            "-Wno-error=return-mismatch",
            "-Wno-error=return-type",
            "-Wno-error=uninitialized",
        ]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R8: clang-15 on OHOS aarch64 miscompiles fileutil.c at -O1+,
        # causing SIGSEGV before main().  Force -O0 in configure script.
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            cfg = f.read()
        cfg = cfg.replace('"-g -O2"', '"-g -O0"')
        cfg = cfg.replace('"-O2"', '"-O0"')
        cfg = cfg.replace('"-g -O2 -Wall"', '"-g -O0 -Wall"')
        with open(configure_path, "w") as f:
            f.write(cfg)
        self.output.info("Patched configure: all -O2 -> -O0")
        # Copy helper scripts to build dir (Makefile uses ../mkinstalldirs
        # from subdirs, so they must be at the build-release/ level)
        for script in ("mkinstalldirs", "install-sh", "missing"):
            src = os.path.join(self.source_folder, script)
            if os.path.isfile(src):
                copy(self, script, src=self.source_folder,
                     dst=self.build_folder)
        autotools = Autotools(self)
        autotools.configure()
        # R9: old hand-written Makefile, single-threaded build is safest
        autotools.make(args=["-j1"])

    def package(self):
        # Install binaries
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for binary in ("catdoc", "xls2csv", "catppt"):
            src = os.path.join(self.build_folder, "src", binary)
            copy(self, binary, src=os.path.dirname(src), dst=bindir)
            # Ensure executable permissions (copy may not preserve them)
            dst = os.path.join(bindir, binary)
            if os.path.isfile(dst):
                os.chmod(dst, 0o755)

        # Install charset data files
        share_catdoc = os.path.join(self.package_folder, "share", "catdoc")
        os.makedirs(share_catdoc, exist_ok=True)
        charset_src = os.path.join(self.source_folder, "charsets")
        for fn in os.listdir(charset_src):
            if fn.endswith((".txt", ".spc", ".rpl")):
                copy(self, fn, src=charset_src, dst=share_catdoc)

        # Install man pages (optional, but nice to have)
        man1dir = os.path.join(self.package_folder, "man", "man1")
        os.makedirs(man1dir, exist_ok=True)
        for manpage in ("catdoc.1", "xls2csv.1", "catppt.1"):
            src = os.path.join(self.build_folder, "doc", manpage)
            if os.path.isfile(src):
                copy(self, manpage, src=os.path.dirname(src), dst=man1dir)

    def package_info(self):
        # Command-line tools, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
