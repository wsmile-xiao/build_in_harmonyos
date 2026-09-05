#!/usr/bin/env python3
"""Conan recipe for lsof 4.99.3 — OHOS (HarmonyOS PC) adaptation.

lsof is a command-line tool (LiSt Open Files), not a library:
- package_type = "application", produces bin/lsof only
- no shared/static options, no cpp_info.libs

Upstream uses stock Autoconf (configure) since 4.94. The recipe passes
--build explicitly because upstream config.guess cannot classify the
HarmonyOS uname output ("HarmonyOS HongMeng Kernel 1.13.0").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LsofConan(ConanFile):
    name = "lsof"
    version = "4.99.3"
    description = "LiSt Open Files - lists information about files opened by processes"
    license = "lsof"
    homepage = "https://github.com/lsof-org/lsof"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # no shared/static options: pure CLI tool, no library artifact

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lsof has no external dependencies (pure C, libc only)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: OHOS is a Linux-like platform, allow both
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream config.guess cannot guess HarmonyOS (uname -s = HarmonyOS),
        # and config.sub rejects the -ohos suffix: pass a linux triplet
        # explicitly (build==host -> native compile, no cross-compiler prefix).
        tc.update_configure_args({"--build": "aarch64-unknown-linux",
                                  "--host": None})
        tc.configure_args.append("--disable-liblsof")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # lsof is a command-line tool, not a library
        self.cpp_info.lib = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
