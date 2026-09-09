#!/usr/bin/env python3
"""Conan recipe — libmad (MPEG audio decoder library).

OHOS PC (aarch64) adaptation:
  - Patch config.guess/config.sub for HarmonyOS platform detection
  - Patch configure: remove GCC-specific optimization flags unsupported by clang
  - Patch configure: fix HMDFS mktemp issue in config.status template
  - Patch mad.h: FPM_INTEL→FPM_DEFAULT, SIZEOF_LONG 4→8 for aarch64
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmadConan(ConanFile):
    name = "libmad"
    version = "0.15.1b"
    description = "MPEG audio decoder library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.underbit.com/products/mad/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_config_guess(self):
        """Patch config.guess and config.sub for HarmonyOS support."""
        cg = os.path.join(self.source_folder, "config.guess")
        cs = os.path.join(self.source_folder, "config.sub")

        if os.path.exists(cg):
            with open(cg, "r") as f:
                content = f.read()
            if "HarmonyOS" not in content:
                harmonyos_block = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "${UNAME_MACHINE}" in\n'
                    '\t    aarch64|arm64) echo aarch64-unknown-linux-gnu && exit 0 ;;\n'
                    '\t    armv7*|armv8*) echo arm-unknown-linux-gnu && exit 0 ;;\n'
                    '\t    x86_64|amd64) echo x86_64-unknown-linux-gnu && exit 0 ;;\n'
                    '\t    i?86) echo i686-unknown-linux-gnu && exit 0 ;;\n'
                    '\t    *) echo ${UNAME_MACHINE}-unknown-linux-gnu && exit 0 ;;\n'
                    '\tesac\n'
                    '\t;;\n\n'
                )
                if '    *:NetBSD:*:*)' in content:
                    content = content.replace(
                        '    *:NetBSD:*:*)',
                        harmonyos_block + '    *:NetBSD:*:*)',
                        1,
                    )
                    with open(cg, "w") as f:
                        f.write(content)

        if os.path.exists(cs):
            with open(cs, "r") as f:
                content = f.read()
            if "ohos" not in content.lower():
                if "gnu* | android*" in content:
                    content = content.replace(
                        "gnu* | android*",
                        "gnu* | android* | ohos*",
                    )
                if "linux-uclibc*)" in content:
                    content = content.replace(
                        "linux-uclibc*)",
                        "linux-uclibc* | linux-ohos*)",
                    )
                with open(cs, "w") as f:
                    f.write(content)

    def _patch_configure(self):
        """Patch configure: remove unsupported clang flags + fix HMDFS mktemp."""
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            return

        # Remove GCC-specific optimization flags unsupported by clang
        unsupported_flags = [
            '-fforce-mem',
            '-fforce-addr',
            '-fthread-jumps',
            '-fcse-follow-jumps',
            '-fcse-skip-blocks',
            '-fexpensive-optimizations',
            '-fregmove',
            '-fschedule-insns2',
        ]
        for flag in unsupported_flags:
            flag_line = '    optimize="$optimize {}"'.format(flag)
            try:
                replace_in_file(self, configure, flag_line + '\n', '')
            except Exception:
                pass

        # Fix HMDFS mktemp issue in config.status template
        try:
            replace_in_file(
                self,
                configure,
                'tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&',
                'tmp=./conftmp; mkdir -p $tmp;',
            )
        except Exception:
            pass

    def _patch_mad_h(self):
        """Patch mad.h for aarch64: FPM_DEFAULT and SIZEOF_LONG=8."""
        mad_h = os.path.join(self.source_folder, "mad.h")
        if os.path.exists(mad_h):
            replace_in_file(self, mad_h, "# define FPM_INTEL", "# define FPM_DEFAULT")
            replace_in_file(self, mad_h, "# define SIZEOF_LONG 4", "# define SIZEOF_LONG 8")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_guess()
        self._patch_configure()
        self._patch_mad_h()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mad"]
