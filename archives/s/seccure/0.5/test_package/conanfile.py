#!/usr/bin/env python3
"""Run the upstream SECCURE end-to-end tests against installed binaries."""

import os
import shlex

from conan import ConanFile


class SeccureTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["seccure"].package_folder
        bindir = os.path.join(package_folder, "bin")
        work = os.path.join(self.build_folder, "upstream-test")
        script = os.path.join(self.source_folder, "run_upstream_tests.sh")
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            "%s %s %s %s"
            % (
                shlex.quote(bash),
                shlex.quote(script),
                shlex.quote(bindir),
                shlex.quote(work),
            ),
            env="conanrun",
        )
