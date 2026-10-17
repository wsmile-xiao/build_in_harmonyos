#!/usr/bin/env python3
"""test_package for fixed-point-fundamentals — runs example binaries via test.sh."""
import os

from conan import ConanFile


class FixedpointfundamentalsTestConan(ConanFile):
    """test_package for fixed-point-fundamentals example programs.

    The package ships 17 executable example programs (no library, no headers).
    test.sh invokes the installed binaries from the package bin/ and checks
    they run with exit code 0 and produce output.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL", "sh")
        self.run(f"{bash} test.sh", env="conanrun")
        self.run(f"{bash} ohos_test.sh", env="conanrun")