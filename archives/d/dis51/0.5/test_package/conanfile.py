#!/usr/bin/env python3
"""Conan test_package for dis51 0.5.

The package only ships one executable, so the consumer test runs the packaged
binary against Intel HEX fixtures (test_package/fixtures/) and compares the
8051 assembly listing it produces with hand-checked expected output
(test_package/expected/): 12 cases in total, see MANIFEST.yml.

The binary is always taken from the tested package's bin/ directory (never
from PATH) so that the CI L1e negative test — package artifacts sabotaged and
the test re-run — genuinely fails.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Dis51TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep the test build folder out of the (git-tracked) test_package
        # source folder: build-folder == source-folder would drop the
        # generated env scripts and the test scratch directory into the
        # package source tree.
        basic_layout(self)

    def test(self):
        bin_dir = os.path.join(self.dependencies["dis51"].package_folder, "bin")
        # The test script lives in the source folder, not in the build folder.
        test_sh = os.path.join(self.source_folder, "test.sh")
        # Keep the scratch directory in the build folder so that nothing is
        # written into the git-tracked test_package source tree.
        work_dir = os.path.join(self.build_folder, "dis51-test-work")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably, so
        # wrap the run in bash (CONFIG_SHELL is provided by the OHOS profile).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} "{test_sh}" "{bin_dir}" "{work_dir}"', env="conanrun")
