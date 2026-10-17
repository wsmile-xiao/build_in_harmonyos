#!/usr/bin/env python3
"""Conan recipe for almond 0.3.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class AlmondConan(ConanFile):
    name = "almond"
    version = "0.3.3"
    description = "Minimal AMD API implementation for optimized browser builds"
    license = "MIT"
    homepage = "https://github.com/requirejs/almond"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    _resource_dir = os.path.join("share", "almond")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source = os.path.join(self.source_folder, "almond.js")
        with open(source, encoding="utf-8") as stream:
            text = stream.read()
        required_api = (
            "var requirejs, require, define;",
            "define = function",
            "requirejs = require = req = function",
        )
        missing = [marker for marker in required_api if marker not in text]
        if missing:
            raise ConanInvalidConfiguration(f"almond.js is missing AMD API markers: {missing}")

    def package(self):
        copy(self, "almond.js", self.source_folder,
             os.path.join(self.package_folder, self._resource_dir), keep_path=False)
        copy(self, "package.json", self.source_folder,
             os.path.join(self.package_folder, self._resource_dir), keep_path=False)
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, self._resource_dir), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []

    def package_id(self):
        self.info.clear()
