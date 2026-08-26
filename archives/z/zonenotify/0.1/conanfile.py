#!/usr/bin/env python3
"""Conan recipe — zonenotify 0.1 (Makefile, CLI tool).

zonenotify sends a DNS NOTIFY packet to BIND slave servers to signal
that a zone has been updated. It is a single-file C program with a
trivial Makefile (no configure script, no library output).

Build system: plain Makefile (single source file compilation).
License: BSD-2-Clause.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZonenotifyConan(ConanFile):
    name = "zonenotify"
    version = "0.1"
    description = "Send DNS NOTIFY packets to BIND slave servers from DJBDNS"
    license = "BSD-2-Clause"
    homepage = "https://github.com/morettoni/zonenotify"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zonenotify supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"

        # E106: OHOS SDK lld depends on libxml2.so.16 which is not
        # available on CI workers. Use GNU ld instead.
        ld_flag = ""
        if self.settings.os == "OHOS":
            ld_flag = "-fuse-ld=/data/service/hnp/bin/ld"

        # The upstream Makefile hardcodes 'cc'; compile directly instead.
        self.run(
            f"{cc} -O2 {ld_flag} zonenotify.c -o zonenotify",
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(
            self,
            "zonenotify",
            src=self.source_folder,
            dst=bin_dir,
        )
        # Ensure execute permission is set (OHOS may not preserve it)
        bin_path = os.path.join(bin_dir, "zonenotify")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
