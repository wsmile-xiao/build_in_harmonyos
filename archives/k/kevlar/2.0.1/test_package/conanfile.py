#!/usr/bin/env python3
"""test_package for kevlar — runs the installed kevlar CLI binaries.

kevlar is an application (package_type=application): bin/kevlar, bin/rst2html,
bin/md2html. The test drives a real end-to-end site generation plus each
binary's --help/version entry, which is the meaningful public-API surface.
"""
import os

from conan import ConanFile


class KevlarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")