#!/usr/bin/env python3
"""Conan recipe for sersniff 0.0.5 — serial port sniffer/tunneler.

Build system: raw Makefile (no configure, no install target).
Provides: `sersniff` CLI binary (tunnel + sniff between two serial/TCP
ports, e.g. a serial sniffer). It has no library API and no dependency
other than libc (plus POSIX sockets/termios).
OHOS notes:
  * Makefile hard-codes `CC = gcc` and `LINK = gcc`; OHOS has no gcc
    binary. CC and LINK are taken from Conan
    `tools.build:compiler_executables:c` (R33) and passed on the make
    command line (overrides the hard-coded defaults).
  * Makefile has no `install` target, so package() places the built
    binary and man page into the Conan package manually.
  * Upstream ships no test suite: Makefile has only `all`/`clean`
    targets, no check/test harness, no tests/ directory (audited for
    test_package/MANIFEST.yml). Upstream tests are declared
    `upstream_tests_exist: false`; the real device evidence is emitted
    by test_package/test.sh which exercises the built binary.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class SersniffConan(ConanFile):
    name = "sersniff"
    version = "0.0.5"
    description = "A program to tunnel between 2 serial ports and sniff the data"
    license = "GPL-2.0-only"
    homepage = "http://www.earth.li/projectpurple/progs/sersniff.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("serial", "sniffer", "tunnel", "tcp")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sersniff is only supported on Linux/OHOS, got {self.settings.os}")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"sersniff/0.0.5 is validated for OHOS armv8, got {self.settings.arch}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R33: expose CC/CXX/AR/RANLIB from Conan conf via buildenv so the
        # make command line (and any rule expansion) resolves clang, not gcc.
        VirtualBuildEnv(self).generate()

    def _compiler(self):
        # R33: compilers come from Conan profile/conf, never shell env vars.
        conf = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}
        cc = conf.get("c") or os.environ.get("CC") or "clang"
        ar = conf.get("ar") or os.environ.get("AR") or "llvm-ar"
        ranlib = conf.get("ranlib") or os.environ.get("RANLIB") or "llvm-ranlib"
        return cc, ar, ranlib

    def build(self):
        cc, ar, ranlib = self._compiler()
        self.output.info(f"sersniff build: CC={cc} LINK={cc} AR={ar} RANLIB={ranlib} (R33)")
        # Makefile defaults `CC = gcc` and `LINK = gcc`; command-line vars
        # win and fix the absent gcc on OHOS (LINK drives the final link).
        # -j1 caps peak memory (R9 / Signal 9 hardening).
        # The Makefile is an in-source build (no out-of-source support: it
        # emits *.o and the `sersniff` binary into the cwd and links in
        # place). With basic_layout() the default run() cwd is the build
        # folder, which contains no Makefile -> "No targets specified and no
        # makefile found". Run make inside the source folder so the Makefile
        # and generated artifacts land where package() reads them.
        self.run(f"make -j1 CC={cc} LINK={cc} AR={ar} RANLIB={ranlib}",
                 cwd=self.source_folder)

    def package(self):
        # Staged install: copy the built binary and man page into the package.
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man8")
        copy(self, "sersniff", src=self.source_folder, dst=bin_dir,
             keep_path=False)
        copy(self, "sersniff.8", src=self.source_folder, dst=man_dir,
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        pkg_bin = os.path.join(bin_dir, "sersniff")
        if os.path.isfile(pkg_bin):
            # HMBS_CAP_CHMOD may be 0 (HMDFS): best effort.
            try:
                os.chmod(pkg_bin, 0o755)
            except OSError:
                self.output.warning("chmod sersniff skipped (HMFS read-only?)")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure downstream runenv can resolve the binary on PATH.
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
