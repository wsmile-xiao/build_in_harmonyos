#!/usr/bin/env python3
"""Conan test_package for ahcpd 0.53."""
import os
import shutil

from conan import ConanFile


class AhcpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ahcpd"]
        bin_path = os.path.join(
            str(dep.package_folder), "usr", "local", "bin", "ahcpd"
        )
        script = os.path.join(self.source_folder, "test_ahcpd.sh")
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            bash = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else shutil.which("bash") or "bash"
            )
        self.run(f'"{bash}" "{script}" "{bin_path}"', env="conanrun")
