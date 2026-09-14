#!/usr/bin/env python3
"""Conan test_package — pipebench 0.40 consumer smoke test.

Verifies the packaged tool from a consumer point of view:
- `pipebench -h` prints usage and exits 0
- a real stdin->stdout passthrough preserves bytes and emits a rate Summary
"""
import os
import shutil

from conan import ConanFile


class PipebenchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_pipebench.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin")}"',
                 env="conanrun")
