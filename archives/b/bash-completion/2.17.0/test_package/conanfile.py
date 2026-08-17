#!/usr/bin/env python3
"""Conan test_package — bash-completion 2.17.0.

Verifies that the installed bash-completion scripts exist, are valid,
and can be sourced by bash to provide completion functions.
"""
import os

from conan import ConanFile


class BashCompletionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["bash-completion"]
        pkg_root = dep.package_folder
        pkg_share = os.path.join(pkg_root, "share", "bash-completion")
        bash_completion = os.path.join(pkg_share, "bash_completion")

        # Verify the main bash_completion script exists
        assert os.path.exists(bash_completion), \
            f"bash_completion script not found at {bash_completion}"

        # Verify completions directory has 100+ files
        completions_dir = os.path.join(pkg_share, "completions")
        completions = os.listdir(completions_dir)
        assert len(completions) > 100, \
            f"Expected 100+ completion files, got {len(completions)}"

        # Verify helpers directory exists
        helpers_dir = os.path.join(pkg_share, "helpers")
        assert os.path.isdir(helpers_dir), \
            f"helpers directory not found at {helpers_dir}"

        # Verify pkg-config file exists
        pc_file = os.path.join(pkg_root, "share", "pkgconfig", "bash-completion.pc")
        assert os.path.exists(pc_file), \
            f"bash-completion.pc not found at {pc_file}"

        # L0d: Use self.run() to verify the package content is usable
        # Run the test script that verifies installed content
        test_script = os.path.join(os.path.dirname(__file__), "test_bash_completion.sh")
        self.run(f"sh {test_script} {pkg_root}", env="conanrun")
