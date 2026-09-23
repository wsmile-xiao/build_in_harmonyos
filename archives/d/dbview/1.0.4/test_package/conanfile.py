#!/usr/bin/env python3
"""Conan test_package for dbview 1.0.4.

The package only ships one executable, so the consumer test runs the packaged
binary against dBase III fixtures (test_package/fixtures/) and compares the
output it produces with hand-checked golden files (test_package/expected/):
22 cases in total, see MANIFEST.yml.

The binary is always taken from the tested package's bin/ directory (never from
PATH) so that the CI L1e negative test — package artifacts sabotaged and the
test re-run — genuinely fails.
"""
import os

from conan import ConanFile


class DbviewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["dbview"].package_folder, "bin")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably, so
        # wrap the run in bash (CONFIG_SHELL is provided by the OHOS profile).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{bin_dir}"', env="conanrun")
