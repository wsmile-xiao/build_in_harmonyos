#!/usr/bin/env python3
"""test_package for 2048.c executable — runs the installed `2048` binary.

Consumer verification: invoke the installed binary the way a real user would,
run the built-in upstream self-test (`2048 test`) and `--version`, and check
observable output + exit codes.
"""
import os

from conan import ConanFile


class Game2048CTestConan(ConanFile):
    """test_package for 2048.c executable — runs test.sh which invokes the 2048 binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")