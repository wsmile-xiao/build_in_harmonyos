#!/usr/bin/env python3
"""Conan recipe — logrotate 3.22.0 (log file rotation utility).

Build system: autotools (release tarball ships a pre-generated ./configure).
Source: https://github.com/logrotate/logrotate

Adaptation notes:
  * logrotate hard-requires libpopt (configure.ac aborts without it). libpopt is
    not yet in the artifact registry, so it is vendored from conandata.yml and
    statically linked into the logrotate binary — no runtime dependency on
    libpopt.so, the tool only links against libc.
  * SELinux / ACL support is optional (configure "check" mode) and stays off,
    since neither library is available on the target.

Rules compliance:
  R1:  Minimal configure args (prefix handled by AutotoolsToolchain).
  R32: settings.os validated with in ("Linux", "OHOS").
  R33: Compiler / flags come from the Conan toolchain, never bare shell vars.
  R38: Executable tool — commands.json declared at the software level.
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LogrotateConan(ConanFile):
    name = "logrotate"
    version = "3.22.0"
    description = "Utility that rotates, compresses and mails system logs"
    license = "GPL-2.0-only"
    homepage = "https://github.com/logrotate/logrotate"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libpopt is vendored (see source()/build()); no registry dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"logrotate 3.22.0 only supports Linux and OHOS, got {self.settings.os}"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"logrotate 3.22.0 only supports armv8, got {self.settings.arch}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored libpopt into ./popt
        get(self, **self.conan_data["popt"], strip_root=True,
            destination=os.path.join(self.source_folder, "popt"))

    @property
    def _popt_prefix(self):
        return os.path.join(self.build_folder, "poptinst")

    def generate(self):
        # HarmonyOS: `mktemp -d` returns dirs with broken group perms (hmmac MAC),
        # which breaks config.status. Shadow mktemp so autoconf's AS_TMPDIR falls
        # back to a plain `mkdir`, which succeeds — this avoids touching the
        # generated configure/config.status scripts (R6/R14).
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text("#!/bin/sh\nexit 1\n")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

        tc = AutotoolsToolchain(self)
        # Point logrotate's configure/compile/link at the vendored static libpopt.
        tc.extra_cflags.append("-I" + os.path.join(self._popt_prefix, "include"))
        tc.extra_ldflags.append("-L" + os.path.join(self._popt_prefix, "lib"))
        # HarmonyOS: config.guess cannot classify the OS (uname -s = HarmonyOS).
        # Give the build triplet explicitly; host defaults to build so the build
        # stays native (cross_compiling=no), unlike a --host override.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def _build_popt(self):
        popt_src = os.path.join(self.source_folder, "popt")
        self.run(
            f"./configure --prefix={self._popt_prefix} "
            "--enable-static --disable-shared --disable-nls "
            "--build=aarch64-unknown-linux-gnu",
            cwd=popt_src,
        )
        self.run("make -j1", cwd=popt_src)
        self.run("make -j1 install", cwd=popt_src)

    def build(self):
        previous_umask = os.umask(0)
        try:
            apply_conandata_patches(self)
            # 1) Vendored static libpopt (required, not yet in the registry).
            self._build_popt()
            # 2) logrotate itself, linked against the static libpopt above.
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            os.umask(previous_umask)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Autotools sbindir is normalised to bin/ by the Conan toolchain, so the
        # logrotate binary lands in bin/ (the default bindir).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
