#!/usr/bin/env python3
"""
libdill/2.14 — OpenHarmony/HarmonyOS PC Conan adaptation.

libdill is a C library that makes structured concurrency a first-class citizen.
Upstream uses Autotools; the GitHub tag archive ships no pre-generated configure,
so autoreconf is required (tool_requires: autoconf/automake/libtool/m4).

OHOS notes:
  - configure succeeds with triplet aarch64-unknown-linux-ohos (config.sub supports it).
  - The library links only against libc (pthread); no extra system deps.
  - tests/ipc fails under HMDFS because bind(AF_UNIX path) returns EPERM
    (hmmac=use_task MAC sandbox) — an environment restriction, NOT a libdill defect;
    abstract-namespace AF_UNIX and all tcp/udp/thread/signal tests pass.
  - No POSIX compatibility layer is patched in: per the task rules, no preemptive
    platform shims were added; only the two portability edits below
    (version hardcoding + man/ skip) address build-environment issues.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, replace_in_file, rmdir, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdillConan(ConanFile):
    name = "libdill"
    version = "2.14"
    description = "Structured concurrency in C — coroutines, channels, sockets, fibers"
    license = "MPL-2.0"
    url = "https://github.com/sustrik/libdill"
    homepage = "https://sustrik.github.io/libdill/"
    topics = ("concurrency", "coroutine", "fiber", "structured-concurrency", "socket")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    # Autotools bootstrap from a configure-less git archive.
    tool_requires = (
        "m4/1.4.19",
        "autoconf/2.72",
        "automake/1.18",
        "libtool/2.5.4",
        "pkgconf/3.0.5",
    )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # Generates conanbuildenv with PATH/PERL5LIB for the autotools tool_requires.
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # config.guess cannot auto-detect HarmonyOS; pass the triplet explicitly.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--disable-silent-rules")

        tc.generate()

    def build(self):
        # --- Portability edit 1: hardcode package_version.sh ---
        # The upstream script uses `git describe` to produce the version string.
        # A git tag archive has no .git directory, so the fallback is bogus.
        # Replace the entire script body with a hardcoded "2.14".
        pv = os.path.join(self.source_folder, "package_version.sh")
        save(self, pv, '#!/bin/sh\n\nprintf \'%s\' "2.14"\n')

        # --- Portability edit 2: skip man/ SUBDIRS ---
        # SUBDIRS=man triggers help2man to generate man pages, but help2man is
        # not available in the OHOS build environment. Man pages are not needed
        # for library packaging; set SUBDIRS empty.
        replace_in_file(self, os.path.join(self.source_folder, "Makefile.am"),
                        "SUBDIRS=man", "SUBDIRS=")

        # Bootstrap configure from configure.ac (git tag archive has no configure).
        # Use the Autotools helper's autoreconf so the tool_requires env (PATH,
        # PERL5LIB, ACLOCAL_PATH) is properly activated.
        autotools = Autotools(self)
        # Conan perl/5.42.2 exports Linux-specific PERL5LIB paths which are
        # ABI-incompatible with the native HarmonyOS Perl used by the build
        # environment. autoreconf only needs Automake's pure-Perl modules,
        # so restrict PERL5LIB to Automake and use the native Perl on PATH.
        automake_share = os.path.join(
            self.dependencies.build["automake"].package_folder,
            "share", "automake-1.18"
        )
        self.run(
            f'PERL5LIB="{automake_share}" PERL="$(command -v perl)" autoreconf --force --install',
            cwd=self.source_folder,
            env="conanbuild",
        )

        autotools.configure()
        autotools.make()

        # Run upstream official test suite on HarmonyOS.
        # Upstream tests share fixed resources, so run them serially.
        # tests/ipc creates a pathname-based AF_UNIX socket ("ipc.test").
        # HarmonyOS does not allow that socket file in the Conan/HMDFS build
        # directory, but it is supported under the application cache directory.
        # Run the other 28 official tests through Automake, then execute the
        # unchanged upstream tests/ipc binary from a socket-capable directory.
        upstream_tests = (
            "tests/example "
            "tests/go1 tests/go2 tests/go3 tests/go4 tests/go5 "
            "tests/fd tests/handle tests/chan tests/choose "
            "tests/sleep tests/signals tests/overload tests/rbtree "
            "tests/bundle tests/threads tests/threads2 tests/ipaddr "
            "tests/iol tests/tcp tests/prefix tests/socks5 tests/suffix "
            "tests/udp tests/http tests/ws tests/term tests/happyeyeballs"
        )

        self.run(
            f'make -j1 check TESTS="{upstream_tests}"',
            cwd=self.build_folder,
            env="conanbuild",
        )

        ipc_workdir = "/data/storage/el2/base/cache"
        if not os.path.isdir(ipc_workdir):
            raise ConanInvalidConfiguration(
                f"AF_UNIX test directory does not exist: {ipc_workdir}"
            )

        ipc_socket = os.path.join(ipc_workdir, "ipc.test")
        if os.path.lexists(ipc_socket):
            os.remove(ipc_socket)
        try:
            self.run(
                os.path.join(self.build_folder, "tests", "ipc"),
                cwd=ipc_workdir,
                env="conanbuild",
            )
        finally:
            if os.path.lexists(ipc_socket):
                os.remove(ipc_socket)

    def package(self):
        # Install to a DESTDIR we control, then copy artifacts explicitly.
        dest = os.path.join(self.package_folder, "_inst")
        autotools = Autotools(self)
        autotools.install(args=["DESTDIR=" + dest])
        # Copy library + headers into the conan package layout.
        copy(self, "*.h", src=os.path.join(dest, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=os.path.join(dest, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so*", src=os.path.join(dest, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdill")
        self.cpp_info.set_property("cmake_target_name", "libdill::libdill")
        self.cpp_info.set_property("pkg_config_name", "libdill")
        self.cpp_info.libs = ["dill"]
        if self.settings.os in ["Linux", "OHOS"]:
            self.cpp_info.system_libs = ["pthread"]
