#!/usr/bin/env python3
"""Consumer smoke tests for bozohttpd's version and HTTP serving path."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class BozohttpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["bozohttpd"].cpp_info.bindirs[0]
        binary = os.path.join(bindir, "bozohttpd")
        abi_script = os.path.join(self.source_folder, "test_elf_abi.py")
        self.run(f'"{sys.executable}" "{abi_script}" "{binary}"', env="conanrun")

        if not can_run(self):
            raise RuntimeError(
                "bozohttpd test_package requires a runnable target: the upstream "
                "20-case suite and HTTP smoke test must execute in CI"
            )

        suite_script = os.path.join(self.source_folder, "test_upstream_suite.py")
        suite_data = os.path.join(self.source_folder, "testsuite")
        self.run(
            f'"{sys.executable}" "{suite_script}" "{binary}" "{suite_data}"',
            env="conanrun",
        )

        runtime_script = os.path.join(self.source_folder, "test_bozohttpd.py")
        self.run(f'"{sys.executable}" "{runtime_script}" "{binary}"', env="conanrun")
