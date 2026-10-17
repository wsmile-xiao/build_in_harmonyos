#!/usr/bin/env python3
"""Test package for pandocomatic — real runtime smoke on HarmonyOS PC.

R34: the test actually invokes the installed pandocomatic binary:
  1. pandocomatic --version -> prints "Pandocomatic version 2.2.0"
  2. pandocomatic --help   -> prints usage
  3. markdown -> HTML conversion through pandocomatic (requires pandoc)
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment

RUBY_STDLIB_GEMS = "/data/service/hnp/ruby.org/ruby_3.4.5/lib/ruby/gems/3.4.0"


class PandocomaticTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("pandoc/3.10.1")

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["pandocomatic"].package_folder
        pandoc_pkg = self.dependencies["pandoc"].package_folder
        env = Environment()
        gem_home = os.path.join(pkg, "gems")
        env.define("GEM_HOME", gem_home)
        env.append_path("GEM_PATH", gem_home)
        env.append_path("GEM_PATH", RUBY_STDLIB_GEMS)
        # pandocomatic bin wrapper + system ruby + pandoc conan package
        env.prepend_path("PATH", os.path.join(gem_home, "bin"))
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.prepend_path("PATH", os.path.join(pandoc_pkg, "bin"))
        with env.vars(self).apply():
            script = os.path.join(self.recipe_folder, "test_pandocomatic.sh")
            self.run(f'bash "{script}"')