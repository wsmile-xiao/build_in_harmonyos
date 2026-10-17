#!/usr/bin/env python3
"""Conan test_package for GNU Proxyknife 1.7 — executes the packaged tool
through the consumer driver test_proxyknife.py (R34: run the packaged
program and assert real behaviour)."""
import os

from conan import ConanFile


class ProxyknifeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["proxyknife"]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_proxyknife.py")
        self.run(f'python3 "{script}" "{bindir}"', env="conanrun")
