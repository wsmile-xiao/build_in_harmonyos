#!/usr/bin/env python3
"""Conan test_package — avimetaedit executable smoke + functional tests.

Runs test.sh which exercises the installed avimetaedit binary against the
three official MediaArea regression AVI samples (AVC / AC-3 / AAC) included
here, covering parsing, XMP/aXML/iXML round-trips and MD5 operations.
"""
import os

from conan import ConanFile


class AvimetaeditTestConan(ConanFile):
    """test_package for the avimetaedit executable."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use the build shell explicitly to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")