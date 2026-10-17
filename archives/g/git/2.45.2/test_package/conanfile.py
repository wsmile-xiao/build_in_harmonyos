#!/usr/bin/env python3
"""Conan test_package — runs test.sh which executes the installed git binary.

L1 test for executable packages (R34: must actually run the packaged tool).
GIT_BIN is resolved from the tested package's bindir so the negative-control
check (package removed → test must fail) is meaningful even when another git
exists on the system PATH.
"""
import os

from conan import ConanFile


class GitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        git_pkg = self.dependencies[self.tested_reference_str]
        git_bin = os.path.join(git_pkg.package_folder,
                               git_pkg.cpp_info.bindirs[0], "git")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'GIT_BIN="{git_bin}" {bash} test.sh', env="conanrun")
