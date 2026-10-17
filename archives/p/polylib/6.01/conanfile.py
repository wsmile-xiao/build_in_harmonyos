#!/usr/bin/env python3
"""Conan recipe — polylib 6.01 (PolyLib, IRISA polyhedral operations library).

Upstream autotools build.  configure auto-detects the GMP package injected by
AutotoolsDeps and then builds every integer representation available on the
target (libpolylib32, libpolylib64 and libpolylibgmp); the CLI tools link
against libpolylibgmp, which is also the library exposed through
cpp_info.libs.

OHOS notes:
- E007: the shipped config.guess/config.sub predate HarmonyOS support.
- E011/E136: the autoconf config.status temp directory must be group/other
  readable on HMDFS, otherwise config.status fails with Permission denied.
- E232/E386: the native OHOS executor cannot always launch the source
  configure script directly, and the profile's hnp bash emits getcwd
  diagnostics inside the HMDFS conan build folder, so configure runs through
  a capability-probed shell with CONFIG_SHELL/SHELL re-asserted.
- Release builds define NDEBUG, so the upstream assert()-hidden pthread
  initialisation in source/arith/errors.c has to be made explicit.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PolylibConan(ConanFile):
    name = "polylib"
    version = "6.01"
    description = ("PolyLib: C library for polyhedral operations on unions of "
                   "polyhedra (Ehrhart polynomials, lattice point counting)")
    license = "GPL-3.0-or-later"
    homepage = "https://icps.u-strasbg.fr/polylib/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # candidate shells for native OHOS, probed from the real build folder
    _NATIVE_OHOS_SHELLS = ("/system/bin/sh", "/bin/sh",
                           "/data/service/hnp/bin/bash")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # <polylib/polylibgmp.h> includes <gmp.h>, so consumers of the gmp
        # variant need gmp's headers too, and the static library needs gmp on
        # the link line (repo convention, cf. isl25/ice/re2).
        self.requires("gmp/6.3.0.1", transitive_headers=True,
                      transitive_libs=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "polylib 6.01 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
            if self.options.fPIC:
                # static library objects must be PIC so consumers can link
                # them into their own shared libraries
                tc.extra_cflags.append("-fPIC")
        tc.generate()
        # conanrun.sh exposes the gmp shared library to the upstream test run
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        self._configure(autotools)
        autotools.make()
        if can_run(self):
            # Upstream regression suite: Test/<subdir> feeds every <case>.in to
            # the matching binary and diffs the output against <case>.out for
            # each integer representation (32, 64 and gmp).
            runenv = os.path.join(self.generators_folder, "conanrun.sh")
            self.run(f'. "{runenv}" && make -C Test check', env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libpolylibgmp is the library the installed CLI tools link against
        # (and the only one upstream installs a pkg-config file for); the 32-
        # and 64-bit integer variants ship in the package as well.
        self.cpp_info.libs = ["polylibgmp"]
        # libpolylibgmp's public header <polylib/polylibgmp.h> includes
        # <gmp.h>, so consumers need the gmp dependency propagated
        self.cpp_info.requires = ["gmp::gmp"]
        # the package also installs the PolyLib command-line tools (c2p, pp64,
        # ehrhart_ranking64, ...), declared in the software-level commands.json
        self.cpp_info.bindirs = ["bin"]

    def _native_ohos_shell(self):
        """Return a shell that preserves the working directory on native OHOS.

        E386: an installed shell can return zero while still emitting getcwd
        diagnostics for the HMDFS build folder (the profile's hnp bash does),
        so probe each candidate from the real build folder and accept only a
        clean `pwd`.
        """
        for shell in self._NATIVE_OHOS_SHELLS:
            if not os.path.isfile(shell):
                continue
            try:
                probe = subprocess.run([shell, "-c", "pwd >/dev/null"],
                                       cwd=self.build_folder, capture_output=True,
                                       text=True, timeout=30)
            except (OSError, subprocess.SubprocessError):
                continue
            if (probe.returncode == 0 and not probe.stdout.strip()
                    and not probe.stderr.strip()):
                self.output.info(f"native OHOS configure shell: {shell}")
                return shell
        raise ConanException(
            "no OHOS shell preserved the build directory; refusing to configure")

    def _configure(self, autotools):
        """Run configure with the dependency runtime and, on OHOS, a probed shell.

        gmp only ships shared libraries, and configure executes the programs it
        compiles while checking the toolchain, so the dependency runtime
        (conanrun.sh) has to be active for configure as well.

        E232: CONFIG_SHELL only affects shells started later by autoconf, so
        the initial launch is prefixed explicitly.  The assignment is repeated
        after Conan's conanbuild environment has been sourced, otherwise the
        profile's hnp bash would be used again (E386).  The outer umask stays
        group writable for the config.status temp directory (E011/E136
        fallback; the configure patch is the primary fix).
        """
        runenv = os.path.join(self.generators_folder, "conanrun.sh")
        configure = os.path.join(self.source_folder, "configure")
        if str(self.settings_build.os) == "OHOS":
            shell = self._native_ohos_shell()
            command = (f'. "{runenv}" && umask 002 && CONFIG_SHELL="{shell}" '
                       f'SHELL="{shell}" "{shell}" "{configure}" '
                       f'{autotools._configure_args}')
        else:
            command = (f'. "{runenv}" && "{configure}" '
                       f'{autotools._configure_args}')
        rc = self.run(command, env="conanbuild", ignore_errors=True)
        if rc != 0:
            config_log = os.path.join(self.build_folder, "config.log")
            if os.path.isfile(config_log):
                self.output.info("---- configure failed: config.log tail ----")
                try:
                    with open(config_log, "r", encoding="utf-8",
                              errors="replace") as stream:
                        self.output.info(stream.read()[-16000:])
                except OSError as exc:
                    self.output.info(f"(config.log unreadable: {exc})")
            raise ConanException(f"configure failed (exit {rc})")
