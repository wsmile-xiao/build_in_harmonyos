#!/usr/bin/env python3
"""Conan recipe for cksfv 1.3.15 — Check SFV (checksum software verification) CLI tool.

cksfv creates and verifies SFV (Sum File Verification) checksum listings using CRC32.
It is a pure C autotools project with no external dependencies.

Platform adaptations (OHOS):
  - configure requires --compiler=aarch64-unknown-linux-ohos-clang so src/config.h
    picks up the correct compiler.  The shipped configure detects clang but defaults
    to "gcc" and emits GNU-make-style flags that clash with OHOS clang.
  - make install uses the POSIX `install` command which is absent from the OHOS
    Conan build PATH.  Override package() to copy files manually with conan's copy().
  - Conan maps arch=armv8, but the OHOS clang triplet is aarch64-unknown-linux-ohos.
  - cksfv configure generates Makefile in the current directory; Conan chdirs to
    build_folder before build().  We chdir back to source_folder before configure/make.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CksfvConan(ConanFile):
    name = "cksfv"
    version = "1.3.15"
    description = "Check SFV — create and verify SFV checksum listings (CRC32)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/heikkiorsila/cksfv"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def requirements(self):
        pass  # no external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS cross-compile: tell configure to use the OHOS clang triplet.
        # Without this, configure assumes gcc and emits incompatible flags.
        tc.extra_cflags.append("-D_FILE_OFFSET_BITS=64")
        tc.extra_cflags.append("-D_LARGEFILE64_SOURCE")
        tc.generate()

    def _ohos_compiler_triple(self):
        """Return the OHOS clang triplet matching the target arch."""
        arch_map = {"armv8": "aarch64", "armv7": "arm"}
        base = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        return f"{base}-unknown-linux-ohos-clang"

    def build(self):
        # Conan's build pipeline chdirs to build_folder before calling build().
        # cksfv's configure script generates Makefile and src/config.h in the
        # current working directory, so we must run from source_folder where
        # Makefile.in and src/*.c exist.
        bf = self.build_folder
        sf = self.source_folder
        if os.path.isdir(bf):
            os.chdir(bf)
            os.environ["PWD"] = bf
        if os.path.isdir(sf):
            os.chdir(sf)
            os.environ["PWD"] = sf
        compiler = self._ohos_compiler_triple()
        autotools = Autotools(self)
        autotools.configure(
            args=[
                f"--prefix={self.package_folder}",
                f"--compiler={compiler}",
            ],
        )
        autotools.make(args=["-j1"])

    def package(self):
        # Binary built in source_folder/src/ (make runs from there)
        copy(self, "cksfv",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # Man page
        copy(self, "cksfv.1",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        # License
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
