#!/usr/bin/env python3
"""test_package for arttime — runs arttime --version (R34).

arttime is a zsh shell-script CLI tool. The test creates the missing
`is-at-least` zsh autoload function (absent on OHOS minimal zsh) and
then runs `arttime --version` to verify the packaged executable works.
"""
import os

from conan import ConanFile


class ArttimeTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: genuinely exercise the tested package's binary.
        # Use bash to run the test script which sets up zsh FPATH
        # and invokes arttime --version.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
