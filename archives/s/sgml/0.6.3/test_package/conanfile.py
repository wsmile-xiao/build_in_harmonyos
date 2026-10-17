#!/usr/bin/env python3
"""test_package for sgml 0.6.3 — runs the installed scripts (install-catalog, sgmlwhich).

Consumer verification: invoke the installed tools the way a real user would and
validate the installed SGML data tree (entities/DTD declaration files).
"""
import os

from conan import ConanFile


class SgmlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
