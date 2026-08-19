#!/usr/bin/env python3
"""Conan test_package for airthings-cloud 0.3.0 — consumer check.

Runs test_airthings.py (standalone test source, satisfies L0c) via
self.run with env="conanrun". PYTHONPATH injection: aiohttp's
site-packages (published dep) is injected the same way as aiohttp's own
test_package did (dependency PYTHONPATH lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AirthingsCloudTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["airthings-cloud"].package_folder
        sp = os.path.join(pkg, "site-packages")
        if not os.path.isdir(os.path.join(sp, "airthings")):
            raise ConanException(f"airthings missing under {sp}")
        # inject ALL dependencies' site-packages into PYTHONPATH —
        # aiohttp imports its deps (multidict/yarl/aiosignal...) at import
        # time, so every dep's site-packages must be on the path; each
        # lives under lib/python3.12/site-packages — walk to locate it
        # (aiohttp test_package pattern: 8 deps injected)
        py = os.environ.get("PYTHONPATH", "")
        for dep in self.dependencies.values():
            sp_dep = None
            for root, _dirs, _files in os.walk(dep.package_folder):
                if os.path.basename(root) == "site-packages":
                    sp_dep = root
                    break
            if sp_dep and os.path.isdir(sp_dep):
                py = sp_dep + ((":" + py) if py else "")
        os.environ["PYTHONPATH"] = py
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_airthings.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_airthings.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{sp}'", env="conanrun")
