#!/usr/bin/env python3
"""Conan recipe for basez 1.6.2 — base16/32/64 encode/decode CLI tool.

basez encodes and decodes using base16, base32, and base64 as described in
RFC 4648.  It is a single-binary CLI tool with optional symlinks for each
encoding variant.

Build system: custom ./configure script + Makefile.src.
  We bypass configure and generate config.h + Makefile directly from Python
  to avoid configure's tool-detection failures on CI workers.

License: GPL-3.0-or-later
Dependencies: none (pure C, only libc)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy


class BasezConan(ConanFile):
    name = "basez"
    version = "1.6.2"
    description = "base16/32/64 encode/decode data to standard output (RFC 4648)"
    license = "GPL-3.0-or-later"
    homepage = "https://codeberg.org/vonshedknocker/basez"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def build(self):
        # R33: Get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        if not os.path.isfile(cc):
            cc = "clang"

        # Bypass configure: generate config.h and Makefile directly.
        # This avoids configure's tool-detection (strip, ld, ranlib, help2man)
        # which fails on CI workers where those tools may not be in PATH.
        self._generate_config_h()
        self._generate_makefile(cc)

        # R9: Always use -j1, never -j$(nproc)
        self.run(f"make CC={cc} -j1")

        # Upstream regression test
        self.run("make test")

    def _generate_config_h(self):
        """Generate config.h from config.h.in by replacing placeholders."""
        config_h = os.path.join(self.source_folder, "config.h")
        with open(config_h, "w") as f:
            f.write('#define APPNAME "BaseZ"\n')
            f.write('#define VERSION "1.6.2"\n')
            f.write('#define PKGNAME "basez"\n')
            f.write('#define COPYRIGHT_YEARS "2013, 2015, 2016"\n')
            f.write('#define COPYRIGHT_NAMES "Milan Kupcevic"\n')
            f.write("#define TMCLAIM 0\n")
            f.write('#define TRADEMARKS ""\n')
            f.write('#define EMAIL "basez@quarkline.net"\n')
            f.write('#define WEB "www.quarkline.net/basez"\n')
            f.write('#define AUTHORS "Milan Kupcevic"\n')
            f.write("#define HAS_ORG 0\n")
            f.write('#define ORG ""\n')
            f.write("#define B32 1\n")
            f.write("#define B64 1\n")
            f.write("#define UNHEX 1\n")

    def _generate_makefile(self, cc):
        """Generate Makefile from Makefile.src by replacing @MACROS@.

        Bypasses configure to avoid tool-detection failures on CI.
        The configure script normally creates configure.options with variable
        definitions and replaces @INCLUDEOPTS@ with .include "configure.options".
        Here we inline all definitions directly at the top of the Makefile.
        """
        src = os.path.join(self.source_folder, "Makefile.src")
        dst = os.path.join(self.source_folder, "Makefile")
        with open(src, "r") as fin:
            content = fin.read()

        # Inline variable definitions (normally in configure.options)
        prefix = self.package_folder
        definitions = (
            f"CC = {cc}\n"
            f"CFLAGS = -O3\n"
            f"PREFIX = {prefix}\n"
            "BINDIR = $(PREFIX)/bin\n"
            "MANDIR = $(PREFIX)/share/man\n"
            "DOCDIR = $(PREFIX)/share/doc/basez\n"
            "DATADIR = $(PREFIX)/share\n"
            "DATAROOTDIR = $(PREFIX)/share\n"
            "EXECPREFIX = $(PREFIX)\n"
            "PKGNAME = basez\n"
            "APPNAME = BaseZ\n"
            "VER = 1.6.2\n"
            "VERSION = 1.6.2\n"
            "FULLNAME = BaseZ 1.6.2\n"
            "SDIR = .\n"
            "INSTALL = install\n"
            "STRIP = true\n"
            "B32 = 1\n"
            "B64 = 1\n"
            "UNHEX = 1\n"
            "B32CMD = base32\n"
            "B64CMD = base64\n"
            "UNHEXCMD = unhex\n"
            "COPYRIGHT_YEARS = 2013, 2015, 2016\n"
            "COPYRIGHT_NAMES = Milan Kupcevic\n"
            "AUTHORS = Milan Kupcevic\n"
            "EMAIL = basez@quarkline.net\n"
            "WEB = www.quarkline.net/basez\n"
            "TMCLAIM = 0\n"
            "HAS_ORG = 0\n"
            "ORG =\n"
            "TRADEMARKS =\n"
        )

        # @INCLUDEOPTS@ → inline definitions (no file include needed)
        content = content.replace("@INCLUDEOPTS@", definitions)
        # @INCLUDEDEPS@ → optional dependency include (ignore if missing)
        content = content.replace("@INCLUDEDEPS@", "-include .depend")
        # Conditional directives → standard Make
        content = content.replace("@IFNDEF@", "ifndef")
        content = content.replace("@IFDEF@", "ifdef")
        content = content.replace("@ENDIF@", "endif")
        content = content.replace("@ERROR@", "error")
        content = content.replace("@ELSE@", "else")
        # @SRCS@ → actual source file list
        content = content.replace(
            "@SRCS@", "basez.c base16.c base32.c base64.c"
        )

        with open(dst, "w") as fout:
            fout.write(content)

    def package(self):
        copy(self, "basez", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "basez.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # R7: Self-sign ELF binary on OHOS
        if self.settings.os == "OHOS":
            bin_path = os.path.join(self.package_folder, "bin", "basez")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(bin_path):
                signed_path = f"{bin_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{bin_path}"'
                    f' -outFile "{signed_path}"'
                    f" -selfSign 1 -signAlg SHA256withECDSA",
                    quiet=True,
                )
                if os.path.isfile(signed_path):
                    os.replace(signed_path, bin_path)
                    os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
