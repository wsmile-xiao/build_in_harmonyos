#!/usr/bin/env python3
"""Conan test_package for mr (myrepos) 1.20180726 — Perl script test.

Verifies that the mr command is functional after installation.
Runs `mr help` to verify the mr script can execute and display help,
checks mr help output content, and verifies webcheckout existence.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class MrTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Skip in cross-compilation: target binaries can't run on x86_64 CI workers
        if cross_building(self):
            self.output.warning("Skipping test in cross-compilation mode")
            return

        if can_run(self):
            dep = self.dependencies["mr"]
            bin_dir = os.path.join(str(dep.package_folder), "bin")
            mr_cmd = os.path.join(bin_dir, "mr")
            webcheckout_cmd = os.path.join(bin_dir, "webcheckout")

            # Test 1: mr help should display usage info
            self.run(f'"{mr_cmd}" help', env="conanrun")
            self.output.info("mr help: PASS")

            # Test 2: mr help output should contain key command names
            # Use temp file instead of pipe (set -o pipefail is a bashism);
            # && chain ensures mr help failure propagates in POSIX-compliant shells
            self.run(
                f'"{mr_cmd}" help > mr_help_output.txt && grep -q "mr" mr_help_output.txt && echo "mr help content check: PASS"',
                env="conanrun"
            )

            # Test 3: webcheckout should exist and be executable
            # (webcheckout depends on LWP::Simple/HTML::Parser CPAN modules,
            #  so we verify file existence + executable bit rather than running it)
            if not os.path.isfile(webcheckout_cmd):
                raise Exception(f"webcheckout not found at {webcheckout_cmd}")
            if not os.access(webcheckout_cmd, os.X_OK):
                raise Exception(f"webcheckout not executable at {webcheckout_cmd}")
            self.output.info("webcheckout existence & executable: PASS")
