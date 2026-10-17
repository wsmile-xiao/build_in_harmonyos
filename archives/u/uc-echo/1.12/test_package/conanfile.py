#!/usr/bin/env python3
"""test_package for uc-echo 1.12 — runs the installed CLI tools end to end.

Consumer verification: build a real correction pipeline with the six installed
binaries (hashing -> HashMerge -> NeighborJoin x2 -> NeighborMerge -> Voting),
assert the corrected output byte-exactly against the golden file, and check
K0 (--version/--help rc=0) for every binary.
"""
import os

from conan import ConanFile


class UcechoTestConan(ConanFile):
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
