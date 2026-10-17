#!/usr/bin/env python3
"""Conan test_package for lice5 5.3.0 — script resource verification.

lice5 is a pure IRC script resource package (no executables). Tests verify
that key script files exist and the directory structure is complete after
installation.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class Lice5TestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["lice5"]
            resource_dir = os.path.join(dep.package_folder, "share", "lice5")

            bash = (os.environ.get("CONFIG_SHELL")
                    or shutil.which("bash")
                    or "/bin/bash")
            if not os.path.isfile(bash):
                bash = "/usr/local/bin/bash"

            test_script = os.path.join(self.source_folder, "test.sh")
            ret = self.run(f'"{bash}" "{test_script}" "{resource_dir}"', env="conanrun")
            assert ret == 0, f"test.sh failed with exit code {ret}"
