#!/usr/bin/env python3
"""Conan recipe for digup 0.6.57 — console tool to verify and update digest files.

digup reads an existing md5sum/sha1sum/sha256sum/sha512sum digest file, rescans
the directory tree, and offers to write back new/updated/renamed/deleted files.
It is a self-contained C program: MD5, SHA1, SHA256, SHA512 and CRC32 come from
its own sources, and the file list is kept in an intrusive red-black tree. The
only system interface is the C library, so there are no Conan dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DigupConan(ConanFile):
    name = "digup"
    version = "0.6.57"
    description = "Console tool to verify and update md5sum or shasum digest files"
    license = "GPL-3.0-or-later"
    homepage = "https://panthema.net/2009/digup/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("digest", "md5", "sha1", "sha256", "sha512", "crc32", "cli")

    # Upstream builds a single executable and no libraries.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS reports `uname -s` as "HarmonyOS", which the shipped
        # config.guess/config.sub (timestamp 2020-01-01) do not know. Patches
        # 0001/0002 teach both scripts the native HarmonyOS triplet, so the
        # build tree canonicalises to build == host == aarch64-unknown-linux-ohos.
        #
        # The repository always passes the *same* profile as -pr:h and -pr:b
        # (ci/conan/build_and_test.sh), so `cross_building()` is False and
        # AutotoolsToolchain does not inject --host/--build at all: configure
        # calls the patched config.guess itself (measured: `checking build
        # system type... aarch64-unknown-linux-ohos`, `checking whether we are
        # cross compiling... no`). configure_args is therefore left untouched;
        # pruning the triplets would only take effect under a heterogeneous
        # build profile, where it would make configure run config.guess on the
        # build machine and silently pick the wrong architecture.
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        # Device default: one compilation job (shared HarmonyOS workstation).
        autotools.make(args=["-j1"])
        # Upstream suite (automake TESTS): test_rbtree test_digest test_digup.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # digup is a CLI tool: it ships no library, only bin/digup.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
