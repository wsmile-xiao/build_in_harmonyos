#!/usr/bin/env python3
"""Consumer test for the whichman command-line tool set."""
import os

from conan import ConanFile


class WhichmanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_dir = self.dependencies["whichman"].package_folder
        bin_dir = os.path.join(package_dir, "bin")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'bash "{script}" "{os.path.join(bin_dir, "whichman")}" '
            f'"{os.path.join(bin_dir, "ftff")}" '
            f'"{os.path.join(bin_dir, "ftwhich")}"',
            env="conanrun",
        )
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"make\","
            "\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,"
            "\"reason\":\"upstream has no test tree or Makefile test/check target\"}"
        )
