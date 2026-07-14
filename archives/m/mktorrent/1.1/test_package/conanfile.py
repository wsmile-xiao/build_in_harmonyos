#!/usr/bin/env python3
"""Conan test_package — mktorrent 1.1.

R34: substantively exercises the binary by having it build a real BitTorrent
metainfo (.torrent) file from a sample payload (see test.sh).
"""
import os

from conan import ConanFile


class MktorrentTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
