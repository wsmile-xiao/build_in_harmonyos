#!/usr/bin/env python3
"""test_package for linuxptp — consumer view of the nine installed binaries.

Verifies that a downstream consumer can invoke the PTP tools installed by the
package (help/usage output, config parsing, tz2alt conversion) on HarmonyOS PC.
"""
import os

from conan import ConanFile


class LinuxptpTestConan(ConanFile):
    """test_package for linuxptp — runs test.sh against the installed binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
