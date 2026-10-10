#!/usr/bin/env python3
"""Conan test_package — jenkins-cli 0.0.47 (jcli) L1 consumer smoke test.

Runs against the installed bin/jcli via test.sh (VirtualRunEnv), which
executes two real assertions (`jcli version` -> Version: v0.0.47, and
`jcli --help` -> usage) and emits the HMBS_TEST_PACKAGE_RESULT marker with the
actual discovered/passed counts.  The main conanfile.py already ran the full
upstream `go test -v ./...` suite on the device; this package is the L1
consumer-level gate.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class JenkinsCliTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["jenkins-cli"].package_folder
        bin_path = os.path.join(package_folder, "bin", "jcli")
        if not os.path.isfile(bin_path):
            raise SystemExit(f"jcli binary not found in package: {bin_path}")

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_script = os.path.join(self.recipe_folder, "test.sh")
        # Pass the absolute path to the packaged jcli down to test.sh through
        # the inherited environment (self.run inherits os.environ).
        os.environ["JCLI_BIN"] = bin_path
        self.run(f"{bash} {test_script}", env="conanrun")
