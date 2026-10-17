#!/usr/bin/env python3
"""Conan recipe — yaha 0.1.83 (Makefile)."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class YahaConan(ConanFile):
    name = "yaha"
    version = "0.1.83"
    description = "Yet Another High-throughput Aligner"
    license = "MIT"
    homepage = "https://github.com/GregoryFaust/yaha"
    url = "https://github.com/GregoryFaust/yaha"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yaha supports Linux and HarmonyOS targets, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # GitHub codeload URLs end in the tag name without an archive suffix.
        # Give Conan the archive extension so it selects the gzip tar extractor.
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename=f"yaha-{self.version}.tar.gz",
            strip_root=True,
        )
        apply_conandata_patches(self)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "cc")
        cpp = compilers.get("cpp", "c++")
        self.run(
            f"make -j1 CC={shlex.quote(cc)} CPP={shlex.quote(cpp)}",
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "yaha",
            src=os.path.join(self.source_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
