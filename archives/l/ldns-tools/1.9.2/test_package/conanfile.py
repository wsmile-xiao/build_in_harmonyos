#!/usr/bin/env python3
"""Conan test_package for ldns-tools 1.9.2.

The tested package only ships command line programs, so the test drives the
real drill and the real ldns example programs: a version query, an offline
zone-file round trip through ldns-read-zone (no resolver involved), and the
failure mode for a missing input (R34: the test must run the binaries).
"""
import os

from conan import ConanFile


class LdnsToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")