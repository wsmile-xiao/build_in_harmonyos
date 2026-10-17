#!/usr/bin/env python3
"""Conan test_package for justbackoff 0.6.0 — consumer check.

Runs two standalone test sources via self.run with env="conanrun" so the
package's conanrun PYTHONPATH injection is applied:

  * test_justbackoff.py       — consumer/API test (R34: really calls the API)
  * test_ohos_justbackoff.py  — OHOS-specific platform contract (≥1 case)

L0c is satisfied by the standalone .py test sources; L0d by the self.run calls
inside test().
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class JustbackoffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        pkg = self.dependencies["justbackoff"].package_folder
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isfile(os.path.join(site, "justbackoff",
                                           "__init__.py")):
            raise ConanException(f"justbackoff package missing under {site}")

        here = os.path.dirname(__file__)
        for script in ("test_justbackoff.py", "test_ohos_justbackoff.py"):
            path = os.path.join(here, script)
            if not os.path.isfile(path):
                raise ConanException(f"{script} missing: {path}")
            self.run(f"python3 '{path}' '{site}'", env="conanrun")
