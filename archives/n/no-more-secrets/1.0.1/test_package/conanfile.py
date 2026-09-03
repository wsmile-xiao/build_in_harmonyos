#!/usr/bin/env python3
"""Conan test_package — no-more-secrets 1.0.1.

Smoke-tests the two installed CLI tools: `nms -v` must print the expected
version string, and the `sneakers` binary must be present and executable.
"""
import os

from conan import ConanFile


class NoMoreSecretsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: only meaningful on Linux/OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["no-more-secrets"].package_folder
        nms = os.path.join(pkg, "bin", "nms")
        sneakers = os.path.join(pkg, "bin", "sneakers")
        # Real execution of the installed binary: version probe must match.
        self.run(f'"{nms}" -v | grep -q "nms version 1.0.1"', env="conanrun")
        # sneakers needs an interactive TTY to run; verify presence/exec here.
        self.run(f'test -x "{sneakers}"', env="conanrun")
        self.output.info("no-more-secrets smoke test passed (nms -v + sneakers present)")
