#!/usr/bin/env python3
"""Conan consumer test for the packaged bash_unit command."""

import os

from conan import ConanFile


class BashUnitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        default_bash = (
            "/data/service/hnp/bin/bash"
            if str(self.settings.os) == "OHOS"
            else "bash"
        )
        bash = os.environ.get("CONFIG_SHELL", default_bash)
        test_tmp = os.path.join(self.build_folder, "consumer-test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        self.run(
            f'TMPDIR="{test_tmp}" "{bash}" test.sh',
            env="conanrun",
        )
