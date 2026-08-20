#!/usr/bin/env python3
"""Conan test_package — perl-mouse 2.6.0-r0 (Mouse Perl XS module).

L1 test: Verify the Mouse module .so and .pm files exist in the package
and call actual Mouse API (has, extends, with, new, accessor) to validate functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_mouse.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and define a class with has/accessor
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlMouseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-mouse"].package_folder
        test_script = os.path.join(os.path.dirname(__file__), "test_mouse.sh")

        # R34: Run test script that calls actual Mouse API (has, extends, with, new, accessor)
        # The script verifies .so/.pm presence, loads the module, and calls Mouse API.
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated — all other errors fail.
        self.run(f'sh "{test_script}" "{pkg_folder}"', env="conanrun")
        self.output.info("Mouse test passed (module verified or platform limitation acknowledged)")
