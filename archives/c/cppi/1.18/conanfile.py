#!/usr/bin/env python3
"""Conan recipe for GNU cppi 1.18 — C preprocessor directive indenter.

Build system: autotools (configure + make).
cppi is a command-line tool that indents C preprocessor directives
(#if, #ifdef, #define, etc.) to reflect their nesting level.
Uses gnulib (bundled in source) and flex (build-time only).
"""
import os

from conan import ConanFile
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CppiConan(ConanFile):
    name = "cppi"
    version = "1.18"
    description = "GNU cppi — indent C preprocessor directives to reflect nesting"
    license = "GPL-3.0"
    homepage = "https://ftp.gnu.org/gnu/cppi/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        if self.settings.os in ("OHOS",):
            self._patch_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check")

    def _patch_ohos(self):
        # E165: fix shebang (/bin/sh does not exist on OHOS)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path, "#! /bin/sh", "#!/system/bin/sh")
        # E110: HMDFS umask 077 restricts temp file creation
        replace_in_file(self, configure_path, "umask 077", "umask 002")
        # E007: config.guess — add HarmonyOS detection before *:NetBSD:*:*)
        cg_path = os.path.join(self.source_folder, "build-aux", "config.guess")
        replace_in_file(self, cg_path,
            "    *:NetBSD:*:*)",
            '    *:HarmonyOS:*:*)\n'
            '\tcase "$UNAME_MACHINE" in\n'
            '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
            '\t    armv7*|armv8*) MACHINE=arm ;;\n'
            '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
            '\t    i?86)         MACHINE=i686 ;;\n'
            '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
            '\tesac\n'
            '\techo ${MACHINE}-unknown-linux-ohos\n'
            '\texit ;;\n\n'
            '    *:NetBSD:*:*)')
        # E007: config.sub — add ohos-linux triplet (after android-linux block)
        cs_path = os.path.join(self.source_folder, "build-aux", "config.sub")
        replace_in_file(self, cs_path,
            '  android-linux)\n'
            '    os=-linux-android\n'
            '    basic_machine=`echo $1 | sed \'s/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/\'`-unknown\n'
            '    ;;\n'
            '  *)',
            '  android-linux)\n'
            '    os=-linux-android\n'
            '    basic_machine=`echo $1 | sed \'s/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/\'`-unknown\n'
            '    ;;\n'
            '  ohos-linux)\n'
            '    os=-linux-ohos\n'
            '    basic_machine=`echo $1 | sed \'s/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/\'`-unknown\n'
            '    ;;\n'
            '  *)')
        # E007: config.sub — add linux-ohos* to KERNEL-OS validation
        replace_in_file(self, cs_path,
            'linux-musl* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu*',
            'linux-musl* | linux-ohos* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu*')
        # E007: config.sub — add -linux-ohos* to the kernel-OS list near end
        replace_in_file(self, cs_path,
            '| -mingw32* | -mingw64* | -linux-gnu* | -linux-android* \\',
            '| -mingw32* | -mingw64* | -linux-gnu* | -linux-android* | -linux-ohos* \\')

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
