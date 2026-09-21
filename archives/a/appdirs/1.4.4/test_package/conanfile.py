#!/usr/bin/env python3
"""Conan test_package for appdirs 1.4.4 — consumer check.

Runs test_appdirs.py (standalone test source, satisfies L0c) via self.run with
env="conanrun" so the conanrun PYTHONPATH injection is available.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class AppdirsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["appdirs"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isfile(os.path.join(site, "appdirs.py")):
            raise ConanException(f"appdirs.py missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_appdirs.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_appdirs.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
        # OHOS 专项测试：验证 appdirs 在 OHOS 沙箱路径语义下行为正确
        ohos_script = os.path.join(os.path.dirname(__file__),
                                   "test_ohos_appdirs.py")
        if not os.path.isfile(ohos_script):
            raise ConanException(f"test_ohos_appdirs.py missing: {ohos_script}")
        self.run(f"python3 '{ohos_script}' '{site}'", env="conanrun")
