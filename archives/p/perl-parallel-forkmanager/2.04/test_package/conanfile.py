#!/usr/bin/env python3
"""Conan test_package — perl-parallel-forkmanager 2.04 (Pure Perl module).

Tests Parallel::ForkManager functionality: module loading, fork/child process,
callbacks, exit code propagation, data structure return, parallel timing.
"""
import os

from conan import ConanFile


class PerlParallelForkManagerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed

    def test(self):
        # Run functional test suite (7 tests covering core functionality)
        # Use bash to invoke script directly (HMDFS may not support execute bit)
        script = os.path.join(self.source_folder, "test_forkmanager.sh")
        self.run(f"bash {script}", env="conanrun")
