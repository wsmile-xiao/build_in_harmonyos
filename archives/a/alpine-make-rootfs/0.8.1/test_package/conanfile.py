#!/usr/bin/env python3
"""Conan test_package for alpine-make-rootfs 0.8.1."""
import os
import shutil

from conan import ConanFile


class AlpineMakeRootfsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_alpine_make_rootfs.sh")
        self.run(
            f'"{bash}" "{script}" "{os.path.join(pkg_folder, "bin", "alpine-make-rootfs")}" "{bash}"',
            env="conanrun",
        )
