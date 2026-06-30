#!/usr/bin/env python3
"""Conan recipe — gnu-barcode 0.99 (Autotools).

Convert text strings to printed bars.
R26: static linking for terminal tools.
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, replace_in_file, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GnubarcodeConan(ConanFile):
    name = "gnu-barcode"
    version = "0.99"
    description = "Convert text strings to printed bars"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/barcode/"
    url = ""  # CI fills this

    settings = "os", "compiler", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail. Create a mktemp wrapper that fixes perms.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF)
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.extra_ldflags.append("-static")
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def _patch_config_guess(self):
        """Patch build-aux/config.guess for HarmonyOS support."""
        f = Path(self.source_folder) / "build-aux" / "config.guess"
        content = f.read_text()
        harmonyos_block = (
            '    *:HarmonyOS:*:*)\n'
            '\tcase "$UNAME_MACHINE" in\n'
            '\t    aarch64|arm64) echo aarch64-unknown-linux-ohos; exit ;;\n'
            '\t    armv7*|armv8*) echo arm-unknown-linux-ohos; exit ;;\n'
            '\t    x86_64|amd64)  echo x86_64-unknown-linux-ohos; exit ;;\n'
            '\t    i?86)          echo i686-unknown-linux-ohos; exit ;;\n'
            '\t    *)             echo ${UNAME_MACHINE}-unknown-linux-ohos; exit ;;\n'
            '\tesac\n'
            '\t;;\n'
        )
        # Insert before the NetBSD case
        marker = '    *:NetBSD:*:*)'
        if 'HarmonyOS' not in content:
            content = content.replace(marker, harmonyos_block + marker)
            f.write_text(content)
            self.output.info("Patched config.guess for HarmonyOS")

    def _patch_config_sub(self):
        """Patch build-aux/config.sub for HarmonyOS support."""
        f = Path(self.source_folder) / "build-aux" / "config.sub"
        content = f.read_text()

        # 1. Add linux-ohos* to maybe_os list
        if 'linux-ohos*' not in content:
            content = content.replace(
                'nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* |',
                'nto-qnx* | linux-gnu* | linux-android* | linux-ohos* | linux-dietlibc | linux-newlib* |'
            )
            content = content.replace(
                'linux-musl* | linux-uclibc* | uclinux-uclibc*',
                'linux-musl* | linux-uclibc* | linux-ohos* | uclinux-uclibc*'
            )

            # 2. Add ohos-linux case after android-linux block
            old_block = (
                '  android-linux)\n'
                '    os=-linux-android\n'
                "    basic_machine=`echo $1 | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown\n"
                '    ;;\n'
                '  *)'
            )
            new_block = (
                '  android-linux)\n'
                '    os=-linux-android\n'
                "    basic_machine=`echo $1 | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown\n"
                '    ;;\n'
                '  ohos-linux)\n'
                '    os=-linux-ohos\n'
                "    basic_machine=`echo $1 | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown\n"
                '    ;;\n'
                '  *)'
            )
            content = content.replace(old_block, new_block)

            # 3. Add -linux-ohos* to kernel list
            content = content.replace(
                '| -mingw32* | -mingw64* | -linux-gnu* | -linux-android* \\',
                '| -mingw32* | -mingw64* | -linux-gnu* | -linux-android* | -linux-ohos* \\'
            )
            content = content.replace(
                '| -linux-uclibc* \\',
                '| -linux-uclibc* | -linux-ohos* \\'
            )
            f.write_text(content)
            self.output.info("Patched config.sub for HarmonyOS")

    def _patch_umask(self):
        """Fix umask 077 -> 022 in configure and config.status.

        HarmonyOS creates temp dirs with restrictive permissions (drwx--S---)
        due to MAC. The default umask 077 in autotools-generated scripts makes
        subdirectories unreadable, causing 'Permission denied' when config.status
        tries to access generated awk scripts.
        """
        for fname in ("configure", "config.status"):
            f = Path(self.source_folder) / fname
            if f.exists():
                content = f.read_text()
                content = content.replace("umask 077", "umask 022")
                f.write_text(content)
        self.output.info("Patched umask 077 -> 022 in configure and config.status")

    def _patch_source_fixes(self):
        """Fix duplicate streaming symbol, sample linking, and include paths."""
        # 1. barcode.h: change 'int streaming;' to 'extern int streaming;'
        f = Path(self.source_folder) / "barcode.h"
        content = f.read_text()
        if 'extern int streaming;' not in content:
            content = content.replace('int streaming;', 'extern int streaming;')
            f.write_text(content)

        # 2. library.c: add 'int streaming;' definition
        f = Path(self.source_folder) / "library.c"
        content = f.read_text()
        if '\nint streaming;\n' not in content:
            content = content.replace(
                '#include <ctype.h>\n',
                '#include <ctype.h>\nint streaming;\n'
            )
            f.write_text(content)

        # 3. Makefile.in: fix sample_LDADD and include path for VPATH builds
        f = Path(self.source_folder) / "Makefile.in"
        content = f.read_text()
        if 'libbarcode.la lib/libgnu.la' not in content.split('sample_LDADD')[1].split('\n')[0]:
            content = content.replace(
                'sample_LDADD = libbarcode.la\n',
                'sample_LDADD = libbarcode.la lib/libgnu.la\n'
            )
        # Fix -Ilib to -I$(srcdir)/lib for VPATH build support
        content = content.replace(
            'AM_CFLAGS = -Ilib @CFLAGS@',
            'AM_CFLAGS = -I$(srcdir)/lib @CFLAGS@'
        )
        f.write_text(content)

        # 4. Makefile.am: same fixes
        f = Path(self.source_folder) / "Makefile.am"
        content = f.read_text()
        if 'libbarcode.la lib/libgnu.la' not in content.split('sample_LDADD')[1].split('\n')[0]:
            content = content.replace(
                'sample_LDADD = libbarcode.la\n',
                'sample_LDADD = libbarcode.la lib/libgnu.la\n'
            )
        content = content.replace(
            'AM_CFLAGS = -Ilib @CFLAGS@',
            'AM_CFLAGS = -I$(srcdir)/lib @CFLAGS@'
        )
        f.write_text(content)

        # 5. Makefile.in: fix include path for VPATH builds
        f = Path(self.source_folder) / "Makefile.in"
        content = f.read_text()
        content = content.replace(
            'AM_CFLAGS = -Ilib @CFLAGS@',
            'AM_CFLAGS = -I$(srcdir)/lib @CFLAGS@'
        )
        f.write_text(content)

        self.output.info("Applied source code fixes (streaming symbol + linking + include paths)")

    def build(self):
        # Apply conandata patches (if any)
        apply_conandata_patches(self)
        # Apply patches manually for reliability
        self._patch_config_guess()
        self._patch_config_sub()
        self._patch_umask()
        self._patch_source_fixes()

        autotools = Autotools(self)
        autotools.configure()
        # Use -j1: HarmonyOS forbids mkfifo (jobserver FIFO) in TMPDIR
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # Use -j1: HarmonyOS forbids mkfifo (jobserver FIFO) in TMPDIR
        autotools.install(args=["-j1"])

        # libbarcode is noinst_LTLIBRARIES (not installed by make install)
        # Manually copy the static library and header
        copy(self, "libbarcode.a", src=Path(self.build_folder) / ".libs",
             dst=Path(self.package_folder) / "lib")
        copy(self, "barcode.h", src=self.source_folder,
             dst=Path(self.package_folder) / "include")

    def package_info(self):
        self.cpp_info.libs = ["barcode"]
