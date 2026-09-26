#!/usr/bin/env python3
"""test_package for lci 1.3 (justinmeza LOLCODE interpreter) — runs test.sh
which invokes the installed `lci` interpreter on real LOLCODE 1.3 programs
and verifies observable output + exit codes (R34 consumer verification).
"""
import os

from conan import ConanFile


class LciTestConan(ConanFile):
    """test_package for lci executable — runs test.sh which executes the lci
    interpreter on LOLCODE programs and checks output."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries;
        # use bash as the wrapper (same as 2048.c / cwdaemon test packages).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        work_dir = self.build_folder
        self.run(f"{bash} test.sh {work_dir}", env="conanrun")
