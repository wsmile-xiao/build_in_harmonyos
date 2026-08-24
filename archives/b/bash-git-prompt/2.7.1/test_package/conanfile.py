#!/usr/bin/env python3
"""Conan test_package for bash-git-prompt。"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class BashGitPromptTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if cross_building(self):
            return
        test_script = os.path.join(self.recipe_folder, "test_bash_git_prompt.py")
        pkg = self.dependencies["bash-git-prompt"].package_folder
        self.run(f'"{sys.executable}" "{test_script}" "{pkg}"', env="conanrun")
