#!/usr/bin/env python3
"""Conan test_package for rdfind 1.8.0 — runs the packaged CLI as a consumer would."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class RdfindTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # Make an otherwise silent skip visible in the build log: CI builds this
            # package natively (host == build => can_run is True), so a skip here
            # means the profiles changed and the consumer test did not really run.
            self.output.warning(
                "can_run=False: skipping the rdfind consumer test "
                "(host/build profiles differ); this build therefore does NOT "
                "verify the packaged binary"
            )
            return

        rdfind = os.path.join(self.dependencies["rdfind"].package_folder, "bin", "rdfind")
        script = os.path.join(self.source_folder, "test_rdfind.sh")
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
        if not shell:
            # Fail closed instead of guessing a worker-specific path (R33): the CI
            # profile provides CONFIG_SHELL/SHELL via its buildenv.
            raise ConanException(
                "no POSIX shell available: neither CONFIG_SHELL nor SHELL is set; "
                "the rdfind consumer test cannot be executed"
            )
        self.run(f'RDFIND_BIN="{rdfind}" "{shell}" "{script}"', env="conanrun")
