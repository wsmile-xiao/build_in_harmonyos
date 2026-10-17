#!/usr/bin/env python3
"""Conan recipe for spinner 1.2.4 — VT100 anti-idle terminal daemon.

Upstream: Joe Laffey / LAFFEY Computer Imaging (GPL-2+), autoconf 2.13 + automake
project. Builds the `spinner` executable: a background daemon that keeps telnet/ssh
links alive by emitting a small rotating VT100 character at the cursor home.

Adapted for HarmonyOS PC, aarch64 (Conan settings os=OHOS arch=armv8; the target
triple aarch64-linux-ohos is supplied by the toolchain shim's --target flag).

No third-party dependencies: spinner links only against the OHOS musl libc, so the
recipe declares no requires()/tool_requires() and W0 dependency checks are vacuous.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpinnerConan(ConanFile):
    name = "spinner"
    version = "1.2.4"
    description = (
        "VT100 anti-idle daemon: keeps telnet/ssh connections alive by cycling a "
        "spinning character at the terminal cursor home position"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://www.laffeycomputer.com/spinner.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R49: never inject a shared system prefix such as /usr/local. autotools
        # requires an ABSOLUTE --prefix, and Autotools.install() prepends
        # DESTDIR=<package_folder> to `make install`, so the staging prefix stays
        # "/" and everything lands under <package_folder>/bin. That keeps the
        # artifact self-contained and writes nothing to a system location.
        # (A relative prefix is rejected: "expected an absolute directory name
        # for --prefix"; an absolute non-"/" prefix gets appended *after* DESTDIR
        # and produces the doubled layout <package_folder>/<abs-prefix>/bin/.)
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # HMDFS portability (E011/E129): relax `umask 077` -> `022` when configure
        # creates its ./confstatXXXXXX scratch dir. HMDFS forces setgid on new
        # directories, so 077 yields drwx--S--- and config.status can no longer
        # write subs.sed/subs.frag/out into it. Without this the Makefile is never
        # generated and `make` dies with "no makefile found".
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS does not allow FIFO creation in the jobserver temp dir
        # ("jobserver mkfifo: .../tmp/GMfifoNNNNN: Operation not permitted").
        # This project is two translation units, so serial make costs nothing.
        autotools.make(args=["-j1"])
        # Staged install: Autotools.install() prepends DESTDIR=<package_folder>,
        # so the binary lands in the package tree and nothing is written to the
        # configured prefix or to any system location. -j1 here as well, because
        # install() does not inherit make()'s args and would otherwise append -jN
        # and hit the same HMDFS jobserver FIFO restriction.
        autotools.install(args=["-j1"])

    def package(self):
        # `make install` provides bin/spinner. Also ship the upstream license so
        # GPL-2 obligations travel with the artifact (CI does not read this, but
        # consumers of the package do).
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
