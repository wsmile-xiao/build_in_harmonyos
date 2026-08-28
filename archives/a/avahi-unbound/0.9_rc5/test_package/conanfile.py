#!/usr/bin/env python3
"""Conan test_package for avahi-unbound 0.9_rc5.

Runs test_avahi_unbound.sh which verifies that the config file is correctly
installed at etc/unbound/unbound.conf.d/avahi.conf and contains the expected
content (7 assertions: file existence, forward-zone section, zone name,
forward-addr, server section, do-not-query-localhost, domain-insecure).
"""
import json
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["avahi-unbound"].package_folder
        # Use zsh directly to support set -euo pipefail (OHOS /bin/sh lacks pipefail)
        script = os.path.join(self.source_folder, "test_avahi_unbound.sh")
        test_pkg = {
            "executed": True,
            "passed": False,
            "command": "test_avahi_unbound.sh",
            "discovered": 7,
            "passedCount": 0,
        }
        try:
            self.run(
                f'zsh "{script}" "{pkg_folder}"',
                env="conanrun")
            test_pkg["passed"] = True
            test_pkg["passedCount"] = 7
        except Exception as exc:
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                    test_pkg, ensure_ascii=False))
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                test_pkg, ensure_ascii=False))
