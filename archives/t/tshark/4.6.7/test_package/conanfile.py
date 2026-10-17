#!/usr/bin/env python3
"""test_package for tshark (CLI tool) — Conan L1 test.

Consumer verification: run the installed `tshark` binary the way a real user
would — check `--version` (binary executes, runtime deps resolve) and
`-G protocols` (the dissection engine initializes and loads the protocol
table). OHOS note: /system/bin/sh (mksh) cannot exec ELF binaries, so the
binary is invoked through bash (test.sh).
"""
import os

from conan import ConanFile


class TsharkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
        # L2: 27 snapshot cases ported from the upstream pytest suite
        # test/suite_dissectors (pure bash + tshark, no python needed).
        self.run(f"{bash} dissectors/runner.sh", env="conanrun")
