#!/usr/bin/env python3
"""Conan recipe for mutt 2.4.1 — autotools-based mail client.

R26: ncurses is a system-name library, forced static.
R32: settings.os check uses standard Conan settings
R33: build() does not depend on undefined shell variables
R34: test_package runs mutt binary
R38: commands.json declared (CLI tool)

Note: Patches are applied inline in build() because export_conandata_patches
creates a patches/ directory that conflicts with mutt's PATCHES file on HMDFS
(case-insensitive path resolution). Patch files in patches/ are kept for reference.
"""
import os
from conan import ConanFile
from conan.tools.files import get, replace_in_file, save, load
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MuttConan(ConanFile):
    name = "mutt"
    version = "2.4.1"
    description = "Mutt is a small but very powerful text-based mail client"
    license = "GPL-2.0-or-later"
    homepage = "http://www.mutt.org"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("ncurses/6.5")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def configure(self):
        # R26: ncurses is a system-name library, must be static
        self.options["ncurses"].shared = False

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Explicitly add dependency include and lib paths for autotools
        inc_flags = []
        lib_flags = []
        for dep_name in ["ncurses", "openssl"]:
            dep = self.dependencies[dep_name]
            pkg_folder = dep.package_folder
            inc_flags.append(f"-I{pkg_folder}/include")
            lib_flags.append(f"-L{pkg_folder}/lib")
        tc.extra_cflags = inc_flags
        tc.extra_ldflags = lib_flags

        tc.configure_args.extend([
            "--enable-imap",
            "--enable-pop",
            "--enable-smtp",
            "--enable-sidebar",
            "--with-ssl",
            "--with-curses",
            "--with-homespool=Mail",
            "--with-mailpath=/var/mail",
        ])

        # OHOS: no /bin/sh, use /system/bin/sh for shell commands
        if self.settings.os == "OHOS":
            tc.configure_args.append("--with-exec-shell=/system/bin/sh")

        tc.generate()

    def build(self):
        # OHOS-specific platform patches
        if self.settings.os == "OHOS":
            # E007: Patch config.guess for HarmonyOS detection
            cg = os.path.join(self.source_folder, "config.guess")
            content = load(self, cg)
            if "__OHOS__" not in content:
                content = content.replace(
                    '#if defined(__ANDROID__)\n\tLIBC=android',
                    '#if defined(__ANDROID__)\n\tLIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos'
                )
                content = content.replace(
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in',
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n    *:HarmonyOS:*:*)\n\tcase "$UNAME_MACHINE" in\n\t    aarch64|arm64) MACHINE=aarch64 ;;\n\t    armv7*|armv8*) MACHINE=arm ;;\n\t    x86_64|amd64)  MACHINE=x86_64 ;;\n\t    i?86)         MACHINE=i686 ;;\n\t    *)            MACHINE="$UNAME_MACHINE" ;;\n\tesac\n\tGUESS=${MACHINE}-unknown-linux-ohos\n\t;;\n'
                )
                save(self, cg, content)

            # E007: Patch config.sub for ohos-linux triplet
            cs = os.path.join(self.source_folder, "config.sub")
            content = load(self, cs)
            if "ohos-linux" not in content:
                content = content.replace(
                    'basic_os=linux-android\n\t\t\t;;',
                    'basic_os=linux-android\n\t\t\t;;\n\tohos-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-ohos\n\t\t\t;;')
            if "ohos-linux" not in content:
                content = content.replace(
                    'basic_os=linux-android\n\t\t\t\t;;',
                    'basic_os=linux-android\n\t\t\t\t;;\n\tohos-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-ohos\n\t\t\t\t;;')
            save(self, cs, content)

            # Fix umask 077 causing HMDFS permission errors
            configure = os.path.join(self.source_folder, "configure")
            replace_in_file(self, configure, "umask 077", "umask 022")

            # Fix check_sec.sh /tmp to TMPDIR (E002)
            check_sec = os.path.join(self.source_folder, "check_sec.sh")
            if os.path.exists(check_sec):
                replace_in_file(self, check_sec, "mktemp -p /tmp", 'mktemp -p ${TMPDIR:-/tmp}')

            # Fix shebangs for OHOS (no /bin/sh on HarmonyOS)
            for f in ["configure", "install-sh", "missing", "compile", "depcomp", "config.rpath"]:
                fpath = os.path.join(self.source_folder, f)
                if os.path.exists(fpath):
                    replace_in_file(self, fpath, "#!/bin/sh", "#!/system/bin/sh", strict=False)
                    replace_in_file(self, fpath, "#! /bin/sh", "#!/system/bin/sh", strict=False)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
