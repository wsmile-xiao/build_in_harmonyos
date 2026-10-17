#!/usr/bin/env python3
"""test_package for bsd-finger — runs test.sh which invokes the finger binary."""
import os
import shutil

from conan import ConanFile


class BsdFingerTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries. Use bash.
        # Resolve bash via CONFIG_SHELL override, then PATH lookup,
        # then the well-known OHOS HNP path as last resort.
        bash = os.environ.get("CONFIG_SHELL") or \
            shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} test.sh", env="conanrun")