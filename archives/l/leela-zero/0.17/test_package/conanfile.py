#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import copy


class LeelaZeroTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test_leela_zero.sh"

    def export_sources(self):
        copy(self, "test_leela_zero.sh", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = os.path.join(self.dependencies["leela-zero"].package_folder, "bin", "leelaz")
        script = os.path.join(self.source_folder, "test_leela_zero.sh")
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f"{shell} {script} {exe}", env="conanrun")
