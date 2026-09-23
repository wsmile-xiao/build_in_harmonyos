#!/usr/bin/env python3
"""Test package for dmtx 0.7.8 (libdmtx) on HarmonyOS PC.

Consumer verification (R34): compile a C program that really performs a
libdmtx encode→decode in-memory roundtrip (the upstream simple_test
pattern: dmtxEncodeCreate → dmtxEncodeDataMatrix → dmtxImageCreate →
dmtxDecodeCreate → dmtxRegionFindNext → dmtxDecodeMatrixRegion), then
run it and assert the decoded output equals the input string.
"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["dmtx"].package_folder
        src = os.path.join(os.path.dirname(__file__), "test_dmtx.c")
        exe = "/data/storage/el2/base/cache/dmtx-tp-test"
        self.run(
            f"/data/service/hnp/bin/clang '{src}' "
            f"-I'{pkg}/include' -L'{pkg}/lib' -ldmtx -lm -o '{exe}'",
            env="conanrun",
        )
        self.run(f"'{exe}'", env="conanrun")
