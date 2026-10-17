#!/usr/bin/env python3
"""Conan test_package for dazzdb — runs the installed tools for real.

The suite lives in test_package/test.sh: it drives the 21 installed commands
through the data paths documented in the upstream README (random genome ->
DAM -> simulated reads -> DB -> tracks -> quiva/arrow streams -> ONE export)
and asserts the output of every step, including byte identical round trips.
All artefacts are written to the build folder, which layout() keeps separate
from the package source directory.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class DazzdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bindir = os.path.join(
            self.dependencies["dazzdb"].package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run('sh "%s" "%s" "%s"' % (script, bindir, self.build_folder),
                 env="conanrun")
