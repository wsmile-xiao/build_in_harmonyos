#!/usr/bin/env python3
"""Conan test_package for mbpoll 1.5.4 - runs the packaged executable."""
import os

from conan import ConanFile


class MbpollTestConan(ConanFile):
    """Smoke test: run the installed mbpoll binary via test.sh."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve the packaged binary by full path (robust regardless of PATH)
        # and hand it to test.sh.
        bin_path = os.path.join(
            self.dependencies["mbpoll"].package_folder, "bin", "mbpoll")
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries directly;
        # drive the test through bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('{} test.sh "{}"'.format(bash, bin_path), env="conanrun")
