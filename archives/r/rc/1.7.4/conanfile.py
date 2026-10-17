#!/usr/bin/env python3
"""Conan recipe — rc 1.7.4 (Plan 9 shell reimplemented for Unix).

rc is a reimplementation of the Plan 9 shell by Byron Rakitzis. The GitHub
archive lacks a pre-generated configure script, so autoreconf is run in
build() to generate it from configure.ac.

The autoconf-generated configure script uses `umask 077 && mktemp -d` to
create temporary directories. On the HarmonyOS build filesystem (HMDFS,
setgid-inherited), umask 077 produces drwx--S--- directories that are
unwritable, causing config.status to fail with "could not setup config
files machinery". This recipe fixes the umask calls via replace_in_file
after autoreconf generates configure (knowledge E081).

rc produces a single binary (bin/rc) and a man page (share/man/man1/rc.1).
It has no external runtime dependencies.

License: COPYING = Zlib ('as-is' license, per the COPYING file in the source tree).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, replace_in_file, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RcConan(ConanFile):
    name = "rc"
    version = "1.7.4"
    description = "rc - the Plan 9 shell, reimplemented for Unix by Byron Rakitzis"
    license = "Zlib"
    homepage = "https://github.com/rakitzis/rc"
    url = "https://github.com/rakitzis/rc"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    tool_requires = "automake/1.18"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rc supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS cross-build: pass canonical GNU triplet so AC_PROG_CC's
        # "does it compile and run a trivial program?" test is satisfied.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # GitHub archive lacks pre-generated configure; regenerate with autoreconf
        self.run("autoreconf --force --install", cwd=self.source_folder,
                 env="conanbuild")
        # Fix HMDFS SGID + umask 077 issue (E081): autoconf generates
        # `umask 077 && mktemp -d` which on HMDFS creates drwx--S---
        # directories that are unwritable. Remove umask 077 from the
        # generated configure script before running it.
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path,
                        "umask 077 && mktemp -d", "mktemp -d")
        replace_in_file(self, configure_path,
                        "umask 077 && mkdir", "mkdir")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
