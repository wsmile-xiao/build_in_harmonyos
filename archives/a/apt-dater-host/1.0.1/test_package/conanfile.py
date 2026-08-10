#!/usr/bin/env python3
import os

from conan import ConanFile


class AptdaterhostTestConan(ConanFile):
    """test_package for apt-dater-host — verifies the shell script is installed correctly."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use bash to run test.sh; on OHOS /system/bin/sh (mksh) cannot
        # execute some constructs, so bash is preferred.
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
