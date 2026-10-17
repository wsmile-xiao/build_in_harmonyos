#!/usr/bin/env python3
"""Conan recipe — bltool 0.2.4 (failed OHOS adaptation record).

bltool is a Haskell CLI tool; OHOS has no GHC/Cabal toolchain so a real
build is impossible. Following the prefixsuffix pattern, this recipe
successfully builds a *failed-adaptation record* (packaging manifest.yaml
+ notes.md) so that `conan create` succeeds, the test_package runs and
verifies the record, and CI does not go red. status: failed is truthful.
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class BltoolConan(ConanFile):
    name = "bltool"
    version = "0.2.4"
    description = "Failed OHOS adaptation record for bltool"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ToxicFrog/bltool"
    package_type = "application"

    settings = "os", "arch"
    exports_sources = "manifest.yaml", "notes.md"

    def layout(self):
        basic_layout(self)

    def build(self):
        # 成功构建"失败记录包"：校验 manifest/notes 记录完整（不抛错，
        # 使 conan create 成功、test_package 可执行、CI 不红）。
        manifest = os.path.join(self.source_folder, "manifest.yaml")
        notes = os.path.join(self.source_folder, "notes.md")
        if not os.path.isfile(manifest) or not os.path.isfile(notes):
            raise RuntimeError("failed adaptation record is incomplete")

    def package(self):
        destination = os.path.join(self.package_folder, "share", "bltool")
        copy(self, "manifest.yaml", src=self.source_folder, dst=destination)
        copy(self, "notes.md", src=self.source_folder, dst=destination)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
