#!/usr/bin/env python3
"""Conan recipe for ocproxy 1.60, a user-level SOCKS and port forwarding proxy.

The upstream release tarball ships autotools *sources* only (configure.ac,
Makefile.am, acinclude.m4) but no generated `configure`/`Makefile.in`, so the
recipe bootstraps autotools itself.  Every game dependency (lwIP and the lwIP
unix contrib port) is vendored inside the tarball, so libevent is the only
external build dependency.
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OcproxyConan(ConanFile):
    name = "ocproxy"
    version = "1.60"
    description = "User-level SOCKS and port forwarding proxy for OpenConnect"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cernekee/ocproxy"
    url = "https://github.com/cernekee/ocproxy"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.13")

    def build_requirements(self):
        # The upstream tarball has no generated configure/Makefile.in, so
        # autoreconf must run.  The device happens to have automake in
        # ~/.harmonybrew/bin, but the CI worker's PATH is much shorter and has
        # no aclocal at all, where autoreconf fails with
        # "aclocal failed with exit status: 2" before configure is generated.
        # Take automake from the registry like the in-repo abx recipe does; its
        # package_info exports ACLOCAL_PATH/AUTOMAKE/ACLOCAL/PERL5LIB so the
        # Perl entry points resolve without relying on the host environment.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ocproxy is validated only for Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()
        # autoconf's config.status creates a 0700 temporary directory; HMDFS on
        # OHOS refuses to write into such a directory even for its creator, so
        # keep every temporary file inside the build directory instead.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        toolchain.generate(env=environment)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            self._bootstrap_autotools()
            autotools = Autotools(self)
            autotools.configure(args=self._configure_args())
            # One job at a time: the device is memory constrained and HMDFS can
            # fail the make jobserver FIFO.
            autotools.make(args=["-j1"])

    def package(self):
        with self._build_environment().vars(self).apply():
            # Single job for the install step too: the device is memory
            # constrained and HMDFS can fail the make jobserver FIFO, so the
            # recipe keeps every make invocation at -j1 for consistency with
            # the build step.
            Autotools(self).install(args=["-j1"])
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # G4: declare and verify the real artefacts.  `make install` silently
        # skips a target that was disabled at configure time, so a missing
        # binary must fail the build here rather than produce a package whose
        # commands.json advertises something that is not inside it.
        for binary in ("ocproxy", "vpnns"):
            if not os.path.isfile(os.path.join(self.package_folder, "bin", binary)):
                raise ConanException(
                    f"expected artefact bin/{binary} was not installed"
                )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _bootstrap_autotools(self):
        """Generate configure/Makefile.in from the shipped autotools sources."""
        self.run("autoreconf --force --install --verbose", cwd=self.source_folder)
        # Autoconf's generated configure/config.status create their private
        # temporary directory with `umask 077 && mktemp -d`.  On HMDFS the
        # resulting 2700 directory is not writable even by the process that
        # just created it (the setgid bit plus an owner unreadable to the
        # mapped owner), so config.status aborts with "Permission denied" while
        # writing subs1.awk.  Drop the umask so the directory stays writable.
        # Verified on the device: without the patch config.status fails at the
        # subs1.awk redirect, with it configure completes.
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self,
            configure,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        )
        replace_in_file(
            self,
            configure,
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"',
        )
        # replace_in_file is a no-op when the literal is absent, so verify the
        # rewrite actually landed: an autoconf re-generation or a wording change
        # upstream would otherwise silently restore the unwritable temp dir and
        # surface much later as "config.status: Permission denied".
        with open(configure, "r", encoding="utf-8") as handle:
            rewritten = handle.read()
        if "umask 077" in rewritten:
            raise ConanException(
                "configure still contains 'umask 077' after the HMDFS rewrite"
            )

    @staticmethod
    def _configure_args():
        """Pin the autoconf triplet explicitly.

        config.guess cannot identify HarmonyOS and its compiler probe cannot
        run on the device (there is no `cc` in PATH), so `configure` refuses to
        continue with "cannot guess build type".  config.sub does understand
        `aarch64-linux-ohos`, so the triplet is given explicitly; build and
        host are identical, which keeps configure in native (not cross) mode.
        """
        return ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]

    def _build_environment(self):
        environment = Environment()
        # AutotoolsDeps supplies -L/-l but no rpath, so the shared libevent
        # produced by conan cannot be resolved when configure runs its
        # "whether the C compiler works" / AC_CHECK_LIB probes on the device.
        environment.append_path(
            "LD_LIBRARY_PATH", self.dependencies["libevent"].package_folder + "/lib"
        )
        if self.settings.os == "OHOS":
            # The OHOS SDK's lld needs its ABI-matched libxml2, which lives in
            # the SDK llvm lib directory and is not on the default loader path.
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
            )
            if sdk_llvm_libs:
                environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libs[-1])
        return environment
