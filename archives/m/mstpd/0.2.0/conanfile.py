#!/usr/bin/env python3
"""Conan recipe for mstpd 0.2.0 — Multiple Spanning Tree Protocol daemon.

Upstream: https://github.com/mstpd/mstpd

Products: mstpd (802.1D/802.1Q STP/RSTP/MSTP daemon), mstpctl (control CLI),
bridge-stp (ifupdown hook script) and the mstpd-utils helper scripts.

Build system: GNU Autotools.  The official 0.2.0 tag archive ships
configure.ac + Makefile.am + autogen.sh but no generated configure script,
so this recipe bootstraps it with autoreconf (see _bootstrap_env()).

Runtime note: mstpd is a kernel-facing daemon (netlink route socket, bridge
sysfs class, ioctl on bridge devices).  Build and CLI surface are verified by
test_package; the kernel-facing runtime surface is probed and disclosed in
notes.md instead of being faked as runnable.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MstpdConan(ConanFile):
    name = "mstpd"
    version = "0.2.0"
    description = ("Multiple Spanning Tree Protocol daemon (mstpd) with the "
                   "mstpctl control utility and the bridge-stp hook")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mstpd/mstpd"
    url = "https://github.com/mstpd/mstpd"
    topics = ("stp", "rstp", "mstp", "802.1d", "802.1q", "bridge", "daemon")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The upstream tag archive has no configure script, so the Autotools
        # bootstrap tools are required.  Evidence from the merged recipe
        # archives/a/accel-config/4.1.9: the CI clean PATH already carries SDK
        # autoconf 2.72 / autoreconf / autom4te / m4 / perl under
        # /data/service/hnp/bin, but has no aclocal / automake / libtoolize.
        # automake/1.18 ships aclocal+automake (with its own PERL5LIB pointing
        # at its share dir) and libtool/2.5.4 ships libtoolize, which
        # configure.ac needs because it calls LT_INIT.
        # autoconf/2.72 and m4/1.4.19 are deliberately NOT declared: declaring
        # them pulls the OHOS-built perl whose XS modules clash with the SDK
        # perl used by SDK autoreconf (Perl_my_cxt_init: symbol not found).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: os membership test, never equality against a single value.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mstpd is a Linux bridge/STP daemon, unsupported on "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _gnu_triplet(self, arch=None):
        """Map a Conan arch to the GNU host triplet used for configure.

        config.guess is not shipped in the tag archive and the OHOS kernel
        reports sysname HarmonyOS, so the auto-detected build type would fail;
        both --build and --host are pinned to the same glibc-style triplet,
        which keeps configure in native mode (its checks really run).
        Same approach as archives/a/accel-config/4.1.9.
        """
        arch = str(arch or self.settings.arch)
        triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        if arch not in triplets:
            raise ConanInvalidConfiguration("Unsupported arch: " + arch)
        return triplets[arch]

    def _bootstrap_env(self):
        """Point the Autotools bootstrap at real, discoverable tools (E521).

        On the minimal OHOS image the installed libtoolize/automake scripts
        hardcode a SED path under the home-local tool bin directory that does
        # not exist; when
        SED is unset libtoolize's aux-dir heuristic walks up the tree and
        ltmain.sh lands outside the source root, which makes automake abort
        with 'required file ./ltmain.sh not found'  (knowledge entry E521,
        PR !5330).  Exporting the resolved paths of SED/AUTOCONF/AUTOHEADER/
        AUTOM4TE fixes it.  Paths are discovered, never hardcoded.
        """
        for var, tool in (("SED", "sed"), ("AUTOCONF", "autoconf"),
                          ("AUTOHEADER", "autoheader"), ("AUTOM4TE", "autom4te"),
                          ("M4", "m4")):
            found = shutil.which(tool)
            if found:
                os.environ[var] = found

        # clang needs a writable TMPDIR; the host /tmp is read-only erofs (E002).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        bash = shutil.which("bash") or "/bin/sh"
        os.environ.setdefault("CONFIG_SHELL", bash)
        os.environ.setdefault("SHELL", bash)

        # configure.ac calls PKG_PROG_PKG_CONFIG, so aclocal must be able to
        # find pkg.m4.  On this platform pkg-config ships inside the SDK outside
        # the conan tool graph, and its aclocal dir is not the conventional one:
        # the real file lives in <sdk>/pkg-config.org/pkg-config_<ver>/share/
        # aclocal/pkg.m4.  Discover it by glob (never hardcode), and add
        # libtool's aclocal dir from the tool graph as belt and braces.
        aclocal_dirs = []
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            import glob as _glob
            root = os.path.dirname(os.path.dirname(pkg_config))
            patterns = [os.path.join(root, "pkg-config.org", "pkg-config_*",
                                     "share", "aclocal"),
                        os.path.join(root, "share", "aclocal")]
            for pattern in patterns:
                for candidate in _glob.glob(pattern):
                    if os.path.isdir(candidate):
                        aclocal_dirs.append(candidate)
        for dep in self.dependencies.build.values():
            if dep.ref.name == "libtool":
                candidate = os.path.join(dep.package_folder, "share", "aclocal")
                if os.path.isdir(candidate):
                    aclocal_dirs.append(candidate)
        existing = os.environ.get("ACLOCAL_PATH", "")
        joined = ":".join([d for d in aclocal_dirs + [existing] if d])
        if joined:
            os.environ["ACLOCAL_PATH"] = joined
        return bash

    def generate(self):
        self._bootstrap_env()
        triplet = self._gnu_triplet()
        build_arch = None
        if self.settings_build is not None:
            build_arch = self.settings_build.get_safe("arch")
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        tc = AutotoolsToolchain(self)
        # E091: the OHOS sysroot declares struct sockaddr_storage twice - once
        # in sys/socket.h (inside #ifndef __MUSL__) and once unguarded in
        # linux/socket.h.  libnetlink.c includes both (sys/socket.h directly,
        # linux/netlink.h through libnetlink.h), so the plain build fails with
        # "redefinition of 'sockaddr_storage'".  Defining __MUSL__ activates the
        # sys/socket.h guard; same handling as archives/a/acpid/2.0.34.
        tc.extra_cflags.append("-D__MUSL__")
        tc.configure_args.extend([
            "--build=" + build_triplet,
            "--host=" + triplet,
            # Keep the optional ifupdown integration out of the package: its
            # install hook symlinks into /etc/network, outside the prefix.
            "--disable-install-ifupdown-scripts",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_env()
        # HMDFS getcwd family (E386/E490): autoconf's configure unconditionally
        # re-execs itself into $CONFIG_SHELL (generated configure lines 119/134),
        # and the repo profile ci/conan/profiles/ohos-aarch64 exports
        # CONFIG_SHELL=/data/service/hnp/bin/bash through its [buildenv].  That
        # bash cannot getcwd() inside the conan build tree, so its `pwd` fails
        # and autoconf's AS_INIT bootstrap check aborts with
        #     configure: error: working directory cannot be determined
        # (B-machine probe 2026-09-26, child spawned with cwd=<build_folder>:
        #  hnp bash `pwd` -> rc=1 plus "shell-init: error retrieving current
        #  directory: getcwd"; the same probe with PWD preset to that directory
        #  -> rc=0 with empty stderr).
        # Presetting PWD lets the shell's `pwd` builtin answer from the logical
        # path instead of through getcwd(); same mechanism as
        # archives/a/adms/2.3.7 and the analog/homebrew recipe it cites.
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.autoreconf(args=["--install", "--force"])
        # HMDFS getcwd family, second stage: autoconf's
        #     tmp=`(umask 077 && mktemp -d "./confXXXXXX")`
        # idiom yields a temporary directory that config.status cannot write
        # into on this filesystem, so the very first heredoc aborts with
        #     ./config.status: line 814: ./confHOBzLB/subs1.awk: Permission denied
        #     config.status: error: could not setup config files machinery
        # Relaxing the umask is the proven fix on this repo
        # (archives/c/cvsgraph/1.7.0, archives/a/adms/2.3.7 patch 0002,
        # archives/a/atari800/5.2.0 patch 0003).  It has to run after
        # autoreconf, because autoreconf is what generates this configure.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022", strict=True)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # AutotoolsToolchain forces --sbindir=${prefix}/bin, so the upstream
        # sbin_PROGRAMS (mstpd, mstpctl) and sbin_SCRIPTS (bridge-stp) land in
        # bin/.  Declaring only sbin here would leave the conanrun PATH without
        # the real directory (rc=127), see archives/a/adcli/0.9.2 notes.
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
