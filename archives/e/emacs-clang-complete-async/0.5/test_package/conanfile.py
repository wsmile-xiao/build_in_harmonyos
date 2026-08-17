#!/usr/bin/env python3
"""Conan test_package — emacs-clang-complete-async 0.5

Tests that the clang-complete binary is installed and runs correctly.
The binary requires a source file argument and links to libclang at runtime.

Since this is an application package (not a library), the test runs the
binary directly via test.sh and verifies expected error output.
"""
import os
import shutil

from conan import ConanFile


class EmacsClangCompleteAsyncTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        self.run(f"{bash} test.sh", env="conanrun")
