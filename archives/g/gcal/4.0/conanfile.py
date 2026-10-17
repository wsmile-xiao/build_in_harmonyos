#!/usr/bin/env python3
"""Conan recipe for GNU gcal 4.0 — Gregorian calendar program (CLI tool).

Upstream is a classic GNU Autotools tree. The carried patch relaxes the
config.status `umask 077` that HMDFS cannot write (E011).

The bundled 2015-era build-aux/config.guess/config.sub do not know
HarmonyOS (`cannot guess build type`). Instead of carrying whole-file
replacement patches (~145 KB — it pushed the PR beyond the AI review size
limit), build() overwrites both helpers with the copies shipped by the
automake toolchain package (E007) and configure pins the build triplet so
config.guess is skipped entirely.

configure is invoked inline with CONFIG_SHELL=/bin/sh: the profile
buildenv injects the OHOS bash whose getcwd() fails on HMDFS (E386).
`gl_cv_have_weak=no` is required: the OHOS toolchain rejects gnulib's
`#pragma weak pthread_cancel` probe on symbols the musl headers do not
declare, so the non-weak pthread path must be selected at configure time.
NOTE: upstream version string is the single character "4"; Conan
requires package versions of at least two characters, so the conan
version is 4.0 (same semantics).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain


class GcalConan(ConanFile):
    name = "gcal"
    version = "4.0"
    description = ("GNU gcal: Gregorian calendar program computing and "
                   "printing calendar sheets on the command line")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gcal/"
    url = "https://ftp.gnu.org/gnu/gcal/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gcal is supported only on Linux/OHOS")

    def build_requirements(self):
        # E007: the config.guess/config.sub copies shipped by this package
        # recognise the ohos triplet, so build() can drop them in instead of
        # patching the bundled files line by line (keeps the PR diff small).
        self.tool_requires("automake/1.18")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # provides the conanbuild env (CC/CFLAGS/CPPFLAGS) consumed by
        # the inline configure/make below
        AutotoolsToolchain(self).generate()

    def _install_config_helpers(self):
        """E007: overwrite the bundled build-aux/config.guess/config.sub with
        the automake copies (whole-file content stays out of the PR diff)."""
        base = self.dependencies.build["automake"].package_folder
        for helper in ("config.guess", "config.sub"):
            matches = glob.glob(os.path.join(base, "**", helper), recursive=True)
            if not matches:
                raise ConanInvalidConfiguration(
                    "automake package does not ship %s" % helper)
            dst = os.path.join(self.source_folder, "build-aux", helper)
            shutil.copy2(sorted(matches, key=len)[0], dst)
            os.chmod(dst, 0o755)

    def build(self):
        apply_conandata_patches(self)
        self._install_config_helpers()
        # E386: pin the plain shell — the profile buildenv's OHOS bash
        # cannot getcwd() on HMDFS inside conan's build folders.
        configure = os.path.join(self.source_folder, "configure")
        self.run(
            f'CONFIG_SHELL=/bin/sh sh "{configure}" '
            f'--prefix="{self.package_folder}" '
            f"--build=aarch64-unknown-linux-ohos "
            f"--disable-nls gl_cv_have_weak=no",
            env="conanbuild")
        self.run("make -j1 MAKEINFO=true", env="conanbuild")

    def package(self):
        self.run("make install MAKEINFO=true", env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
