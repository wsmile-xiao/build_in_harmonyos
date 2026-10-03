#!/usr/bin/env python3
"""test_package for transfuse 0.7.6 — drives the installed executables.

transfuse ships no library, only the ``transfuse`` executable and its
``tf-extract`` / ``tf-inject`` / ``tf-clean`` aliases, so the consumer check
runs those binaries the way a user would and asserts on their observable
output: the version string, the [tf-block:N-<hash>] block segmentation, the
[[t:b:...]] inline-span markers, UTF-8 round-tripping and a byte-for-byte
match against a checked-in golden file.
"""
import os

from conan import ConanFile


class TransfuseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # OHOS: /system/bin/sh is mksh and cannot exec the ELF binaries, so the
        # script is launched through the HNP bash (same pattern as 2048.c).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")