#!/usr/bin/env python3
"""Conan test_package for tboot 1.10.5 — exercises the installed host tools.

The package ships seven command line programs (see the recipe's package_info
and commands.json), so the consumer test is an executable test: it runs every
tool with real inputs and pins the sha256 that tb_polgen computes with
libcrypto, plus the HarmonyOS specifics of the port ($TMPDIR scratch file,
aarch64/OHOS-only ABI).  See test.sh and MANIFEST.yml.
"""
import os

from conan import ConanFile


class TbootTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so the test
        # driver is run with bash; the tools themselves are resolved through
        # the VirtualRunEnv PATH (i.e. from the tested package's bin/).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
