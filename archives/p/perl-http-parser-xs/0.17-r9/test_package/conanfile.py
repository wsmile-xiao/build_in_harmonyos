#!/usr/bin/env python3
"""Conan test_package — HTTP::Parser::XS Perl XS module.

L1 test: Verify the Perl module .so exists in the package and call actual
HTTP parsing API (parse_http_request + parse_http_response) to validate
functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_http_parser_xs.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and call parse_http_request + parse_http_response
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlHttpParserXsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-http-parser-xs"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_http_parser_xs.sh")

        # R34: Run test script that calls actual HTTP::Parser::XS API
        # parse_http_request + parse_http_response
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("HTTP::Parser::XS test passed (module verified or platform limitation acknowledged)")
