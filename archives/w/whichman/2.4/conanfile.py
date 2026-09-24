#!/usr/bin/env python3
"""Conan recipe for whichman 2.4."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class WhichmanConan(ConanFile):
    name = "whichman"
    version = "2.4"
    description = "Fault-tolerant search utilities for man pages, files, and PATH programs"
    license = "GPL-2.0-only"
    homepage = "https://main.linuxfocus.org/~guido/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"whichman supports Linux/OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = compiler_executables.get("c", "clang")
        self.run(f"make -j1 CC='{cc} -static'", env="conanbuild", cwd=self.source_folder)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for tool in ("whichman", "ftff", "ftwhich"):
            copy(self, tool, src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(
            self,
            "*.1",
            src=os.path.join(self.source_folder, "man1"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "whichman"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
