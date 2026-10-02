#!/usr/bin/env python3
"""Conan recipe for hamlib 4.7.1 — amateur radio rig/rotator/amp control library.

Upstream: https://github.com/Hamlib/Hamlib (LGPL-2.1-or-later), autotools.
Source used: official release tarball (contains a pre-generated `configure`,
so no autoreconf/bootstrap is needed on the CI runner).

OHOS (HarmonyOS PC aarch64) adaptations:
  - patches/0001: pthread_cancel() shim for musl libc
  - patches/0002: <linux/wireless.h> guarded by libc probe (uapi vs musl clash)
  - patches/0003: E007 config.guess HarmonyOS triplet (config.sub already ok)
  - patches/0004: upstream rmode_t typo (mode_t leaked by glibc only)
  - patches/0005: E114 HMDFS `umask 077` temp dir in generated configure
  - in-recipe E490 helper: restore autotools execute bits
Optional dependencies (libusb, readline) are disabled: they are not published
on ohpcd and are not required by the rigctl/rigctld use cases.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import stat


class HamlibConan(ConanFile):
    name = "hamlib"
    version = "4.7.1"
    description = "Amateur radio rig/rotator/amplifier control library (libhamlib + rigctl/rotctl tools)"
    license = "LGPL-2.1-or-later"
    homepage = "https://hamlib.github.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os gate
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"hamlib is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Optional features whose dependencies are not published on ohpcd;
        # neither is needed by the rigctl/rigctld CLI paths.
        tc.configure_args.append("--without-libusb")
        tc.configure_args.append("--without-readline")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: HMDFS / packaging may drop the POSIX execute bit of autotools
        # helper scripts -> configure aborts with Permission denied.
        self._restore_exec_bits()
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job (parallel make hits the HMDFS jobserver fifo, E074)
        autotools.make(args=["-j1"])
        # R51: run the upstream test suite (tests/Makefile.am TESTS =
        # amptest.sh test2038.sh testbcd.sh testcache.sh testcaps.sh
        # testcookie.sh testfreq.sh testgrid.sh testloc.sh testrig.sh
        # testrigcaps.sh -> 11/11 PASS on the HarmonyOS PC runner)
        autotools.make(target="check", args=["-j1"])

    def _restore_exec_bits(self):
        """E490: restore +x on known autotools helper scripts."""
        helpers = (
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "compile", "depcomp", "ltmain.sh", "ar-lib",
            "test-driver", "ylwrap", "mkinstalldirs",
        )
        roots = {
            self.source_folder,
            os.path.join(self.source_folder, "build-aux"),
            self.build_folder,
            os.path.join(self.build_folder, "build-aux"),
        }
        for root in roots:
            for name in helpers:
                path = os.path.join(root, name)
                if os.path.isfile(path):
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["hamlib"]
        # The package also ships the upstream CLI tools (rigctl, rigctld,
        # rotctl, rotctld, ampctl, ampctld, rigmem, rigsmtr, rigswr, ...)
        # -> R38 commands.json is declared at the software level.
        self.cpp_info.bindirs = ["bin"]
