#!/usr/bin/env python3
"""Conan recipe for the architecture-independent jGrowl browser assets."""
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


class JgrowlConan(ConanFile):
    name = "jgrowl"
    version = "1.4.10"
    description = "Unobtrusive jQuery notification plugin browser assets"
    license = "MIT"
    homepage = "https://github.com/stanlemon/jGrowl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(
            self,
            filename="jgrowl-1.4.10.tar.gz",
            **self.conan_data["sources"],
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        # The upstream archive ships ready-to-use JS/CSS assets; no target build is needed.

    def package(self):
        assets = os.path.join(self.package_folder, "share", "jgrowl")
        licenses = os.path.join(self.package_folder, "licenses")
        os.makedirs(assets, exist_ok=True)
        os.makedirs(licenses, exist_ok=True)

        for filename in (
            "jquery.jgrowl.js",
            "jquery.jgrowl.min.js",
            "jquery.jgrowl.css",
            "jquery.jgrowl.min.css",
            "jquery.jgrowl.map",
        ):
            copy(self, filename, src=self.source_folder, dst=assets, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=licenses, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/jgrowl"]
