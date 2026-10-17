#!/usr/bin/env python3
"""Conan test_package — HTML::Parser Perl XS module.

L1 test: Verify the Perl module .so exists in the package and call actual
HTML::Parser API functions (parse HTML, encode/decode entities) to validate
functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_html_parser.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and call HTML::Parser API
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlHtmlParserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-html-parser"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_html_parser.sh")

        # R34: Run test script that calls actual HTML::Parser API
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("HTML::Parser test passed (module verified or platform limitation acknowledged)")
