#!/usr/bin/env python3
"""
test_package for jruby-webrick — validates WEBrick .rb files.

This test exercises the real WEBrick API by validating that the packaged
.rb files contain the correct module/class declarations that constitute
the WEBrick HTTP server toolkit.
"""

import os

from conan import ConanFile


class JrubyWebrickTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["jruby-webrick"]
        test_script = os.path.join(self.source_folder, "test_webrick.py")
        self.run(f'python3 "{test_script}" "{dep.package_folder}"', env="conanrun")
