#!/usr/bin/env python3
"""test_package for mmc 1.0 — verifies the packaged `mmc` executable as a consumer.

Runs the installed binary twice:
  1. bare invocation -> upstream banner + usage (proves the tool is runnable)
  2. a real photon-transport simulation on the bundled 40-tetrahedron cube mesh
     -> exit 0, "total simulated energy" summary and a flux output file
"""
import os

from conan import ConanFile


class MmcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execve ELF binaries directly;
        # run the driver script with the OHOS bash from CONFIG_SHELL.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
