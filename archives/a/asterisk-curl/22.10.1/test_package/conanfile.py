#!/usr/bin/env python3
"""Conan test_package for asterisk-curl — runs the R34 consumer check.

L1 official test: verifies the three packaged curl modules exist under
<pkg>/lib/asterisk/modules/, are valid aarch64 ELF shared objects, and link
libcurl. R34 real artifact verification, not just file presence.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["asterisk-curl"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_asterisk_curl.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
