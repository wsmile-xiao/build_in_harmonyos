#!/usr/bin/env python3
"""Conan test_package for smex — verifies smex.el is installed correctly.

smex is a pure Emacs Lisp package with no binary to execute. Tests verify
the actual package content (file existence + version + function definition)
by delegating to test.sh, which performs three assertions:
  1. smex.el exists in share/emacs/site-lisp/
  2. smex.el declares "Version: 3.0"
  3. smex.el defines (defun smex ...)
"""
import os

from conan import ConanFile


class SmexTestConan(ConanFile):
    """test_package for smex — verifies smex.el installation via test.sh."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # smex is a pure Emacs Lisp file — no binary to execute.
        # All test assertions are pure file-read operations (grep on
        # smex.el), so cross-compilation must NOT skip them. Reference:
        # flow-cli test_package puts file-read checks outside can_run().
        smex_pkg = self.dependencies["smex"].package_folder
        test_script = os.path.join(self.source_folder, "test.sh")

        # Locate bash for executing test.sh (OHOS has no /bin/sh)
        bash = os.environ.get("CONFIG_SHELL") or "bash"

        # R34: test must report failure via return code.
        # test.sh exits non-zero on any assertion failure.
        self.run(f'{bash} "{test_script}" "{smex_pkg}"', env="conanrun")
