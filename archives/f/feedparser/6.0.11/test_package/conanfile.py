#!/usr/bin/env python3
"""Conan test_package for feedparser 6.0.11 — consumer check (R34).

 feedparser needs sgmllib3k on the import path — the site-all PYTHONPATH
 (self + sgmllib3k) is assembled by the test conanfile like the awscli
 precedent.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class FeedparserTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["feedparser"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        paths = [os.path.join(pkg, "lib", py_ver, "site-packages")]
        if "sgmllib3k" in self.dependencies:
            paths.append(os.path.join(
                self.dependencies["sgmllib3k"].package_folder,
                "lib", py_ver, "site-packages"))
        site_all = os.pathsep.join(p for p in paths if os.path.isdir(p))
        if not os.path.isfile(os.path.join(paths[0], "feedparser",
                                           "__init__.py")):
            raise ConanException(f"feedparser missing under {paths[0]}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_feedparser.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_feedparser.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site_all}'", env="conanrun")
