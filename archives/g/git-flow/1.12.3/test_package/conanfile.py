#!/usr/bin/env python3
"""Conan test_package for git-flow 1.12.3 — Shell script test.

Verifies that the git-flow command is functional after installation.
Runs `git-flow version` and checks the output contains expected version string.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GitflowTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get the bin directory from the dependency package
            dep = self.dependencies["git-flow"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            git_flow_cmd = os.path.join(bin_dir, "git-flow")

            # Run git-flow version and verify output
            self.run(f'"{git_flow_cmd}" version', env="conanrun")
