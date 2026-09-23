#!/usr/bin/env python3
"""test_package for cfingerd — executable package (R34: must invoke the real binary).

cfingerd is an inetd-spawned finger daemon: it cannot run as a service in the
OHOS sandbox (needs root + inetd + a connected socket). The `-h` option prints
the command-line usage and exits 0 without touching sockets or privileges,
which makes it the right smoke target here.
"""
import os

from conan import ConanFile


class CfingerdTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
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
