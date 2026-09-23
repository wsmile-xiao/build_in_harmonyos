#!/usr/bin/env python3
"""Conan test package: import blinker and run all upstream pytest cases."""
import os
import sys

from conan import ConanFile


class BlinkerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        python = sys.executable
        dependency = self.dependencies[self.tested_reference_str]
        site_packages = os.path.join(dependency.package_folder, "lib", "site-packages")
        tests_dir = os.path.join(dependency.package_folder, "res", "upstream_tests")
        consumer_test = os.path.join(self.recipe_folder, "consumer_test.py")
        pytest = f"{python} -m pytest"
        self.run(
            f'{python} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 pytest==8.3.3 pytest-asyncio==0.24.0',
            env="conanrun",
        )
        self.run(
            f'PYTHONPATH="{site_packages}:$PYTHONPATH" {python} -c '
            f'"import blinker; assert blinker.__file__.startswith(\\\"{site_packages}/\\\")"',
            env="conanrun",
        )
        self.run(
            f'PYTHONPATH="{site_packages}:$PYTHONPATH" {pytest} -q "{tests_dir}" '
            f'"{consumer_test}" -o addopts="" -o asyncio_mode=auto --tb=short',
            env="conanrun",
        )
