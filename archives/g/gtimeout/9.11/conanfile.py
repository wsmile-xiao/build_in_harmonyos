#!/usr/bin/env python3
"""Conan recipe for gtimeout 9.11 — GNU coreutils timeout command.

gtimeout is the GNU coreutils `timeout` command with a `g` prefix
to distinguish it from the system-provided `timeout`.

Source: GNU coreutils 9.11 (https://ftp.gnu.org/gnu/coreutils/)

R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.

Patches (2 files, applied via conandata.yml):
  0001-build-aux-config.guess.patch  - HarmonyOS platform recognition in config.guess
  0002-lib-freadahead.c.patch        - musl libc opaque FILE adaptation
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    get, save, load, apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GtimeoutConan(ConanFile):
    name = "gtimeout"
    version = "9.11"
    description = "GNU coreutils timeout command — run a command with bounded time"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/coreutils/"
    url = "https://ftp.gnu.org/gnu/coreutils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gtimeout has no external dependencies
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gtimeout is only supported on Linux/OHOS, not " + str(self.settings.os)
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

        # Build - bypass missing autotools tools (automake/makeinfo not installed)
        autotools.make(args=[
            "-j2",
            "ACLOCAL=true",
            "AUTOMAKE=true",
            "AUTOCONF=true",
            "AUTOHEADER=true",
            "MAKEINFO=true",
        ])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=[
            "MAKEINFO=true",
            "ACLOCAL=true",
            "AUTOMAKE=true",
            "AUTOCONF=true",
            "AUTOHEADER=true",
        ])

        # Rename timeout to gtimeout
        bin_dir = os.path.join(self.package_folder, "bin")
        timeout_path = os.path.join(bin_dir, "timeout")
        gtimeout_path = os.path.join(bin_dir, "gtimeout")
        if os.path.exists(timeout_path):
            shutil.copy2(timeout_path, gtimeout_path)

    def package_info(self):
        # gtimeout is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure gtimeout binary is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
