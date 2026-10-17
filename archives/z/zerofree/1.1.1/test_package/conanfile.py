#!/usr/bin/env python3
"""Test package for zerofree 1.1.1.

The functional test lives in test.sh: it validates the argument contract and
then drives the packaged binary over a real 1 MiB ext2 image whose free blocks
carry a non-zero pattern, asserting that the tool reports dirty free blocks
before the run and none after it.

Delegates to test.sh (kept as a standalone test source file so the assertions
are visible without reading Python).
"""
import os

from conan import ConanFile


class ZerofreeTestConan(ConanFile):
    # CLI application: the run env (VirtualRunEnv) puts bin/ on PATH, so the
    # script can call `zerofree` by name.
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"/data/service/hnp/bin/bash {script}", env="conanrun")
