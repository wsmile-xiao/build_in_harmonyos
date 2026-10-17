#!/usr/bin/env python3
"""Conan recipe — m1ddc 1.2.0 (Makefile / multi-file Objective-C CLI)

DDC/CI display control tool for Apple Silicon Macs (waydabber/m1ddc).
Builds sources/i2c.m + sources/ioregistry.m + sources/m1ddc.m into `m1ddc`.

Build system: plain Makefile (clang -fmodules + -framework CoreDisplay on
Apple), no configure.
License: MIT
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class M1ddcConan(ConanFile):
    name = "m1ddc"
    version = "1.2.0"
    description = "Control external displays via DDC/CI (brightness, volume, contrast, input) on Apple Silicon Macs"
    license = "MIT"
    homepage = "https://github.com/waydabber/m1ddc"
    url = "https://github.com/waydabber/m1ddc"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply 0001-portable-nonapple.patch: Apple-only sources are split
        # into #ifdef __APPLE__ (original) + portable C stubs. Without the
        # patch the OHOS clang build dies at "@import Darwin/Cocoa" and
        # "-framework CoreDisplay" (modules/frameworks not found).
        apply_conandata_patches(self)
        # R33: resolve the C compiler from Conan conf (never bare shell vars).
        # Preflight PATH takes precedence when the configured path is absent:
        # ci profile hardcodes /data/service/hnp/bin/clang which is missing
        # on some preflight workers (Error 127 inaccessible or not found);
        # juise pattern prefers PATH lookup (HMBS prepends tool dirs).
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        conf_cc = comp_execs.get("c")
        if conf_cc and os.path.isfile(conf_cc):
            cc = conf_cc
        else:
            cc = (
                shutil.which("clang")
                or shutil.which("cc")
                or os.environ.get("CC")
                or conf_cc
                or "clang"
            )
        # Faithful to upstream Makefile (clang -fmodules -I headers), minus
        # the Apple-only "-framework CoreDisplay" link flag which does not
        # exist on OHOS. The i2c/ioregistry translation units compile to
        # portable stubs on non-Apple; m1ddc.m carries the portable CLI.
        self.run(
            f"{cc} -fmodules -I headers -o m1ddc "
            "sources/i2c.m sources/ioregistry.m sources/m1ddc.m",
            cwd=self.source_folder,
        )

    def package(self):
        # m1ddc is a command-line tool: install the binary to bin/
        copy(self, "m1ddc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
