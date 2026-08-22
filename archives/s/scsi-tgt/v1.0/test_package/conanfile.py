#!/usr/bin/env python3
"""Conan test_package for scsi-tgt v1.0 — binary tool smoke test.

Verifies that the tgtd binary is installed and runs correctly.
R34: test executes the package's binary (tgtd --version).
"""
import os

from conan import ConanFile


class ScsiTgtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        if self.settings.os == "OHOS":
            comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            cc = comp_execs.get("c", "")
            if cc:
                bash = os.path.join(os.path.dirname(cc), "bash")
            else:
                bash = "/data/service/hnp/bin/bash"
        else:
            bash = "bash"
        self.run(f"{bash} test.sh", env="conanrun")
