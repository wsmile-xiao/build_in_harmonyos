#!/usr/bin/env python3
"""test_package for ucon64 — runs test_ucon64.sh which exercises the binary."""
import os

from conan import ConanFile


class Ucon64TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # conanrun env puts the package's bin/ on PATH, so `ucon64` resolves.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test_ucon64.sh")
        self.run(f'{bash} "{script}"', env="conanrun")
