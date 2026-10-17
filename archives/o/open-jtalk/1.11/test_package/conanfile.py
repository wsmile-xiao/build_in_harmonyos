#!/usr/bin/env python3
"""test_package for the open-jtalk 1.11 executable package.

open-jtalk ships a command line program (``bin/open_jtalk``) plus the MeCab
NAIST-JDic data directory (``dic/``), so the consumer test runs the delivered
binary from the Conan run environment and checks the packaged data files.
"""
import os

from conan import ConanFile


class OpenJTalkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute the ELF binary directly;
        # wrap the assertions in bash, as the other executable packages do.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
