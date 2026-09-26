#!/usr/bin/env python3
"""Consumer test for the packaged ren command-line tool."""
import os
import shlex

from conan import ConanFile


class RenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        ren_bin = os.path.join(self.dependencies["ren"].package_folder, "bin", "ren")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f"bash {shlex.quote(script)} {shlex.quote(ren_bin)} "
            f"{shlex.quote(self.build_folder)}",
            env="conanrun",
        )
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"make\","
            "\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,"
            "\"reason\":\"upstream has no test tree or Makefile test/check target\"}"
        )
