#!/usr/bin/env python3
"""test_package for yersinia executable — runs the installed `yersinia` binary.

Consumer verification: invoke the installed binary the way a real user would
(no-args banner before the root gate; root-gate message as non-root)."""
import os

from conan import ConanFile


class YersiniaTestConan(ConanFile):
    """test_package for yersinia — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
