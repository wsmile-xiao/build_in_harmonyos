#!/usr/bin/env python3
"""Conan test_package for bpm-tools.

Runs test_bpm.sh which generates synthetic 120 BPM audio,
pipes it to the bpm binary, and verifies the detection result.
"""
from conan import ConanFile


class BpmtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Build in source directory so test_bpm.sh is accessible
        self.folders.build = "."
        self.folders.generators = "."

    def test(self):
        # Run the functional test script
        # env="conanrun" sources conanrun.sh which sets PATH to include bpm binary
        self.run("zsh ./test_bpm.sh", env="conanrun")
