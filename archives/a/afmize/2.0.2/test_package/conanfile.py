#!/usr/bin/env python3
"""Conan test package for afmize 2.0.2 (explicit command consumer)."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class AfmizeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"

    def generate(self):
        VirtualRunEnv(self).generate(scope="run")

    def build(self):
        copy(self, "*.pdb", self.source_folder, self.build_folder)
        copy(self, "config.toml", self.source_folder, self.build_folder)
        copy(self, "test.sh", self.source_folder, self.build_folder)

    def test(self):
        # Host and build profiles are the same OHOS device in this workflow;
        # invoke through the configured bash because /system/bin/sh cannot
        # directly exec an ELF on this worker.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        exe = os.path.join(self.dependencies["afmize"].package_folder, "bin", "afmize")
        self.run(
            'AFMIZE_BIN="{}" "{}" test.sh'.format(exe, bash),
            env="conanrun",
            cwd=self.build_folder,
        )
        for ext in ("ppm", "tsv", "json"):
            path = os.path.join(self.build_folder, "afmize-test." + ext)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise ConanException("empty or missing output: " + path)
