#!/usr/bin/env python3
"""Conan recipe for lcab 1.0b12 — create Microsoft cabinet (.cab) archives.

lcab is a small command-line tool (no library is produced).
Build system: pre-generated GNU autotools (configure + make) shipped in the
tarball; autoconf/automake are NOT required at build time.

Adaptation notes (OHOS):
- Pure POSIX C (stdio/dirent/sys/stat/unistd), no external dependency.
- Upstream ships mytypes.h with VERSION "1.0b11" although the release is
  1.0b12 -> patched (0001-mytypes.h.patch, same fix as Debian).
- Upstream Makefile.am installs the binary only; the man page lcab.1 is
  copied by package() instead of patching the build system.
- config.status creates its temporary directory with umask 077; on HMDFS that
  directory is not writable by the same process, so build() relaxes the umask
  and prefers TMPDIR (knowledge E011/E528).
"""
import os
import platform

from conan import ConanFile
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches, copy, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcabConan(ConanFile):
    name = "lcab"
    version = "1.0b12"
    description = "Command-line tool to create Microsoft cabinet (.cab) archives"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/lcab"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cab", "cabinet", "archiver", "microsoft")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS" and platform.machine() not in ("aarch64", "arm64"):
            # Only a real cross build needs --host: this legacy configure has no
            # AC_CANONICAL_HOST, so it enters cross mode solely through --host.
            # On an AArch64 OHOS runner the build is native and --host is wrong.
            tc.configure_args.append("--host=aarch64-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._relocate_config_status_tmpdir()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _relocate_config_status_tmpdir(self):
        """config.status must not build its temp dir with umask 077 on HMDFS.

        On HarmonyOS the build folder lives on HMDFS, where a 0700 directory
        created by config.status is not writable by the same process, so every
        generated file (subs.sed, Makefile, config.h) fails with
        "Permission denied" and make then finds no Makefile.
        """
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self, configure,
            '  tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&',
            '  tmp=`(umask 000 && mktemp -d -q "${TMPDIR:-.}/confstatXXXXXX") 2>/dev/null` &&',
        )
        replace_in_file(
            self, configure,
            '  tmp=./confstat$$-$RANDOM\n  (umask 077 && mkdir $tmp)',
            '  tmp=${TMPDIR:-.}/confstat$$-$RANDOM\n  (umask 000 && mkdir -p $tmp)',
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=f"{self.package_folder}/licenses")
        copy(self, "lcab.1", src=self.source_folder,
             dst=f"{self.package_folder}/share/man/man1")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
