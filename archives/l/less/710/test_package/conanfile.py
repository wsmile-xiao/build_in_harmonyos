#!/usr/bin/env python3
"""Conan test_package for less 710.

Behavioral consumer test: run the packaged less binary against a real
file and assert its paging output (not a --version-only smoke).
"""
from conan import ConanFile


class LessTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: run the actual packaged less binary with assertions
        import os
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        self.run(f'sh smoke.sh "{bindir}"', env="conanrun")
