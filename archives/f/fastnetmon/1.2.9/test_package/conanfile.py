#!/usr/bin/env python3
"""Conan test_package for FastNetMon 1.2.9."""

from conan import ConanFile


class FastnetmonTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", cwd=self.recipe_folder, env="conanrun")
