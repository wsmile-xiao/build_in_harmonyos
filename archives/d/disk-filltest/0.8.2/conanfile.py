#!/usr/bin/env python3
"""Conan recipe for disk-filltest 0.8.2 (upstream single-file Makefile build)."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout


class DiskFilltestConan(ConanFile):
    name = "disk-filltest"
    version = "0.8.2"
    description = (
        "Simple program to detect bad disks by filling them with random data "
        "and re-reading the files to verify the pseudo-random sequence."
    )
    license = "GPL-3.0-or-later"
    homepage = "https://panthema.net/2013/disk-filltest/"
    url = "https://github.com/bingmann/disk-filltest"
    topics = ("disk", "storage", "test", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        # Two official upstream distributions of the same release: the GitHub tag
        # archive (byte-identical to the Debian orig tarball) and the author's own
        # project site. The HarmonyOS device reaches panthema.net but not
        # github.com, the CI worker the other way round, so both are declared.
        errors = []
        for entry in self.conan_data["sources"]:
            # Reset the source tree so a partially extracted first attempt cannot
            # be mixed with the second archive.
            rm(self, "*", self.source_folder)
            try:
                get(self, **entry, strip_root=True)
            except Exception as exc:  # noqa: BLE001 - fall through to next source
                errors.append("{}: {}".format(entry["url"], exc))
            else:
                self.output.info("Source fetched from {}".format(entry["url"]))
                return
        raise ConanException(
            "disk-filltest sources unavailable ({}).".format("; ".join(errors))
        )

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("disk-filltest requires a POSIX host (Linux or OHOS)")
        # In build() (not source()) to match the merged reference packages; this
        # recipe ships no patches, so the call is a no-op kept for convention.
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or str(self.settings.compiler)
        if compilers and not compilers.get("c"):
            self.output.warn(
                "tools.build:compiler_executables has no 'c' entry; falling back to "
                "settings.compiler={}".format(cc)
            )
        # Upstream `all` target: $(CC) $(CFLAGS) -o disk-filltest disk-filltest.c
        # CFLAGS stays upstream-owned (-O3 -W -Wall -ansi); it compiles clean on the
        # OHOS clang 15 / musl toolchain, and upstream fixes it regardless of
        # Conan's build_type.
        self.run('make -j1 CC="{}"'.format(cc))

    def package(self):
        # Upstream `make install` needs GNU install plus gzip (man page) and
        # hard-codes a /usr/local prefix; neither is available on the device PATH,
        # so the artifacts are placed from the recipe instead. The man page is
        # shipped uncompressed for the same reason.
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        lic_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "disk-filltest", src=self.build_folder, dst=bin_dir, keep_path=False)
        copy(self, "disk-filltest.1", src=self.build_folder, dst=man_dir, keep_path=False)
        copy(self, "COPYING", src=self.build_folder, dst=lic_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
