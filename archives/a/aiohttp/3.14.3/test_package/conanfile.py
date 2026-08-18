#!/usr/bin/env python3
"""Conan test_package for aiohttp 3.14.3 — consumer check.

Runs test_aiohttp.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" (the conanrun PATH injection is required — a bare
subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class AiohttpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["aiohttp"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "aiohttp")):
            raise ConanException(f"aiohttp package missing under {site}")
        # inject PYTHONPATH for all runtime deps (package_info prints but
        # doesn't set runenv_info — CI failed: No module named 'multidict',
        # same lesson as cgi's PERL5LIB injection)
        deps = ["yarl", "multidict", "idna", "propcache", "aiosignal",
                "frozenlist", "attrs", "aiohappyeyeballs"]
        paths = []
        for d in deps:
            dp = self.dependencies.get(d)
            if dp:
                dsite = os.path.join(dp.package_folder, "lib", py_ver,
                                     "site-packages")
                if os.path.isdir(dsite):
                    paths.append(dsite)
        if paths:
            os.environ["PYTHONPATH"] = ":".join(paths) + ":" + site
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_aiohttp.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_aiohttp.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
