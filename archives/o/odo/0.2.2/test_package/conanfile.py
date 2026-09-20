#!/usr/bin/env python3
"""Conan test_package for odo 0.2.2 -- consumer test.

odo is a command-line application (not a library): the consumer test
builds a tiny shell script that invokes the packaged `odo` binary and
verifies its real behaviour (set / print / increment), i.e. a real
consumer use of the public CLI.
"""
import os

from conan import ConanFile


class OdoTestConan(ConanFile):
    """test_package for odo -- runs test.sh which exercises the packaged odo binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
