#!/usr/bin/env python3
"""Conan test_package — nethogs 0.8.8 (executable smoke test).

Consumes the installed nethogs binary: verifies -V prints the version
and -h prints usage. nethogs is a CLI tool, not a library, so the test
drives the binary rather than calling a library API.
"""
import os

from conan import ConanFile


class NethogsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot run ELF binaries directly;
        # use CONFIG_SHELL from HMBS-injected env (typically /bin/sh on
        # HMFS, which resolves getcwd correctly — HNP bash does not).
        # See HMBS platform diagnosis: shell_getcwd.
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f"{shell} test.sh", env="conanrun")