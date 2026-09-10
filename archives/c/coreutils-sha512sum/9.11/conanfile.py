#!/usr/bin/env python3
"""Conan recipe for coreutils-sha512sum 9.11 — GNU sha512sum digest tool.

sha512sum is a single digest utility from GNU Coreutils 9.11. In 9.11 the
digest tools were refactored onto the cksum framework: src/sha512sum is
built from src/coreutils-sha512sum.c (wrapper setting cksum_algorithm=sha512)
plus src/cksum.c. Only the src/sha512sum make target is built and packaged.

R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.

Patches (2 files, applied via conandata.yml):
  0001-build-aux-config.guess.patch  - HarmonyOS platform recognition in config.guess
  0002-lib-freadahead.c.patch        - musl libc opaque FILE adaptation

Notes vs coreutils 9.10 full adaptation:
  - gnulib modules freadptr/freadseek were removed upstream in 9.11, so the
    9.10 patches 0003/0004 are obsolete and do not apply.
  - The fstat/lseek EACCES patches for cat/dd/head/od/sort/split/tail/wc
    (9.10 patches 0005-0012) target other commands; sha512sum's digest path
    only calls isatty() on stdin, so they are not needed here.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    get, save, load, copy, mkdir, apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CoreutilsSha512sumConan(ConanFile):
    name = "coreutils-sha512sum"
    version = "9.11"
    description = "GNU sha512sum digest tool (single utility from coreutils 9.11)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/coreutils/"
    url = "https://ftp.gnu.org/gnu/coreutils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # coreutils has no external dependencies
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "coreutils-sha512sum is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-fPIC")
        tc.generate()

    def _fix_umask(self, path):
        """Fix umask 077 in configure/config.status for HMDFS compatibility.

        On HarmonyOS HMDFS, umask 077 in mktemp/mkdir creates directories
        where file creation fails with EACCES. Replace umask 077 with umask 0.
        """
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def build(self):
        apply_conandata_patches(self)

        # Fix configure script: umask 077 breaks on HMDFS (E008/E046)
        configure_path = os.path.join(self.source_folder, "configure")
        self._fix_umask(configure_path)

        autotools = Autotools(self)
        # Run configure - config.status may fail due to umask 077 in
        # generated code on HMDFS. We catch only ConanException to handle
        # this known platform issue, then fix and re-run config.status.
        try:
            autotools.configure()
        except ConanException:
            pass

        # Fix config.status (generated file - cannot be a source patch)
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self._fix_umask(cs_path)
            self.run('cd "{}" && bash config.status'.format(self.build_folder))

        # Build the default `all` target (not a bare src/sha512sum target):
        # the `all` target lists BUILT_SOURCES, which generates gnulib headers
        # (stdckdint.h, stdcountof.h, locale.h, configmake.h, ...) required by
        # lib/libcoreutils.a and src/cksum.c. A direct `make src/sha512sum`
        # skips BUILT_SOURCES and fails with missing generated headers.
        # Bypass missing autotools tools (automake/makeinfo not installed).
        autotools.make(args=[
            "-j2",
            "ACLOCAL=true",
            "AUTOMAKE=true",
            "AUTOCONF=true",
            "AUTOHEADER=true",
            "MAKEINFO=true",
        ])

    def package(self):
        mkdir(self, os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "sha512sum",
            src=os.path.join(self.build_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

    def package_info(self):
        # command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure sha512sum is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
