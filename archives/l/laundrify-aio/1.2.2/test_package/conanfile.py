#!/usr/bin/env python3
"""Conan test_package for laundrify-aio 1.2.2 — consumer check.

Runs test_laundrify.py (standalone test source, satisfies L0c) via
self.run with env="conanrun". PYTHONPATH injection follows the
airthings-cloud pattern: every dependency's site-packages is walked
and injected (aiohttp imports multidict/yarl/... at import time).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class LaundrifyAioTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["laundrify-aio"].package_folder
        sp = os.path.join(pkg, "site-packages")
        if not os.path.isdir(os.path.join(sp, "laundrify_aio")):
            raise ConanException(f"laundrify_aio missing under {sp}")
        # inject ALL dependencies' site-packages into PYTHONPATH
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
                                   "test_laundrify.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_laundrify.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{sp}'", env="conanrun")
