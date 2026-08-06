#!/usr/bin/env python3
"""Conan test_package — Data::UUID Perl XS module.

L1 test: Verify the Perl module .so exists in the package and call actual
Data::UUID API functions (create_str, to_string, from_string, compare) to
validate functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_uuid.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and call create_str + to_string + from_string + compare
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class DataUUIDTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["data-uuid"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_uuid.sh")

        # R34: Run test script that calls actual Data::UUID API (create_str, to_string,
        # from_string, compare). The script verifies .so/.pm presence, loads the module,
        # and calls Data::UUID functions. On OHOS HMDFS, "Permission denied" (E073) is
        # tolerated — all other errors fail.
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("Data::UUID test passed (module verified or platform limitation acknowledged)")
