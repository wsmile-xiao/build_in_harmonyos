#!/usr/bin/env python3
"""Conan test_package — yydecode 0.2.10.

R34: yydecode is a command-line tool (not a library), so the test genuinely
executes the packaged binary and validates its byte-for-byte output instead of
only printing strings.
"""
import os

from conan import ConanFile


class YydecodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        data_dir = os.path.join(self.recipe_folder, "testdata")
        script = os.path.join(self.recipe_folder, "test.sh")
        # OHOS: /system/bin/sh (mksh) does not reliably execute ELF binaries,
        # so run the driver through bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} "{script}" "{data_dir}"', env="conanrun")
