#!/usr/bin/env python3
"""Test package for bgpq4 1.16."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, load
import os
import shutil

from conan.errors import ConanException


class Bgpq4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def export_sources(self):
        copy(self, "test_bgpq4.sh", self.recipe_folder, self.export_sources_folder)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_bgpq4.sh")
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
            if not os.path.isfile(bash):
                raise ConanException("bash not found; set CONFIG_SHELL to a bash executable")
            self.run(f'"{bash}" "{script}"', env="conanrun")
            output = load(self, os.path.join(self.build_folder, "bgpq4-version.txt"))
            if "bgpq4" not in output.lower():
                raise Exception(f"unexpected bgpq4 version output: {output!r}")
