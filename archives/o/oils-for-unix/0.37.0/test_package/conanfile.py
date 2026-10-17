#!/usr/bin/env python3
"""test_package for oils-for-unix (command-line tool).

Runs test.sh in the conanrun environment (PATH includes the installed bin/),
so the test really executes the packaged osh/ysh/oils-for-unix binaries and
asserts their output and exit codes.
"""
import os

from conan import ConanFile


class OilsForUnixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot reliably exec our ELF binaries;
        # wrap the test script with the real bash available on the build host.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
