#!/usr/bin/env python3
"""Conan test_package for brew-cask-completion 2.1.

Verifies that the completion scripts are properly installed and contain
expected content (R34: test must substantially depend on the tested package).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BrewCaskCompletionTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["brew-cask-completion"]
            pkg = dep.package_folder

            # Check bash completion script exists and has expected content
            bash_completion = os.path.join(pkg, "share", "bash-completion", "completions", "brew-cask")
            if not os.path.isfile(bash_completion):
                raise Exception(f"Bash completion script not found: {bash_completion}")
            with open(bash_completion, "r") as f:
                bash_content = f.read()
            if "brew-cask" not in bash_content:
                raise Exception("Bash completion script does not contain 'brew-cask'")
            if "complete" not in bash_content:
                raise Exception("Bash completion script does not contain 'complete' command")
            self.output.info("Bash completion script verified: contains 'brew-cask' and 'complete'")

            # Check fish completion script exists and has expected content
            fish_completion = os.path.join(pkg, "share", "fish", "vendor_completions.d", "brew-cask.fish")
            if not os.path.isfile(fish_completion):
                raise Exception(f"Fish completion script not found: {fish_completion}")
            with open(fish_completion, "r") as f:
                fish_content = f.read()
            if "brew-cask" not in fish_content:
                raise Exception("Fish completion script does not contain 'brew-cask'")
            if "complete" not in fish_content:
                raise Exception("Fish completion script does not contain 'complete' command")
            self.output.info("Fish completion script verified: contains 'brew-cask' and 'complete'")

            # Run smoke test script (source file for CI L0c compliance)
            self.run(f'cd "{self.source_folder}" && bash test.sh "{pkg}"', env="conanrun")
